package com.generalsx.zerohour;

import android.content.Context;
import android.net.Uri;
import java.io.File;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;

// GeneralsX @feature Android port 04/10/2026 Guard transactional import and cancellation.
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28)
public class ModImportRegressionTest {
    @Rule public TemporaryFolder temp = new TemporaryFolder();
    private Context context;
    private File game, mods, existing;
    private final byte[] original = {8,7,6,5};

    @Before public void prepare() throws Exception {
        context = RuntimeEnvironment.getApplication();
        game = temp.newFolder("game");
        mods = new File(game, "Mods");
        assertTrue(mods.mkdir());
        existing = new File(mods, "Installed.big");
        Files.write(existing.toPath(), original);
        context.getSharedPreferences(SetupActivity.PREFS_NAME, Context.MODE_PRIVATE).edit()
            .clear().putString(SetupActivity.PREF_GAME_PATH, game.getAbsolutePath()).commit();
        assertTrue(ModManager.setActiveMod(context, existing));
    }

    private byte[] big() throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        DataOutputStream out = new DataOutputStream(bytes);
        out.writeBytes("BIGF");
        out.writeInt(0); // Existing validator ignores the little-endian archive-size field.
        out.writeInt(0);
        out.writeInt(16);
        return bytes.toByteArray();
    }

    private File document(String name, byte[] bytes) throws Exception {
        File input = new File(temp.getRoot(), name);
        Files.write(input.toPath(), bytes);
        return input;
    }

    private File zip(String filename, String entry, byte[] bytes) throws Exception {
        ByteArrayOutputStream contents = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(contents)) {
            zip.putNextEntry(new ZipEntry(entry));
            zip.write(bytes);
            zip.closeEntry();
        }
        return document(filename, contents.toByteArray());
    }

    private void unchanged() throws Exception {
        assertArrayEquals(original, Files.readAllBytes(existing.toPath()));
        assertEquals(existing, ModManager.getActiveMod(context));
        File staging = new File(mods, ".installing");
        assertTrue(!staging.exists() || staging.list().length == 0);
    }

    @Test public void importsBigAndKeepsExistingChoiceUntilExplicitActivation() throws Exception {
        File input = document("Valid.BIG", big());
        ModImportService.Result first = ModImportService.importDocument(context, Uri.fromFile(input));
        assertEquals(1, first.bigCount);
        assertEquals(16, first.bytes);
        assertArrayEquals(big(), Files.readAllBytes(first.installed.toPath()));
        unchanged();
        ModImportService.Result second = ModImportService.importDocument(context, Uri.fromFile(input));
        assertNotEquals(first.installed, second.installed);
        assertArrayEquals(big(), Files.readAllBytes(first.installed.toPath()));
        assertTrue(ModManager.setActiveMod(context, second.installed));
        assertEquals(second.installed, ModManager.getActiveMod(context));
    }

    @Test public void importsZipWithNestedBigWithoutChangingLiveRoot() throws Exception {
        File live = new File(game, "vanilla.big");
        Files.write(live.toPath(), original);
        ModImportService.Result result = ModImportService.importDocument(context,
            Uri.fromFile(zip("Package.zip", "Data/valid.big", big())));
        assertTrue(result.installed.isDirectory());
        assertEquals(1, result.bigCount);
        assertArrayEquals(big(), Files.readAllBytes(new File(result.installed,"Data/valid.big").toPath()));
        assertArrayEquals(original, Files.readAllBytes(live.toPath()));
        unchanged();
    }

    @Test public void corruptBigFailsWithoutDestroyingInstalledMod() throws Exception {
        assertThrows(IOException.class, () -> ModImportService.importDocument(context,
            Uri.fromFile(document("Corrupt.big", new byte[32]))));
        unchanged();
        assertEquals(1, ModManager.listMods(context).size());
    }

    @Test public void traversalAndAbsoluteZipPathsCannotEscapeStaging() throws Exception {
        for (String entry : new String[] {"../Installed.big", "/vanilla.big", "Data/../../escape.big"}) {
            File input = zip("Unsafe.zip", entry, big());
            assertThrows(IOException.class, () -> ModImportService.importDocument(context, Uri.fromFile(input)));
            unchanged();
        }
        assertFalse(new File(game, "escape.big").exists());
        assertFalse(new File(game, "vanilla.big").exists());
    }

    // GeneralsX @feature Android port 04/10/2026 Cancellation stays transactional.
    @Test public void cancellationRemovesStagingAndKeepsInstalledModsUntouched() throws Exception {
        Uri uri = Uri.parse("content://test.mod.documents/Cancellable.big");
        ModImportService.CancellationSignal cancellation = new ModImportService.CancellationSignal();
        InputStream stream = new InputStream() {
            private int reads;
            @Override public int read() { return -1; }
            @Override public int read(byte[] bytes, int offset, int length) {
                if (reads++ == 0) {
                    java.util.Arrays.fill(bytes, offset, offset + Math.min(length, 64), (byte) 1);
                    cancellation.cancel();
                    return Math.min(length, 64);
                }
                return -1;
            }
        };
        org.robolectric.Shadows.shadowOf(context.getContentResolver()).registerInputStream(uri, stream);

        assertThrows(ModImportService.ImportCancelledException.class,
            () -> ModImportService.importDocument(context, uri, cancellation));
        unchanged();
        assertEquals(1, ModManager.listMods(context).size());
    }
}
