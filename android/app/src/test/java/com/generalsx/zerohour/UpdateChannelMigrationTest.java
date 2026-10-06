package com.generalsx.zerohour;

import android.content.Context;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;

// GeneralsX @feature Codex 06/10/2026 Exercise actual updater migration without a network or operator key.
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28)
public class UpdateChannelMigrationTest {
    @Test public void legacySerialAndEngineAreNotTrustedButAutoPreferenceSurvives() throws Exception {
        Context ctx = RuntimeEnvironment.getApplication();
        ctx.getSharedPreferences("gx_update_own_v1", Context.MODE_PRIVATE).edit().clear().commit();
        ctx.getSharedPreferences("gx_update", Context.MODE_PRIVATE).edit()
            .putInt("serial", 12).putBoolean("auto_check", false).commit();
        File update = UpdateManager.updateDir(ctx);
        assertTrue(update.isDirectory() || update.mkdirs());
        File legacy = new File(update, "engine_active.txt");
        Files.write(legacy.toPath(), "99999".getBytes(StandardCharsets.US_ASCII));
        assertEquals(0, UpdateManager.acceptedSerial(ctx));
        assertFalse(UpdateManager.isAutoCheckEnabled(ctx));
        assertEquals(0, UpdateManager.activeEngineSeq(ctx));
        assertTrue(legacy.isFile());
        assertEquals("99999", new String(Files.readAllBytes(legacy.toPath()), StandardCharsets.US_ASCII));
        UpdateManager.setAutoCheckEnabled(ctx, true);
        assertTrue(UpdateManager.isAutoCheckEnabled(ctx));
        assertFalse(ctx.getSharedPreferences("gx_update", Context.MODE_PRIVATE).getBoolean("auto_check", true));
    }

    @Test public void unsignedCachedEngineCannotActivate() throws Exception {
        Context ctx = RuntimeEnvironment.getApplication();
        File update = UpdateManager.updateDir(ctx);
        assertTrue(update.isDirectory() || update.mkdirs());
        File dir = new File(update, "engine_own_v1/99999");
        assertTrue(dir.isDirectory() || dir.mkdirs());
        Files.write(new File(dir, "libmain.so").toPath(), new byte[]{1});
        Files.write(new File(dir, "libmain60.so").toPath(), new byte[]{2});
        Files.write(new File(update, "engine_active_own_v1.txt").toPath(), "99999".getBytes(StandardCharsets.US_ASCII));
        assertEquals(0, UpdateManager.activeEngineSeq(ctx));
        assertNull(UpdateManager.activeEngineLibrary(ctx, "../../other.so"));
    }
}
