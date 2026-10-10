package com.generalsx.zerohour;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/** Pure decision guards. Download/package/signature verification needs an Android APK fixture. */
public class ApkUpdateManagerTest {
    @Test public void newerReleaseTagsAllowTheCurrentRepositorySuffix() {
        assertTrue(ApkUpdateManager.isNewerVersion(
            "v1.4.7-launcher-day-night", "1.4.0"));
        assertTrue(ApkUpdateManager.isNewerVersion("v2.0.0", "1.99.99"));
        assertFalse(ApkUpdateManager.isNewerVersion("v1.4.7", "1.4.7"));
        assertFalse(ApkUpdateManager.isNewerVersion("v1.4.6", "1.4.7"));
        assertFalse(ApkUpdateManager.isNewerVersion("v1.4.8", "1.5.0"));
        assertFalse(ApkUpdateManager.isNewerVersion("latest", "1.4.0"));
        assertFalse(ApkUpdateManager.isNewerVersion("v999999999999999999999.1.0", "1.4.0"));
    }

    @Test public void untrustedApkDownloadLocationsAreRejected() {
        assertTrue(ApkUpdateManager.trustedDownloadUrl(
            "https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/"
                + "releases/download/v1.4.7-launcher-day-night/app.apk"));
        assertFalse(ApkUpdateManager.trustedDownloadUrl(
            "http://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/"
                + "releases/download/v1.4.7/app.apk"));
        assertFalse(ApkUpdateManager.trustedDownloadUrl(
            "https://evil.example/koreazolfakar-droid/GeneralsZH-Android-Port/"
                + "releases/download/v1.4.7/app.apk"));
        assertFalse(ApkUpdateManager.trustedDownloadUrl(
            "https://github.com/another-owner/another-repo/releases/download/v1.4.7/app.apk"));
        assertFalse(ApkUpdateManager.trustedDownloadUrl(
            "https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/"
                + "releases/download/v1.4.7/not-an-apk.zip"));
        assertFalse(ApkUpdateManager.trustedDownloadUrl(
            "https://github.com:8443/koreazolfakar-droid/GeneralsZH-Android-Port/"
                + "releases/download/v1.4.7/app.apk"));
    }
}
