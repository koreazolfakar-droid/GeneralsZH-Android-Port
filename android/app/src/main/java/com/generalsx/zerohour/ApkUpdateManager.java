package com.generalsx.zerohour;

import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.net.Uri;

import androidx.core.content.FileProvider;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * APK-only updates. This is deliberately independent of UpdateManager's signed engine channel.
 * No native libraries, engine markers, external game directories or mods are modified here.
 * GitHub is a discovery/download source, NOT a source of installation authority: the complete
 * APK must match its release SHA-256, our installed package name and signing certificate, and
 * have a strictly higher versionCode before the Android package installer is offered.
 */
final class ApkUpdateManager {
    private static final String RELEASES_API =
        "https://api.github.com/repos/koreazolfakar-droid/GeneralsZH-Android-Port/releases/latest";
    private static final String APK_PATH_PREFIX =
        "/koreazolfakar-droid/GeneralsZH-Android-Port/releases/download/";
    private static final Pattern VERSION =
        Pattern.compile("^v?(\\d+)\\.(\\d+)\\.(\\d+)(?:[-+].*)?$");
    private static final Pattern SHA256 = Pattern.compile("^[0-9a-fA-F]{64}$");
    private static final long MAX_APK_BYTES = 512L * 1024 * 1024;

    static final class Release {
        final String version;
        final String url;
        final String sha256;
        final long size;

        Release(String version, String url, String sha256, long size) {
            this.version = version;
            this.url = url;
            this.sha256 = sha256.toLowerCase(Locale.ROOT);
            this.size = size;
        }
    }

    interface ProgressListener {
        /** Called from the caller's background thread. */
        void onProgress(long bytes, long total);
    }

    private ApkUpdateManager() { }

    static boolean isNewerVersion(String candidate, String current) {
        long[] theirs = parseVersion(candidate);
        long[] ours = parseVersion(current);
        if (theirs == null || ours == null) return false;
        for (int i = 0; i < 3; i++) {
            if (theirs[i] != ours[i]) return theirs[i] > ours[i];
        }
        return false;
    }

    private static long[] parseVersion(String value) {
        if (value == null) return null;
        Matcher m = VERSION.matcher(value);
        if (!m.matches()) return null;
        try {
            return new long[] {
                Long.parseLong(m.group(1)), Long.parseLong(m.group(2)),
                Long.parseLong(m.group(3))
            };
        } catch (NumberFormatException invalid) {
            return null;
        }
    }

    static boolean trustedDownloadUrl(String text) {
        try {
            URL url = new URL(text);
            return "https".equals(url.getProtocol())
                && url.getPort() == -1
                && "github.com".equalsIgnoreCase(url.getHost())
                && url.getPath().startsWith(APK_PATH_PREFIX)
                && !url.getPath().contains("..")
                && url.getPath().endsWith(".apk")
                && url.getUserInfo() == null;
        } catch (Exception invalid) {
            return false;
        }
    }

    static Release check(Context context) throws Exception {
        byte[] data = readLimited(open(RELEASES_API, 0), 2 * 1024 * 1024);
        JSONObject release = new JSONObject(new String(data, StandardCharsets.UTF_8));
        if (release.optBoolean("draft") || release.optBoolean("prerelease")) return null;
        String tag = release.optString("tag_name", "");
        PackageInfo installed = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
        if (!isNewerVersion(tag, installed.versionName)) return null;

        JSONArray assets = release.optJSONArray("assets");
        if (assets == null) return null;
        for (int i = 0; i < assets.length(); i++) {
            JSONObject asset = assets.optJSONObject(i);
            if (asset == null) continue;
            String url = asset.optString("browser_download_url", "");
            String digest = asset.optString("digest", "");
            long size = asset.optLong("size", 0);
            if (!trustedDownloadUrl(url) || !digest.startsWith("sha256:") ||
                    !SHA256.matcher(digest.substring(7)).matches() ||
                    size <= 0 || size > MAX_APK_BYTES) continue;
            // The metadata is public; the installation signature is checked after download.
            return new Release(tag, url, digest.substring(7), size);
        }
        return null;
    }

    private static File updateDir(Context context) throws IOException {
        File dir = new File(context.getCacheDir(), "apk-updates");
        if (!dir.isDirectory() && !dir.mkdirs()) throw new IOException("Cannot create APK cache");
        return dir;
    }

    /** Blocking. Retains a partial file on network errors, and resumes only the same digest. */
    static File download(Context context, Release release, ProgressListener listener) throws Exception {
        if (!trustedDownloadUrl(release.url) || !SHA256.matcher(release.sha256).matches() ||
                release.size <= 0 || release.size > MAX_APK_BYTES) {
            throw new IOException("Invalid APK release metadata");
        }
        File dir = updateDir(context);
        File completed = new File(dir, release.sha256 + ".apk");
        if (completed.isFile() && completed.length() == release.size &&
                hash(completed).equals(release.sha256)) {
            if (listener != null) listener.onProgress(release.size, release.size);
            return completed;
        }
        if (completed.exists() && !completed.delete()) throw new IOException("Cannot replace cached APK");
        File partial = new File(dir, release.sha256 + ".part");
        long offset = partial.exists() ? partial.length() : 0;
        if (offset > release.size) {
            if (!partial.delete()) throw new IOException("Invalid partial APK");
            offset = 0;
        }
        if (dir.getUsableSpace() < (release.size - offset) + 8L * 1024 * 1024) {
            throw new IOException("Not enough space for the APK update");
        }
        if (offset < release.size) {
            HttpURLConnection conn = open(release.url, offset);
            try {
                int status = conn.getResponseCode();
                if (offset > 0 && status == HttpURLConnection.HTTP_OK) {
                    offset = 0; // Server refused Range: safely start a fresh file.
                } else if (offset > 0 && (status != HttpURLConnection.HTTP_PARTIAL ||
                        !conn.getHeaderField("Content-Range").startsWith("bytes " + offset + "-"))) {
                    throw new IOException("Invalid resumed download response");
                } else if (offset == 0 && status != HttpURLConnection.HTTP_OK) {
                    throw new IOException("Unexpected APK download response: " + status);
                }
                long written = offset;
                if (listener != null) listener.onProgress(written, release.size);
                try (InputStream input = conn.getInputStream();
                     FileOutputStream output = new FileOutputStream(partial, offset > 0)) {
                    byte[] buffer = new byte[65536];
                    long reported = written;
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        output.write(buffer, 0, count);
                        written += count;
                        if (written > release.size) throw new IOException("APK exceeds release size");
                        if (listener != null && (written - reported >= 262144 || written == release.size)) {
                            reported = written;
                            listener.onProgress(written, release.size);
                        }
                    }
                    output.getFD().sync();
                }
            } finally {
                conn.disconnect();
            }
        }
        if (partial.length() != release.size || !hash(partial).equals(release.sha256)) {
            // Keep no unverifiable bytes for a future resume attempt.
            partial.delete();
            throw new IOException("APK size or SHA-256 did not match GitHub release");
        }
        if (!partial.renameTo(completed)) throw new IOException("Cannot finalize downloaded APK");
        verifyArchive(context, completed);
        return completed;
    }

    /** Enforce package identity + exact current signer, even if release metadata was altered. */
    static void verifyArchive(Context context, File apk) throws Exception {
        PackageManager pm = context.getPackageManager();
        int flags = PackageManager.GET_SIGNING_CERTIFICATES;
        PackageInfo candidate = pm.getPackageArchiveInfo(apk.getAbsolutePath(), flags);
        PackageInfo installed = pm.getPackageInfo(context.getPackageName(), flags);
        if (candidate == null || !context.getPackageName().equals(candidate.packageName)) {
            throw new IOException("APK package name does not match installed app");
        }
        if (candidate.getLongVersionCode() <= installed.getLongVersionCode()) {
            throw new IOException("APK versionCode is not newer than the installed version");
        }
        if (candidate.signingInfo == null || installed.signingInfo == null ||
                !sameSigners(candidate.signingInfo.getApkContentsSigners(),
                             installed.signingInfo.getApkContentsSigners())) {
            throw new IOException("APK signing certificate does not match the installed app");
        }
    }

    private static boolean sameSigners(Signature[] a, Signature[] b) {
        if (a == null || b == null || a.length == 0 || a.length != b.length) return false;
        byte[][] left = new byte[a.length][];
        byte[][] right = new byte[b.length][];
        for (int i = 0; i < a.length; i++) {
            left[i] = a[i].toByteArray();
            right[i] = b[i].toByteArray();
        }
        java.util.Comparator<byte[]> comparator = (x, y) -> {
            for (int i = 0; i < Math.min(x.length, y.length); i++) {
                int d = (x[i] & 255) - (y[i] & 255);
                if (d != 0) return d;
            }
            return x.length - y.length;
        };
        Arrays.sort(left, comparator);
        Arrays.sort(right, comparator);
        for (int i = 0; i < left.length; i++) {
            if (!Arrays.equals(left[i], right[i])) return false;
        }
        return true;
    }

    static Intent installIntent(Context context, File apk) {
        Uri uri = FileProvider.getUriForFile(context,
            context.getPackageName() + ".fileprovider", apk);
        Intent intent = new Intent(Intent.ACTION_VIEW);
        intent.setDataAndType(uri, "application/vnd.android.package-archive");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        return intent;
    }

    private static String hash(File file) throws Exception {
        MessageDigest sha = MessageDigest.getInstance("SHA-256");
        try (InputStream in = new FileInputStream(file)) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) != -1) sha.update(buf, 0, n);
        }
        StringBuilder out = new StringBuilder(64);
        for (byte b : sha.digest()) out.append(String.format(Locale.ROOT, "%02x", b & 255));
        return out.toString();
    }

    private static byte[] readLimited(HttpURLConnection conn, int limit) throws IOException {
        try {
            if (conn.getResponseCode() != HttpURLConnection.HTTP_OK) {
                throw new IOException("HTTP " + conn.getResponseCode());
            }
            try (InputStream input = conn.getInputStream();
                 ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int n;
                while ((n = input.read(buffer)) != -1) {
                    if (bytes.size() + n > limit) throw new IOException("Release metadata too large");
                    bytes.write(buffer, 0, n);
                }
                return bytes.toByteArray();
            }
        } finally {
            conn.disconnect();
        }
    }

    private static HttpURLConnection open(String source, long offset) throws IOException {
        URL url = new URL(source);
        for (int hop = 0; hop < 6; hop++) {
            String host = url.getHost().toLowerCase(Locale.ROOT);
            if (!"https".equals(url.getProtocol()) || url.getPort() != -1 ||
                    !(host.equals("api.github.com") || host.equals("github.com") ||
                      host.equals("release-assets.githubusercontent.com") ||
                      host.equals("objects.githubusercontent.com"))) {
                throw new IOException("Untrusted APK update host");
            }
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setInstanceFollowRedirects(false);
            conn.setConnectTimeout(12000);
            conn.setReadTimeout(30000);
            conn.setRequestProperty("Accept", "application/vnd.github+json");
            conn.setRequestProperty("User-Agent", "GeneralsZH-Android-AppUpdater");
            if (offset > 0) conn.setRequestProperty("Range", "bytes=" + offset + "-");
            int status = conn.getResponseCode();
            if (status == 301 || status == 302 || status == 303 || status == 307 || status == 308) {
                String location = conn.getHeaderField("Location");
                conn.disconnect();
                if (location == null) throw new IOException("Missing download redirect");
                url = new URL(url, location);
                continue;
            }
            if (status != 200 && status != 206) {
                conn.disconnect();
                throw new IOException("GitHub HTTP " + status);
            }
            return conn;
        }
        throw new IOException("Too many download redirects");
    }
}
