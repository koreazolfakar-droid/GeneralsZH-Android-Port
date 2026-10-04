package com.generalsx.zerohour;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import java.io.File;
import java.io.RandomAccessFile;
import java.nio.file.Files;
import static org.junit.Assert.*;

// GeneralsX @feature Android port 04/10/2026 Size scans must never follow links or read payloads.
public class ModLibraryInfoTest {
    @Rule public TemporaryFolder temp = new TemporaryFolder();

    @Test public void countsNestedFilesWithoutFollowingLinks() throws Exception {
        File root = temp.newFolder("Mods");
        File mod = new File(root, "Fixture");
        assertTrue(mod.mkdir());
        Files.write(new File(mod, "one.big").toPath(), new byte[19]);
        File nested = new File(mod, "Data");
        assertTrue(nested.mkdir());
        Files.write(new File(nested, "two.big").toPath(), new byte[31]);
        File outside = temp.newFile("base.big");
        Files.write(outside.toPath(), new byte[1024]);
        Files.createSymbolicLink(new File(mod, "outside.big").toPath(), outside.toPath());
        Files.createSymbolicLink(new File(mod, "cycle").toPath(), mod.toPath());
        assertEquals(50, ModLibraryInfo.measure(mod));
        assertTrue(ModLibraryInfo.isManagedEntry(root, mod));
        assertFalse(ModLibraryInfo.isManagedEntry(root, outside));
        assertFalse(ModLibraryInfo.isManagedEntry(root, new File(root, "../base.big")));
    }

    @Test public void reportsLargeArchivesFromMetadataOnly() throws Exception {
        File big = temp.newFile("large.big");
        long bytes = 1800000000L;
        try (RandomAccessFile file = new RandomAccessFile(big, "rw")) { file.setLength(bytes); }
        assertEquals(bytes, ModLibraryInfo.measure(big));
    }

    @Test public void rejectsRootSymlinkAndMarksMissingSizeUnknown() throws Exception {
        File root = temp.newFolder("Mods");
        File target = temp.newFile("vanilla.big");
        File link = new File(root, "Escape.big");
        Files.createSymbolicLink(link.toPath(), target.toPath());
        assertFalse(ModLibraryInfo.isManagedEntry(root, link));
        assertEquals(-1, ModLibraryInfo.measure(link));
        assertEquals(-1, ModLibraryInfo.measure(new File(root, "missing")));
        assertEquals(0, ModLibraryInfo.measure(root));
    }

    @Test public void interruptedScanDoesNotPresentPartialTotal() throws Exception {
        File root = temp.newFolder("empty");
        Thread.currentThread().interrupt();
        try { assertEquals(-1, ModLibraryInfo.measure(root)); }
        finally { Thread.interrupted(); }
    }
}
