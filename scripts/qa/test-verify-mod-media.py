#!/usr/bin/env python3
"""Synthetic BIGF fixture for read-only media archive diagnostics."""
from pathlib import Path
import subprocess
import struct
import sys
import tempfile

SCRIPT = Path(__file__).with_name('verify-mod-media.py')


def write_big(path, entries):
    header_size = 16 + sum(8 + len(name.encode('latin1')) + 1 for name, _ in entries)
    table = bytearray()
    data = bytearray()
    offset = header_size
    for name, payload in entries:
        table += struct.pack('>II', offset, len(payload))
        table += name.encode('latin1') + b'\0'
        data += payload
        offset += len(payload)
    path.write_bytes(b'BIGF' + struct.pack('>III', offset, len(entries), header_size) + table + data)


def main():
    tga = bytes([0, 0, 2]) + bytes(9) + struct.pack('<HH', 64, 64) + bytes([24, 0]) + bytes(32)
    dds = b'DDS ' + bytes(124)
    mp3 = b'ID3' + bytes(24)
    with tempfile.TemporaryDirectory(prefix='gzh-media-qa-') as tmp:
        path = Path(tmp) / 'textures.big'
        write_big(path, [
            ('Data\\Art\\Textures\\TRSTRTHOLECVR.TGA', tga),
            ('Data\\Art\\Textures\\RU-NAVALYARD.DDS', dds),
            ('Data\\Audio\\Tracks\\CHI_01.mp3', mp3),
        ])
        proc = subprocess.run([sys.executable, str(SCRIPT), '--root', str(tmp)],
                              check=True, capture_output=True, text=True)
        for text in ('TEXTURE trstrtholecvr.tga: CANDIDATES FOUND',
                     'TEXTURE ru-navalyard.tga: CANDIDATES FOUND',
                     'MUSIC CHI_01.mp3: CANDIDATES FOUND',
                     'header=True', 'exact-extension=False'):
            assert text in proc.stdout, (text, proc.stdout)
        path.write_bytes(b'BIGF' + bytes(12))
        invalid = subprocess.run([sys.executable, str(SCRIPT), '--root', str(tmp)],
                                 capture_output=True, text=True)
        assert invalid.returncode == 2
        assert 'INVALID BIG' in invalid.stderr
    print('PASS: BIGF media coverage / extension / corrupt header fixture')


if __name__ == '__main__':
    main()
