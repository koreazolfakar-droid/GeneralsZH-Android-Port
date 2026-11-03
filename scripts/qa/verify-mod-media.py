#!/usr/bin/env python3
"""Read-only BIG media coverage check; does not alter game/mod archive priority.

Usage: python scripts/qa/verify-mod-media.py --root /retail/root --root /active/mod
"""
import argparse
from pathlib import Path
import struct
import sys

TARGETS = (
    ('texture', 'trstrtholecvr.tga'),
    ('texture', 'ru-navalyard.tga'),
    ('music', 'CHI_01.mp3'),
)


def members(path):
    with path.open('rb') as f:
        size = path.stat().st_size
        header = f.read(16)
        if len(header) != 16 or header[:4] not in (b'BIGF', b'BIG4'):
            raise ValueError('invalid BIG signature/header')
        count, end = struct.unpack('>II', header[8:16])
        if end < 16 or end > size or count > 200000 or count > (end - 16) // 9:
            raise ValueError('invalid BIG directory boundaries')
        for _ in range(count):
            if f.tell() + 9 > end:
                raise ValueError('truncated BIG entry')
            start, length = struct.unpack('>II', f.read(8))
            if start > size or length > size - start:
                raise ValueError('BIG member outside archive')
            name = bytearray()
            for _ in range(4096):
                if f.tell() >= end:
                    raise ValueError('unterminated BIG filename')
                part = f.read(1)
                if part == b'\0':
                    break
                name += part
            else:
                raise ValueError('overlong BIG filename')
            if not name:
                raise ValueError('empty BIG filename')
            position = f.tell()
            f.seek(start)
            peek = f.read(min(32, length))
            f.seek(position)
            yield name.decode('latin1').replace('\\', '/'), peek, length


def looks_valid(extension, peek, size):
    if extension == '.tga':
        if size < 18 or len(peek) < 18:
            return False
        width, height = struct.unpack_from('<HH', peek, 12)
        return width > 0 and height > 0 and peek[2] in (2, 10) and peek[16] in (24, 32)
    if extension == '.dds':
        return size >= 128 and peek[:4] == b'DDS '
    if extension == '.mp3':
        return size > 4 and (peek.startswith(b'ID3') or
                             (len(peek) > 1 and peek[0] == 0xff and (peek[1] & 0xe0) == 0xe0))
    return None


def inspect(roots):
    matches = {name: [] for _, name in TARGETS}
    exceptions = []
    bigs = sorted({p for root in roots for p in root.rglob('*')
                   if p.is_file() and p.suffix.lower() == '.big'})
    for path in bigs:
        try:
            for member, peek, size in members(path):
                leaf = member.rsplit('/', 1)[-1]
                for kind, expected in TARGETS:
                    base = expected.rsplit('.', 1)[0]
                    candidate = leaf.casefold()
                    options = (expected.casefold(),
                               base.casefold() + ('.dds' if kind == 'texture' else '.wav'))
                    if candidate not in options:
                        continue
                    ext = Path(leaf).suffix.lower()
                    valid = looks_valid(ext, peek, size)
                    matches[expected].append((str(path), member, size, valid,
                                              leaf.casefold() == expected.casefold()))
        except (OSError, ValueError) as exc:
            exceptions.append((str(path), str(exc)))
    for kind, expected in TARGETS:
        found = matches[expected]
        print(f'{kind.upper()} {expected}: ' +
              ('CANDIDATES FOUND' if found else 'NOT FOUND IN INSPECTED BIGS'))
        for archive, member, size, valid, same in found:
            print(f'  {archive} :: {member} ({size} bytes, header={valid}, exact-extension={same})')
    for path, error in exceptions:
        print(f'INVALID BIG: {path}: {error}', file=sys.stderr)
    print(f'Inspected {len(bigs)} archive(s); malformed/unreadable={len(exceptions)}')
    return len(exceptions) == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, action='append', required=True,
                        help='Retail or active mod folder')
    args = parser.parse_args()
    sys.exit(0 if inspect(args.root) else 2)
