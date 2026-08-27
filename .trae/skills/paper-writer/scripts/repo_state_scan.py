#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path

def run_git(root,*args):
    p=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,check=False)
    return p.stdout.strip() if p.returncode==0 else ''
def read_text(p):
    try:return p.read_text(encoding='utf-8',errors='replace')
    except OSError:return ''
def collect(root,patterns):
    out=[]
    for pat in patterns: out += [str(p.relative_to(root)) for p in root.glob(pat) if p.is_file()]
    return sorted(set(out))
def tokens(text):
    ks=['NEEDS_REVIEW','FROZEN','VERIFIED','VALIDATED','APPROVED','DRAFT','CURRENT','STALE','PASS','FAIL']
    return [x for x in ks if x in text]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project',required=True); ap.add_argument('--module',required=True); ap.add_argument('--fetch',action='store_true'); ns=ap.parse_args()
    root=Path(ns.project).resolve(); cfg=json.loads(read_text(root/'config'/'project.json')); mod=next((m for m in cfg.get('modules',[]) if m.get('key')==ns.module),None)
    if not mod: raise SystemExit(f'module {ns.module!r} not found')
    if ns.fetch: subprocess.run(['git','fetch','origin','--prune'],cwd=root,check=False)
    branch=mod.get('branch',''); mr=root/mod.get('path',''); task=root/mod.get('task','')
    cb=run_git(root,'branch','--show-current'); head=run_git(root,'rev-parse','HEAD'); remote=run_git(root,'rev-parse',f'origin/{branch}') if branch else ''
    tt=read_text(task); pf=collect(mr,['paper/*.tex','paper/*.md']); pt='\n'.join(read_text(mr/p) for p in pf)
    mf=collect(mr,['results/*model_interface*.json','results/*model_contract*.json','results/*model_spec*.json','results/**/*model_interface*.json'])
    rf=collect(mr,['results/*result_registry*.json','results/registry.csv','results/*run_report*.json','results/*verification*.json','results/**/*run_report*.json','results/**/*verification*.json'])
    mt='\n'.join(read_text(mr/p) for p in mf); rt='\n'.join(read_text(mr/p) for p in rf); w=[]
    if cb and branch and cb!=branch:w.append(f'current branch is {cb}, expected {branch}')
    if head and remote and head!=remote:w.append('HEAD differs from current origin branch tip')
    if 'NEEDS_REVIEW' in tt and any(x in rt for x in ('FROZEN','VERIFIED')):w.append('task says NEEDS_REVIEW while result sources contain VERIFIED/FROZEN; resolve before promotion')
    if 'NEEDS_REVIEW' in tt and 'APPROVED' in mt:w.append('model may be APPROVED while final result remains NEEDS_REVIEW; keep states separate')
    if any(x in pt for x in ('数值求解后应给出','后续应给出','待最终','待确认')) and rf:w.append('paper contains pending language while result files exist; paper may be stale')
    if re.search(r'最终.*结果|最优.*方案|最终.*方案',pt) and 'NEEDS_REVIEW' in tt:w.append('paper appears to state a final answer while task still says NEEDS_REVIEW')
    print(json.dumps({'module':ns.module,'expected_branch':branch,'current_branch':cb,'head':head,'remote_tip':remote,'task':str(task.relative_to(root)) if task.exists() else None,'task_status_tokens':tokens(tt),'model_semantic_files':mf,'model_status_tokens':tokens(mt),'result_status_files':rf,'result_status_tokens':tokens(rt),'paper_files':pf,'warnings':w,'rule':'current user > current task/manifest > model semantic source > result status/formal run > code/data > paper > history'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
