#!/usr/bin/env python3
"""Validate actual APK/native engine provenance before signing or publication."""
# GeneralsX @feature Codex 06/10/2026 Verify native stamps and dependency identity for engine-only updates.
import base64
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import zipfile

ENGINE_LIBS = ('libmain.so', 'libmain60.so')
BASE_URL = 'https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/'
CHANNEL = 'koreazolfakar-droid/mobile-v4/v1'
ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_PUBLIC_DER = base64.b64decode('MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEFjy+4K0lTRmnwQe+nQqXreCMtJehCl1wiYNgq5Rr/MHWkDukps0eUbmuyxSenyFL4T5zo+WBIFeLDO5PXFoG/A==')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def public_der(path):
    data = Path(path).read_bytes()
    if not data.strip().startswith(b'-----BEGIN PUBLIC KEY-----') or b'PRIVATE' in data:
        raise ValueError('Expected public SPKI PEM only')
    info = subprocess.check_output(['openssl', 'pkey', '-pubin', '-in', str(path), '-text', '-noout'])
    if b'ASN1 OID: prime256v1' not in info:
        raise ValueError('Update public key must be ECDSA P-256')
    der = subprocess.check_output(['openssl', 'pkey', '-pubin', '-in', str(path), '-outform', 'DER'])
    if der == UPSTREAM_PUBLIC_DER:
        raise ValueError('Our channel must not reuse the upstream signing identity')
    return der


def native_stamp(data, commit, sequence):
    if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
        raise ValueError('Expected an AArch64 ELF64 engine')
    # Read the exported Git metadata from file-backed dynamic symbols, never by string search.
    offset = struct.unpack_from('<Q', data, 40)[0]
    width, count = struct.unpack_from('<HH', data, 58)
    if width != 64 or not count or offset + width * count > len(data):
        raise ValueError('Missing ELF section table')
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + width * i) for i in range(count)]
    values = {}
    for section in sections:
        if section[1] != 11:  # SHT_DYNSYM
            continue
        strings = sections[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        if section[9] != 24 or section[4] + section[5] > len(data):
            raise ValueError('Invalid ELF dynamic symbols')
        for position in range(section[4], section[4] + section[5], 24):
            name, info, _, index, address, size = struct.unpack_from('<IBBHQQ', data, position)
            if name >= len(names) or index == 0 or index >= len(sections) or info & 15 != 1:
                continue
            label = names[name:].split(b'\0', 1)[0]
            if label not in (b'GitSHA1', b'GitRevision'):
                continue
            backing = sections[index]
            start = backing[4] + address - backing[3]
            if start < backing[4] or start + size > backing[4] + backing[5] or start + size > len(data):
                raise ValueError('Native metadata is not file-backed')
            values[label] = data[start:start + size]
    if values.get(b'GitSHA1', b'').rstrip(b'\0') != commit.encode('ascii'):
        raise ValueError('Native GitSHA1 does not match provenance')
    if values.get(b'GitRevision') != struct.pack('<i', sequence):
        raise ValueError('Native GitRevision does not match provenance')


def validate_source(commit, sequence):
    if not re.fullmatch('[0-9a-f]{40}', commit) or sequence <= 0:
        raise ValueError('Invalid engine source identity')
    if subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--is-shallow-repository'], text=True).strip() != 'false':
        raise ValueError('Engine publication requires complete source history')
    count = int(subprocess.check_output(['git', '-C', str(ROOT), 'rev-list', '--count', commit], text=True))
    if count != sequence:
        raise ValueError('Engine sequence is not the real complete-history source count')


def apk_payload(apk):
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError('Invalid/duplicate APK ZIP payload')
        metadata = json.loads(archive.read('assets/engine_provenance.json'))
        sequence = int(archive.read('assets/engine_build.txt').strip())
        if metadata.get('schema') != 1 or metadata.get('engine_build') != sequence:
            raise ValueError('APK engine metadata differs from provenance')
        libraries = {n.removeprefix('lib/arm64-v8a/'): archive.read(n) for n in names
                     if n.startswith('lib/arm64-v8a/') and n.endswith('.so')}
        expected = metadata['native_libraries']
        if set(expected) != set(libraries) or not set(ENGINE_LIBS) <= set(libraries):
            raise ValueError('APK native library set is incomplete')
        validate_source(metadata['source_commit'], sequence)
        tree = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', metadata['source_commit'] + '^{tree}'], text=True).strip()
        if metadata.get('source_tree') != tree:
            raise ValueError('APK engine source tree differs from provenance')
        for name, data in libraries.items():
            if expected[name] != {'sha256': digest(data), 'size': len(data)}:
                raise ValueError('APK native payload differs from provenance: ' + name)
            if name in ENGINE_LIBS:
                native_stamp(data, metadata['source_commit'], sequence)
        if digest(libraries[ENGINE_LIBS[0]]) == digest(libraries[ENGINE_LIBS[1]]):
            raise ValueError('Rate slots contain identical engines')
        return sequence, metadata['source_commit'], libraries


def verify_manifest(directory, public_key):
    directory = Path(directory)
    public_der(public_key)
    body = (directory / 'manifest.json').read_bytes()
    signature = base64.b64decode((directory / 'manifest.json.sig').read_bytes().strip(), validate=True)
    with tempfile.TemporaryDirectory(prefix='gx-update-verify-') as temporary:
        sig = Path(temporary) / 'signature.der'
        sig.write_bytes(signature)
        subprocess.run(['openssl', 'dgst', '-sha256', '-verify', str(public_key),
                        '-signature', str(sig), str(directory / 'manifest.json')],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    manifest = json.loads(body)
    if manifest.get('schema') != 1 or manifest.get('channel') != CHANNEL or type(manifest.get('serial')) is not int or manifest['serial'] <= 0:
        raise ValueError('Invalid signed update identity/schema/serial')
    engine = manifest.get('engine')
    if engine and (type(engine.get('seq')) is not int or engine['seq'] <= 0):
        raise ValueError('Invalid engine sequence')
    return manifest


def verify_directory(directory, public_key):
    directory = Path(directory)
    manifest = verify_manifest(directory, public_key)
    engine = manifest.get('engine')
    allowed = {'manifest.json', 'manifest.json.sig'}
    if engine:
        import gzip
        seq = engine['seq']
        validate_source(engine['source_commit'], seq)
        if set(engine['files']) != set(ENGINE_LIBS) or not engine.get('requires_libs'):
            raise ValueError('Both engine variants and dependency hashes are required')
        for name in ENGINE_LIBS:
            entry = engine['files'][name]
            relative = f'engine/{seq}/{name}.gz'
            allowed.add(relative)
            if entry['url'] != BASE_URL + relative or not 0 < entry['size'] <= 256 * 1024 * 1024:
                raise ValueError('Invalid engine URL/size')
            with gzip.open(directory / relative) as stream:
                data = stream.read(entry['size'] + 1)
            if len(data) != entry['size'] or digest(data) != entry['sha256']:
                raise ValueError('Engine payload differs from signed identity')
            native_stamp(data, engine['source_commit'], seq)
        for name, sha in engine['requires_libs'].items():
            if not re.fullmatch(r'lib[A-Za-z0-9_+.-]+\.so', name) or '..' in name or name in ENGINE_LIBS or not re.fullmatch('[0-9a-f]{64}', sha):
                raise ValueError('Invalid dependency identity')
    support = manifest.get('support')
    if support:
        relative = support['url'].removeprefix(BASE_URL)
        if not support['url'].startswith(BASE_URL) or not re.fullmatch(r'support/[a-f0-9]{16}\.json', relative):
            raise ValueError('Invalid own support URL')
        payload = (directory / relative).read_bytes()
        if len(payload) != support['size'] or digest(payload) != support['sha256']:
            raise ValueError('Support payload differs from signed identity')
        allowed.add(relative)
    if manifest.get('config', {}).get('datapack_manifest_url') == BASE_URL + 'datapack-manifest.json':
        allowed.add('datapack-manifest.json')
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('Publication symlinks are forbidden')
        if path.is_file():
            if path.relative_to(directory).as_posix() not in allowed:
                raise ValueError('Unexpected publication file: ' + path.name)
            if path.suffix != '.gz' and b'PRIVATE KEY-----' in path.read_bytes():
                raise ValueError('Private key material is forbidden in publication')
    return manifest
