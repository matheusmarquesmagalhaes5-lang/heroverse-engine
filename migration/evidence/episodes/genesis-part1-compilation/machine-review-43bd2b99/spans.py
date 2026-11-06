import json,sys
W=sys.argv[1]
tl=json.load(open(W+'/migration/production/pilot-023/out/timeline.json'))['segments']
st={r['name']:r for r in tl}
plan=json.load(open(W+'/migration/production/bible/compilations/genesis-part1-compilation.json'))
spans=[]
def rep(name,f):
    c=json.load(open(W+f))['composed']; r=st[name]
    for x in c.get('timeline') or []:
        sid=str(x.get('shot') or x.get('id'))
        if (sid.startswith('k-') or sid.startswith('b-')) and x['start'] < r['seconds']-0.5:
            a=r['start']+x['start']; b=min(r['start']+x['end'], r['start']+r['seconds']-0.3)
            spans.append({'src':name,'shot':sid,'start':round(a,2),'end':round(b,2)})
rep('flood-ends-long','/migration/evidence/episodes/flood-ends-long/report-41484825424.json')
rep('genesis-10-11-long','/migration/evidence/episodes/genesis-10-11-long/report-41850571431.json')
import glob
for s in ('genesis-07-short','genesis-08-short','genesis-09-short'):
    f=glob.glob(W+f'/migration/evidence/episodes/{s}/report-*.json')[0].replace(W,'')
    rep(s,f)
keeper_stills={'arc-01-long-k-promise-2','arc-01-long-k-promise-3','flood-ends-long-k-bow','flood-ends-long-k-insight'}
secs=[('hook',plan['hook'])]+[(f'i{n}',it) for n,it in enumerate(plan['interludes'],1)]+[('close',plan['close'])]
for key,k in secs:
    r=st[key]; ls=r['line_starts']; ids=sorted(ls)
    bounds=[ls[i]-0.5 for i in ids]+[r['seconds']]
    for j,(i,b) in enumerate(zip(ids,k['beats'])):
        if b['still']['approved_still'] in keeper_stills:
            spans.append({'src':key,'shot':i+':'+b['still']['approved_still'],'start':round(r['start']+bounds[j]+0.3,2),'end':round(r['start']+bounds[j+1]-0.3,2),'portrait':True})
json.dump(spans,open(sys.argv[2],'w'),indent=0); print(len(spans)); [print(s) for s in spans]
