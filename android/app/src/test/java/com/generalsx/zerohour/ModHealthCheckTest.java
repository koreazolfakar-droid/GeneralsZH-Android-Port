package com.generalsx.zerohour;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import java.io.File;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import static org.junit.Assert.*;

public class ModHealthCheckTest {
    @Rule public TemporaryFolder temp = new TemporaryFolder();

    private File writeBig(File file, int offset, int size) throws Exception {
        byte[] label = "Data/INI/test.ini".getBytes(StandardCharsets.US_ASCII);
        int header = 16 + 8 + label.length + 1;
        int total = Math.max(header + 8, offset + size);
        ByteBuffer buf = ByteBuffer.allocate(total);
        buf.put("BIGF".getBytes(StandardCharsets.US_ASCII));
        buf.putInt(total).putInt(1).putInt(header).putInt(offset).putInt(size)
            .put(label).put((byte) 0);
        Files.write(file.toPath(), buf.array());
        return file;
    }

    @Test public void scansOriginalFilesWithoutReadingHugePayloads() throws Exception {
        File root = temp.newFolder("Mods");
        File mod = new File(root, "Project X Remastered");
        assertTrue(mod.mkdir());
        File data = new File(mod,"Data/Scripts");
        assertTrue(data.mkdirs());
        assertTrue(new File(mod,"Window").mkdir());
        Files.write(new File(data,"Scripts.ini").toPath(), new byte[]{1,2,3});
        File big = writeBig(new File(mod,"!!ProjectXRe_INI.big"), 48, 4);
        File nested = new File(mod,"extra");
        assertTrue(nested.mkdir());
        File nestedBig = writeBig(new File(nested,"Other.big"), 48, 4);
        byte[] previous = Files.readAllBytes(big.toPath());

        ModHealthCheck.Result scan = ModHealthCheck.scan(mod);
        assertEquals(2, scan.archives);
        assertEquals(2, scan.validArchives);
        assertEquals(0, scan.invalidArchives);
        assertEquals(2, scan.archivedEntries);
        assertEquals(1, scan.looseFiles);
        assertEquals(1, scan.nestedArchives);
        assertTrue(scan.dataFolder);
        assertTrue(scan.windowFolder);
        assertFalse(scan.truncated);
        assertArrayEquals(previous, Files.readAllBytes(big.toPath()));
        assertTrue(nestedBig.isFile());
    }

    @Test public void corruptBigIsFlaggedWithoutDeletingOrReplacingIt() throws Exception {
        File mod = temp.newFolder("Standalone");
        File corrupt = new File(mod,"broken.big");
        Files.write(corrupt.toPath(), "BAD!".getBytes(StandardCharsets.US_ASCII));
        byte[] content = Files.readAllBytes(corrupt.toPath());
        ModHealthCheck.Result result = ModHealthCheck.scan(mod);
        assertEquals(1, result.archives);
        assertEquals(1, result.invalidArchives);
        assertEquals(0, result.validArchives);
        assertEquals(1, result.issues().size());
        assertEquals("broken.big", result.issues().get(0));
        assertArrayEquals(content, Files.readAllBytes(corrupt.toPath()));
    }

    @Test public void outOfBoundsIndexedArchiveIsRejected() throws Exception {
        File big = writeBig(temp.newFile("overflow.big"), 4095, 8);
        // The structural table itself is valid, but the payload is no longer there.
        try (RandomAccessFile file = new RandomAccessFile(big,"rw")) {
            file.setLength(64);
        }
        assertEquals(-1, ModHealthCheck.checkBigTable(big));
    }

    @Test public void hugeSparseBigIsOnlyReadThroughItsSmallIndex() throws Exception {
        File big = temp.newFile("large.big");
        try (RandomAccessFile file = new RandomAccessFile(big,"rw")) {
            file.write("BIGF".getBytes(StandardCharsets.US_ASCII));
            file.writeInt(0);
            file.writeInt(0);
            file.writeInt(16);
            file.setLength(1800000000L);
        }
        assertEquals(0, ModHealthCheck.checkBigTable(big));
        ModHealthCheck.Result result = ModHealthCheck.scan(big);
        assertEquals(1, result.validArchives);
        assertEquals(1800000000L, result.bytes);
    }

    @Test public void ignoresSymlinkOutsideTheMod() throws Exception {
        File folder = temp.newFolder("SafeMod");
        File outside = temp.newFile("outside.big");
        Files.write(outside.toPath(), "INVALID!".getBytes(StandardCharsets.US_ASCII));
        Files.createSymbolicLink(new File(folder,"linked.big").toPath(), outside.toPath());
        ModHealthCheck.Result result = ModHealthCheck.scan(folder);
        assertEquals(0, result.archives);
        assertEquals(1, result.symlinks);
        assertEquals(0, result.invalidArchives);
    }

    @Test public void interruptedInspectionReportsIncomplete() throws Exception {
        File folder = temp.newFolder("Interrupted");
        Thread.currentThread().interrupt();
        try {
            ModHealthCheck.Result result = ModHealthCheck.scan(folder);
            assertTrue(result.cancelled);
            assertTrue(result.truncated);
        } finally {
            Thread.interrupted();
        }
    }
}
