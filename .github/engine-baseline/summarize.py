import collections,json,pathlib,re,subprocess
out=pathlib.Path('baseline-report');out.mkdir(exist_ok=True)
requests=[]
for p in sorted((out/'compile-requests').rglob('*.json')):
    row=json.loads(p.read_text());log=p.with_suffix('.log').read_text() if p.with_suffix('.log').exists() else ''
    row['results']=re.findall(r'Result: (\S+)',log)
    row['hit']=any(x.endswith('cache_hit') for x in row['results'])
    row['miss']='cache_miss' in row['results']
    row['actually_compiled']=not row['hit'] and row['exit']==0
    requests.append(row)
summary={'total_compile_requests':len(requests),'cache_hits':sum(r['hit'] for r in requests),
    'cache_misses':sum(r['miss'] for r in requests),
    'actual_successful_compiler_invocations':sum(r['actually_compiled'] for r in requests),
    'failed_requests':sum(r['exit']!=0 for r in requests),'requests':requests}
(out/'compiler-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='requests'},indent=2))
states={}
for mode,name in [('common','android-vulkan'),('30','engine-baseline-30'),('60','engine-baseline-60')]:
    d=pathlib.Path('build')/name
    states[mode]={'directory':str(d),'CMakeCache':(d/'CMakeCache.txt').exists(),'ninja':(d/'build.ninja').exists(),
      'ninja_deps':(d/'.ninja_deps').exists(),'ninja_log':(d/'.ninja_log').exists(),
      'object_count':sum(1 for p in d.rglob('*.o')),'archive_count':sum(1 for p in d.rglob('*.a')),
      'generated_git':(d/'resources/gitinfo.cpp').exists(),'engine_output':(d/'GeneralsMD/Code/Main/libmain.so').exists()}
(out/'incremental-state.json').write_text(json.dumps(states,indent=2)+'\n')
