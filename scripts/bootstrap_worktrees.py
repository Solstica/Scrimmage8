#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/"config/project.json").read_text(encoding="utf-8"))

def run(*args,check=True):
    return subprocess.run(args,cwd=ROOT,text=True,check=check)

def exists_ref(ref):
    return subprocess.run(["git","show-ref","--verify","--quiet",ref],cwd=ROOT).returncode==0

def worktree_map():
    p=subprocess.run(["git","worktree","list","--porcelain"],cwd=ROOT,text=True,capture_output=True,check=True)
    by_branch={}; by_path={}; item={}
    for line in p.stdout.splitlines()+[""]:
        if not line:
            if item.get("path"):
                by_path[str(Path(item["path"]).resolve()).lower()]=dict(item)
                if item.get("branch"):
                    by_branch[item["branch"]]=dict(item)
            item={}; continue
        key,_,value=line.partition(" ")
        if key=="worktree": item["path"]=value
        elif key=="branch": item["branch"]=value.removeprefix("refs/heads/")
        elif key=="detached": item["detached"]=True
    return by_branch,by_path

def write_manifest(root, rows):
    path=root/"worktrees.json"
    path.write_text(json.dumps({"repository":str(ROOT),"worktrees":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"[MANIFEST] {path}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(ROOT.parent/(ROOT.name+"-worktrees")))
    ap.add_argument("--push",action="store_true",help="创建后 push 到 origin")
    ap.add_argument("--no-fetch",action="store_true",help="不更新远端引用")
    a=ap.parse_args(); wtroot=Path(a.root).resolve(); wtroot.mkdir(parents=True,exist_ok=True)
    if subprocess.run(["git","diff","--quiet"],cwd=ROOT).returncode or subprocess.run(["git","diff","--cached","--quiet"],cwd=ROOT).returncode:
        raise SystemExit("当前仓库有未提交修改，请先处理。")
    if not a.no_fetch: run("git","fetch","origin","--prune",check=False)
    base=CFG.get("default_base","main")
    rows=[]
    for m in sorted((x for x in CFG["modules"] if x.get("active",True)), key=lambda x:x["merge_order"]):
        branch=m["branch"]; dest=wtroot/m["key"]
        by_branch,by_path=worktree_map()
        if dest.exists():
            registered=by_path.get(str(dest).lower())
            if not registered:
                raise SystemExit(f"目标目录已存在但不是Git worktree：{dest}")
            if registered.get("branch")!=branch:
                raise SystemExit(f"目标worktree分支不符：{dest} 当前为 {registered.get('branch')}，期望 {branch}")
            print(f"[OK] {m['key']}: {dest}（已存在）")
            rows.append({"key":m["key"],"branch":branch,"path":str(dest),"under_root":True})
            continue
        occupied=by_branch.get(branch)
        if occupied:
            path=str(Path(occupied["path"]).resolve())
            print(f"[USE] {m['key']}: {branch} 已在 {path}，不重复检出")
            rows.append({"key":m["key"],"branch":branch,"path":path,"under_root":False})
            continue
        local=f"refs/heads/{branch}"; remote=f"refs/remotes/origin/{branch}"
        if exists_ref(local):
            run("git","worktree","add",str(dest),branch)
        elif exists_ref(remote):
            run("git","worktree","add","-b",branch,str(dest),f"origin/{branch}")
        else:
            run("git","worktree","add","-b",branch,str(dest),base)
            if a.push: run("git","push","-u","origin",branch)
        print(f"[OK] {m['key']}: {dest}")
        rows.append({"key":m["key"],"branch":branch,"path":str(dest),"under_root":True})
    write_manifest(wtroot,rows)
    print("\n完成。已存在于其他路径的分支会复用而不会导致初始化中断；进入清单路径后运行 workflow.py start <key>。")

if __name__=="__main__": main()
