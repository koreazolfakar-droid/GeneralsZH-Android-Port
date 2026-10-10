#!/usr/bin/env python3
"""Reuse verified complete engine state; never bootstrap native dependencies or publish."""
# GeneralsX @build Codex 08/10/2026 Promote the verified cache-host builder to the mobile branch.
import hashlib, json, os, pathlib, re, shutil, struct, subprocess, sys, zipfile
root = pathlib.Path.cwd()
tools = pathlib.Path(os.environ['GX_BASELINE_TOOLS'])
out = root / 'baseline-report'
out.mkdir(exist_ok=True)
common = root / 'build/android-vulkan'
os.environ['GX_COMMON_BUILD'] = str(common)
os.environ['GX_COMPILE_RECORDS'] = str(out / 'compile-requests')
ndk = pathlib.Path(os.environ['ANDROID_NDK_HOME'])
llvm = ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin'
def sha(p):
    with pathlib.Path(p).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
def capture(args): return subprocess.check_output(list(map(str, args)), text=True).strip()
def run(args, name, phase='configure'):
    env = dict(os.environ, GX_BUILD_PHASE=phase)
    with (out / (name.replace('/', '-') + '.log')).open('w') as log:
        process = subprocess.Popen(list(map(str, args)), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log.write(line); log.flush(); print(line, end='', flush=True)
        if process.wait(): raise RuntimeError(name + ' failed: ' + str(process.returncode))
source = capture(['git', 'rev-parse', 'HEAD'])
assert source == os.environ['GX_SOURCE_HEAD']
assert not capture(['git', 'diff', 'HEAD', '--name-only']), 'Committed, unchanged source checkout required'
sequence = int(capture(['bash', 'scripts/build/android/engine-build-number.sh', root]))
assert capture(['git','rev-parse','--is-shallow-repository']) == 'false'
from state import CONFIG, identity, inspect, normalize
compat, _ = identity(root)
receipt = inspect(root, compat, legacy=os.environ.get('GX_LEGACY_STATE') == '1')
baseline_source = receipt['source']
build_requested = os.environ.get('GX_ENGINE_OPERATION') == 'build'
if build_requested:
    normalize(root, receipt)
epoch = CONFIG['legacy_source_epoch']
changed = set(capture(['git','diff','--name-only',baseline_source,source]).splitlines())
report = {'build_mode': 'INCREMENTAL ENGINE ONLY', 'source_head': source,
          'resolved_engine_sequence': sequence, 'publish': False, 'real_device': 'NOT TESTED',
          'variants': {}, 'dependency_compatibility': 'NOT TESTED', 'new_apk_required': None}
def save(): (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
save()
baseline = json.loads((tools / 'bootstrap-native.json').read_text())
report['baseline'] = baseline
assert sha(tools / 'assets/libadrenotools.so') == baseline['native_libraries']['libadrenotools.so']['sha256']
assert (ndk / 'source.properties').read_text().find('27.2.12479018') >= 0
assert capture(['git', '-C', '/opt/vcpkg', 'rev-parse', 'HEAD']) == '42e4e33e1505c9f47b58c21e0f557c1571b751ee'
run(['git','submodule','update','--init','--depth','1','references/fbraz3-dxvk'], 'dxvk-source-only')
run(['git','-C','references/fbraz3-dxvk','submodule','update','--init','--depth','1'], 'dxvk-headers-only')
# Submodule revision and all nested revisions are pinned to the retained baseline.
assert capture(['git','rev-parse',baseline_source+':references/fbraz3-dxvk']) == capture(['git','-C','references/fbraz3-dxvk','rev-parse','HEAD'])
for relative in capture(['git','-C','references/fbraz3-dxvk','ls-files','--recurse-submodules']).splitlines():
    path=root/'references/fbraz3-dxvk'/relative
    if path.is_file() and not path.is_symlink(): os.utime(path,(epoch,epoch))
# Only byte-unchanged Git inputs can recover their original PCH mtime.
headers = {}
for relative in capture(['git','ls-files']).splitlines():
    path=root/relative
    if relative not in changed and path.is_file() and not path.is_symlink() and path.suffix in ('.h','.hpp','.hxx'):
        headers[str(path.resolve())]=sha(path)
assert not capture(['git','-C','references/fbraz3-dxvk','diff','--name-only'])
for relative in capture(['git','-C','references/fbraz3-dxvk','ls-files','--recurse-submodules']).splitlines():
    path=root/'references/fbraz3-dxvk'/relative
    if path.is_file() and not path.is_symlink() and path.suffix in ('.h','.hpp','.hxx'):
        headers[str(path.resolve())]=sha(path)
# The separately cached SDK has newer, byte-identical headers than the sealed
# objects/PCH. Verify the pinned NDK contents before normalizing its *metadata*.
# Each exact historical timestamp required by Clang is subsequently restored by
# the checksum-checked compiler launcher. Do not disable Ninja's compile guard.
if build_requested:
    from ndk_cache import prepare as prepare_ndk_pch
    report['ndk_cache'] = prepare_ndk_pch(ndk, epoch, headers, out)
    save()
verified_headers=out/'verified-unchanged-headers.json'
verified_headers.write_text(json.dumps(headers))
os.environ['GX_VERIFIED_HEADERS']=str(verified_headers)
for name in ['libdxvk_d3d8.so','libdxvk_d3d9.so']:
    path = common / '_deps/dxvk-build-android/src' / ('d3d8' if 'd3d8' in name else 'd3d9') / name
    assert sha(path) == baseline['native_libraries'][name]['sha256']
    report.setdefault('reused',{})[name] = {'path':str(path),'sha256':sha(path),'rebuilt':False}
if build_requested:
    for name in ['test-engine-incremental-state.py','test-engine-build-number.py','test-engine-packaging.py','test-engine-native-version.py',
                 'test-engine-3277-hotfix.py','test-save-map-safety.py','test-mod-localization.py','smoke/test-mod-localization.py',
                 'test-standalone-mod-overlay.py','test-mod-archive-loading.py',
                 'test-verified-ndk-pch-cache.py',
                 'test-own-update-channel.py','test-android-validation-staging.py',
                 'test-engine-security.py','test-online-tls.py',
                 'test-video-upload-performance.py','test-particle-removal.py']:
        if not (root/'scripts/qa'/name).is_file():
            if name not in ('test-video-upload-performance.py','test-particle-removal.py'):
                raise RuntimeError('Required source check missing: '+name)
            report.setdefault('source_tests',[]).append({'test':name,'status':'NOT TESTED','reason':'not committed in source HEAD'})
            save(); continue
        if name == 'test-online-tls.py' and subprocess.run(['pkg-config','--exists','libcurl','openssl']).returncode != 0:
            report.setdefault('source_tests',[]).append({'test':name,'passed':False,'status':'NOT TESTED','reason':'host libcurl development files absent'})
            save(); print('NOT TESTED in Actions: host TLS fixture needs unavailable libcurl development files', flush=True); continue
        run(['python3','scripts/qa/'+name], name)
        report.setdefault('source_tests',[]).append({'test':name,'passed':True}); save()
    run(['ccache','--set-config=compiler_check=content'], 'ccache-content')
    run(['ccache','--set-config=sloppiness=pch_defines,time_macros'], 'ccache-pch')
    run(['ccache','--zero-stats'], 'ccache-stats-reset-only')
launcher = 'python3;' + str(tools / 'compiler.py')
def configure(directory, high_fps, reuse):
    # GeneralsX @build Codex 08/10/2026 Reuse the pinned LZHL source too.
    # Re-running FetchContent's clone would touch identical table inputs and
    # unnecessarily invalidate the retained compression objects.
    lzhl = directory / '_deps/lzhl-src/CompLibHeader'
    assert lzhl.is_dir(), 'RETAINED LZHL SOURCE REQUIRED'
    assert capture(['git', '-C', lzhl, 'rev-parse', 'HEAD']) == 'dfd96e2ca64adaddb35dd4ebadd6add7d5586783'
    assert not capture(['git', '-C', lzhl, 'diff', 'HEAD', '--name-only']), 'Retained LZHL source changed'
    generated_before = {p:(sha(p),p.stat().st_atime_ns,p.stat().st_mtime_ns) for p in directory.rglob('*') if p.is_file() and p.suffix in ('.h','.hpp','.hxx','.cpp')}
    os.environ['GX_REUSE_RUNTIME'] = '1' if reuse else '0'
    run(['cmake','--preset','android-vulkan','-B',directory,
         '-DSAGE_HIGH_FPS_SIM=' + ('ON' if high_fps else 'OFF'),
         '-DCMAKE_C_COMPILER_LAUNCHER=' + launcher, '-DCMAKE_CXX_COMPILER_LAUNCHER=' + launcher,
         '-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=' + str(tools / 'provider.cmake'),
         '-DFETCHCONTENT_SOURCE_DIR_LZHL=' + str(lzhl),
         '-DVCPKG_INSTALLED_DIR=' + str(common / 'vcpkg_installed'),
         '-DVCPKG_INSTALL_OPTIONS=--only-binarycaching',
         '-DMESON_EXECUTABLE=/usr/bin/false','-DGLSLANG_EXECUTABLE=/usr/bin/false',
         '-DANDROID_CI_BUILD_NUMBER=' + os.environ['GITHUB_RUN_NUMBER']],
        'configure-' + directory.name)
    for p,(digest,atime,mtime) in generated_before.items():
        if p.is_file() and sha(p)==digest: os.utime(p,ns=(atime,mtime))
def build(directory, targets, phase):
    plan = capture(['ninja','-C',directory,'-n',*targets])
    (out / (phase + '-plan.txt')).write_text(plan + '\n')
    explanation = subprocess.run(['ninja','-C',str(directory),'-n','-d','explain',*targets],text=True,capture_output=True)
    (out/(phase+'-explain.txt')).write_text(explanation.stdout+explanation.stderr)
    planned_compiles = sum('Building CXX object' in line or 'Building C object' in line for line in plan.splitlines())
    assert planned_compiles <= CONFIG['max_compile_requests_per_variant'], 'INCREMENTAL REUSE GUARD: excessive compile plan '+str(planned_compiles)
    assert not re.search(r'(Performing (build|configure).*dxvk|meson setup|Building.*ANGLE)',plan,re.I)
    run(['cmake','--build',directory,'--target',*targets,'--parallel','2'], 'build-' + phase, phase)
# All runtime outputs are mandatory: never configure/build a missing dependency.
runtime_outputs = [common/'_deps/sdl3-build/libSDL3.so',common/'_deps/sdl3_image-build/libSDL3_image.so',
                   common/'_deps/openal_soft-build/libopenal.so',common/'libgamespy.so']
assert all(p.is_file() for p in runtime_outputs), 'VERIFIED RUNTIME STATE REQUIRED'
report['restored_runtime_state_reused_without_rebuild'] = True
runtime = {'libSDL3.so':common/'_deps/sdl3-build/libSDL3.so',
           'libSDL3_image.so':common/'_deps/sdl3_image-build/libSDL3_image.so',
           'libopenal.so':common/'_deps/openal_soft-build/libopenal.so',
           'libgamespy.so':common/'libgamespy.so',
           'libadrenotools.so':tools/'assets/libadrenotools.so',
           'libc++_shared.so':ndk/'toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so'}
comparison = []
dependency_dir = out/'runtime-comparison'; dependency_dir.mkdir(exist_ok=True)
for name,path in runtime.items():
    checked = dependency_dir/name
    # Production package-android-zh.sh copies the NDK C++ runtime unchanged.
    # Only project-built dependencies use the explicit strip-unneeded pass.
    if name not in ('libadrenotools.so','libc++_shared.so'):
        run([llvm/'llvm-strip','--strip-unneeded','-o',checked,path], 'strip-comparison-'+name)
    else: shutil.copyfile(path,checked)
    digest = sha(checked); expected = baseline['native_libraries'][name]['sha256']
    comparison.append({'library':name,'sha256':digest,'bootstrap_sha256':expected,'match':digest==expected,'path':str(path)})
for name in ['libEGL_angle.so','libGLESv2_angle.so']:
    path=root/'Core/Libraries/Source/d3d8gles/angle-prebuilt/arm64-v8a'/name
    comparison.append({'library':name,'sha256':sha(path),'bootstrap_sha256':baseline['native_libraries'][name]['sha256'],
                       'match':sha(path)==baseline['native_libraries'][name]['sha256'],'rebuilt':False})
for name in ['libdxvk_d3d8.so','libdxvk_d3d9.so']:
    comparison.append({'library':name,'sha256':report['reused'][name]['sha256'],
      'bootstrap_sha256':baseline['native_libraries'][name]['sha256'],'match':True,'rebuilt':False})
report['dependency_comparison']=comparison
report['dependency_compatibility']='PASS' if all(r['match'] for r in comparison) else 'FAIL'
report['new_apk_required']=not all(r['match'] for r in comparison); save()
if report['new_apk_required']: raise RuntimeError('NEW APK REQUIRED: dependency fingerprint changed; STOP, no engine publish')
if not build_requested:
    report['build']='NOT RUN'; save()
    print('PASS: restored engine state and dependencies; no native build or publication')
    sys.exit(0)
for rate in (30,60):
    directory=root/('build/engine-baseline-'+str(rate))
    configure(directory, rate==60, True)
    commands=json.loads((directory/'compile_commands.json').read_text())
    assert not any('/_deps/' in c['file'] and any(x in c['file'] for x in ('sdl3-','openal_soft-','gamespy-','adrenotools-')) for c in commands)
    build(directory,['z_generals'],'engine-'+str(rate))
    generated=(directory/'resources/gitinfo.cpp').read_text()
    assert re.search(r'int GitRevision = '+str(sequence)+r';',generated)
    assert 'const char GitSHA1[] = "'+source+'";' in generated
    engine_sources=[c for c in commands if any(x in c['file'] for x in ('/GeneralsMD/','/Core/'))]
    for c in engine_sources:
        text=c.get('command',' '.join(c.get('arguments',[])))
        assert '-DGENERALS_ONLINE_HIGH_FPS_LIMIT='+str(rate) in text
        assert ('-DGENERALS_ONLINE_HIGH_FPS_SERVER=1' in text)==(rate==60)
    binary=directory/'GeneralsMD/Code/Main/libmain.so'
    destination=out/('libmain60.so' if rate==60 else 'libmain.so')
    run([llvm/'llvm-strip','--strip-unneeded','-o',destination,binary], 'strip-engine-'+str(rate))
    with destination.open('rb') as f:
        head=f.read(64);assert head[:4]==b'\x7fELF' and struct.unpack_from('<H',head,18)[0]==183
    # Symbol values must come from the actual ELF, not just JSON/generated text.
    symbols=capture([llvm/'llvm-readelf','--dyn-syms','--wide',destination])
    data=destination.read_bytes()
    offsets=[]
    phoff=struct.unpack_from('<Q',data,32)[0];phsize,phnum=struct.unpack_from('<HH',data,54)
    for index in range(phnum):
        p=struct.unpack_from('<IIQQQQQQ',data,phoff+index*phsize)
        if p[0]==1:offsets.append((p[3],p[2],p[5]))
    def value(name):
        match=re.search(r'^\s*\d+:\s*([0-9a-fA-F]+)\s+\d+.*\s'+name+r'$',symbols,re.M);assert match,name
        address=int(match[1],16)
        return next(file+address-virtual for virtual,file,size in offsets if virtual<=address<virtual+size)
    assert struct.unpack_from('<i',data,value('GitRevision'))[0]==sequence
    assert data[value('GitSHA1'):].split(b'\x00',1)[0].decode()==source
    report['variants'][str(rate)]={'path':str(destination),'sha256':sha(destination),'size':destination.stat().st_size,
         'source_sha':source,'engine_sequence':sequence,'simulation_hz':rate,'state_path':str(directory)};save()
assert report['variants']['30']['sha256']!=report['variants']['60']['sha256']
assert capture(['git','rev-parse','HEAD'])==source
report['build']='PASS';save()
print(json.dumps(report['variants'],indent=2))
