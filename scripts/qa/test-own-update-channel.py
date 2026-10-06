#!/usr/bin/env python3
"""Host tests of production publisher/validator and source migration guards; no Android build."""
import base64
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('artifacts',ROOT/'scripts/update/update-artifacts.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
passed=[]

def reject(fn,name):
    try:fn()
    except (ValueError,KeyError,subprocess.CalledProcessError):passed.append(name)
    else:raise AssertionError('Unsafe input accepted: '+name)

def run(*cmd,**options):
    return subprocess.run(cmd,check=True,capture_output=True,**options)

with tempfile.TemporaryDirectory(prefix='gx-update-test-') as temp:
    d=Path(temp)
    run('openssl','genpkey','-algorithm','EC','-pkeyopt','ec_paramgen_curve:P-256','-out',str(d/'private.pem'))
    run('openssl','pkey','-in',str(d/'private.pem'),'-pubout','-out',str(d/'public.pem'))
    a.public_der(d/'public.pem');passed.append('own public P-256 validation')
    reject(lambda:a.public_der(d/'private.pem'),'private PEM rejected')
    (d/'upstream.pem').write_text('-----BEGIN PUBLIC KEY-----\n'+base64.b64encode(a.UPSTREAM_PUBLIC_DER).decode()+'\n-----END PUBLIC KEY-----\n')
    reject(lambda:a.public_der(d/'upstream.pem'),'upstream identity rejected')
    run('openssl','genpkey','-algorithm','EC','-pkeyopt','ec_paramgen_curve:P-384','-out',str(d/'other-private.pem'))
    run('openssl','pkey','-in',str(d/'other-private.pem'),'-pubout','-out',str(d/'other-public.pem'))
    reject(lambda:a.public_der(d/'other-public.pem'),'other EC curve rejected')
    publication=d/'publication';publication.mkdir()
    doc={'schema':1,'serial':1,'channel':a.CHANNEL,'config':{}}
    def sign(doc):
        (publication/'manifest.json').write_text(json.dumps(doc)+'\n')
        sig=run('openssl','dgst','-sha256','-sign',str(d/'private.pem'),str(publication/'manifest.json')).stdout
        (publication/'manifest.json.sig').write_bytes(base64.b64encode(sig)+b'\n')
    sign(doc)
    assert a.verify_directory(publication,d/'public.pem')==doc;passed.append('signed settings manifest verifies')
    (publication/'manifest.json').write_text('tampered')
    reject(lambda:a.verify_directory(publication,d/'public.pem'),'altered signed bytes rejected')
    sign(dict(doc,channel='MYSOREZ'))
    reject(lambda:a.verify_directory(publication,d/'public.pem'),'signed foreign channel rejected')
    sign(dict(doc,serial=0))
    reject(lambda:a.verify_directory(publication,d/'public.pem'),'zero serial rejected')
    sign(dict(doc,serial=True))
    reject(lambda:a.verify_directory(publication,d/'public.pem'),'boolean serial rejected')
    sign(dict(doc,engine={'seq':'../../escape'}))
    reject(lambda:a.verify_directory(publication,d/'public.pem'),'path-like engine sequence rejected')
    reject(lambda:a.native_stamp(b'not ELF','a'*40,3333),'non-ELF engine rejected')
    # Execute the real secret-signing script against isolated public-only source fixtures.
    fixture=d/'source';(fixture/'scripts/update').mkdir(parents=True)
    (fixture/'android/app/src/main/assets').mkdir(parents=True)
    for filename in ('sign-manifest.sh','update-artifacts.py'):
        shutil.copyfile(ROOT/'scripts/update'/filename,fixture/'scripts/update'/filename)
    shutil.copyfile(d/'public.pem',fixture/'android/app/src/main/assets/update-public.pem')
    prepared=d/'prepared';prepared.mkdir()
    (prepared/'manifest.json').write_text(json.dumps(doc)+'\n')
    runtime=d/'runtime';runtime.mkdir()
    environment=dict(os.environ,RUNNER_TEMP=str(runtime),UPDATE_SIGNING_KEY=(d/'private.pem').read_text())
    run('bash',str(fixture/'scripts/update/sign-manifest.sh'),str(prepared),env=environment)
    a.verify_directory(prepared,d/'public.pem')
    assert not list(runtime.iterdir()), 'Signing temp files were not removed'
    passed.append('production secret signer: matching own identity, exact bytes and private-temp cleanup')
    environment['UPDATE_SIGNING_KEY']=(d/'other-private.pem').read_text()
    rejected=subprocess.run(['bash',str(fixture/'scripts/update/sign-manifest.sh'),str(prepared)],env=environment,capture_output=True)
    assert rejected.returncode!=0 and not list(runtime.iterdir())
    passed.append('production secret signer: wrong secret identity refused and cleaned')
    environment.pop('UPDATE_SIGNING_KEY')
    rejected=subprocess.run(['bash',str(fixture/'scripts/update/sign-manifest.sh'),str(prepared)],env=environment,capture_output=True)
    assert rejected.returncode!=0
    passed.append('production signer missing secret fails closed')
    # Execute the production publication script against a local bare remote.
    # Only transport is redirected; validation, branch serial guard and normal push are real.
    shutil.copyfile(ROOT/'scripts/update/push-updates-branch.sh',fixture/'scripts/update/push-updates-branch.sh')
    real_git=shutil.which('git')
    run(real_git,'init','--quiet','--initial-branch=main',str(fixture))
    run(real_git,'-C',str(fixture),'remote','add','origin','https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port.git')
    bare=d/'remote.git';run(real_git,'init','--quiet','--bare',str(bare))
    tools=d/'tools';tools.mkdir()
    wrapper=tools/'git'
    wrapper.write_text('#!/usr/bin/env python3\nimport os,sys\nargs=sys.argv[1:]\n'+
        'if "remote" in args and "add" in args: args=[('+repr(str(bare))+' if x=="https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port.git" else x) for x in args]\n'+
        'os.execv('+repr(real_git)+',['+repr(real_git)+']+args)\n')
    wrapper.chmod(0o755)
    transport=dict(os.environ,PATH=str(tools)+os.pathsep+os.environ['PATH'])
    run('bash',str(fixture/'scripts/update/push-updates-branch.sh'),str(prepared),cwd=fixture,env=transport)
    first=run(real_git,'--git-dir',str(bare),'rev-parse','refs/heads/updates').stdout
    stale=subprocess.run(['bash',str(fixture/'scripts/update/push-updates-branch.sh'),str(prepared)],cwd=fixture,env=transport,capture_output=True)
    assert stale.returncode!=0 and run(real_git,'--git-dir',str(bare),'rev-parse','refs/heads/updates').stdout==first
    passed.append('production publisher initial signed branch and stale-serial rejection')
    (prepared/'manifest.json').write_text(json.dumps(dict(doc,serial=2))+'\n')
    signenv=dict(os.environ,RUNNER_TEMP=str(runtime),UPDATE_SIGNING_KEY=(d/'private.pem').read_text())
    run('bash',str(fixture/'scripts/update/sign-manifest.sh'),str(prepared),env=signenv)
    run('bash',str(fixture/'scripts/update/push-updates-branch.sh'),str(prepared),cwd=fixture,env=transport)
    history=run(real_git,'--git-dir',str(bare),'rev-list','--count','refs/heads/updates').stdout.strip()
    assert history==b'2'
    passed.append('production publisher fast-forward retains previous history')
    (prepared/'private.pem').write_text('forbidden fixture (no real secret)')
    rejected=subprocess.run(['bash',str(fixture/'scripts/update/push-updates-branch.sh'),str(prepared)],cwd=fixture,env=transport,capture_output=True)
    assert rejected.returncode!=0
    passed.append('unexpected publication files rejected before push')
    # Compile the real dependency-free Java trust validator when a JDK is available.
    if shutil.which('javac'):
        classes=d/'classes';classes.mkdir()
        run('javac','-d',str(classes),str(ROOT/'android/app/src/main/java/com/generalsx/zerohour/UpdateTrust.java'),str(ROOT/'scripts/qa/update/UpdateTrustTest.java'))
        print(run('java','-cp',str(classes),'com.generalsx.zerohour.UpdateTrustTest').stdout.decode().strip())
    else:
        print('NOT TESTED locally: UpdateTrust JVM checks (javac absent)')

source=(ROOT/'android/app/src/main/java/com/generalsx/zerohour/UpdateManager.java').read_text()
assert 'MYSOREZ' not in source and 'PUBLIC_KEY_B64' not in source
assert 'gx_update_own_v1' in source and 'engine_own_v1' in source
assert 'ctx.getSharedPreferences("gx_update", Context.MODE_PRIVATE).getBoolean(KEY_AUTO, true)' in source
assert 'verify(ctx, body, signature)' in source
assert 'writeBytes(new File(target, "manifest.json"), manifestBytes)' in source
assert 'seq < readInt(activeEngineMarker(ctx))' in source
assert 'cannot replace an activated engine with different bytes' in source
assert 'remote_config.ini' in source and 'boot_pending' in source
assert '/storage/emulated' not in source
passed.append('source guards: isolated channel, legacy preference preserved, retained signed metadata and downgrade protection')

# Test the production APK parser on actual independently verified Engine 3333 bytes, if available.
apk=ROOT.parent/'artifacts/engine-3277-merged/GeneralsZH-Engine3333-debug.apk'
if apk.is_file():
    sequence,commit,libraries=a.apk_payload(apk)
    assert sequence==3333 and commit=='c3043dcfb89570351ca33adfa786bcede8532843'
    assert len(libraries)==17
    passed.append('actual Engine 3333 APK: complete history/tree/provenance and both native Git symbols')
    with tempfile.TemporaryDirectory(prefix='gx-update-apk-publisher-') as temporary:
        out=Path(temporary)/'prepared'
        run('python3',str(ROOT/'scripts/update/publish-update.py'),'--apk',str(apk),'--serial','1','--out',str(out))
        doc=json.loads((out/'manifest.json').read_bytes())
        assert doc['engine']['seq']==3333 and doc['engine']['source_commit']==commit
        assert set(doc['engine']['requires_libs'])==set(libraries)-set(a.ENGINE_LIBS)
        assert 'support' not in doc
        for name in a.ENGINE_LIBS:
            payload=gzip.decompress((out/f'engine/3333/{name}.gz').read_bytes())
            assert payload==libraries[name] and a.digest(payload)==doc['engine']['files'][name]['sha256']
        passed.append('production APK publisher: correct own URLs, exact dual engine bytes, dependency hashes, no upstream support identity')

    reject(lambda:a.native_stamp(libraries['libmain.so'],commit,sequence+1),'false native build label rejected')
    reject(lambda:a.native_stamp(libraries['libmain.so'],'a'*40,sequence),'false native source commit rejected')
else:
    print('NOT TESTED locally: real baseline APK fixture absent')
for name in passed:print('PASS:',name)
print('PASS:',len(passed),'own-channel host checks')
