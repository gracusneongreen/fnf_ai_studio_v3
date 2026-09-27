"""Unified CLI for FNF-REAL-DRAW V0.6."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
from chat_ai import run_chat

def main():
    parser=argparse.ArgumentParser(prog="fnf-real-draw",description="AI chat + image-to-image animation CLI")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("chat",help="open the AI chat")
    a=sub.add_parser("animate",help="generate the five base poses")
    a.add_argument("--input",required=True); a.add_argument("--output",default="output")
    a.add_argument("--strength",type=float,default=0.55); a.add_argument("--steps",type=int,default=28)
    a.add_argument("--seed",type=int,default=1234)
    args=parser.parse_args()
    if args.command=="chat": run_chat(); return
    cmd=[sys.executable,str(Path(__file__).with_name("animate.py")),"--input",args.input,"--output",args.output,
         "--strength",str(args.strength),"--steps",str(args.steps),"--seed",str(args.seed)]
    raise SystemExit(subprocess.call(cmd))
if __name__=="__main__": main()
