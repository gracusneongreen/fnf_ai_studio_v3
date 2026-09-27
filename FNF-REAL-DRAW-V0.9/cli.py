from __future__ import annotations
import argparse,json
from pathlib import Path
from pose.detector import discover_frames,DetectorAdapter
from pose.sequence import build_sequence
from qc.validator import validate_sequence
from retarget.rig import retarget_sequence

def main():
    p=argparse.ArgumentParser(description="FNF-REAL-DRAW V0.9")
    s=p.add_subparsers(dest="cmd",required=True)
    d=s.add_parser("detect"); d.add_argument("folder"); d.add_argument("output")
    v=s.add_parser("validate"); v.add_argument("sequence")
    r=s.add_parser("retarget"); r.add_argument("sequence"); r.add_argument("output")
    a=p.parse_args()
    if a.cmd=="detect":
        frames=discover_frames(a.folder)
        # Adapter is explicit: no hidden detector or model is assumed.
        result=DetectorAdapter().extract_sequence(frames)
        Path(a.output).write_text(json.dumps(build_sequence(result),indent=2),encoding="utf-8")
        print(f"Saved {len(result)} detected frames to {a.output}")
    elif a.cmd=="validate":
        data=json.loads(Path(a.sequence).read_text(encoding="utf-8"))
        print(json.dumps(validate_sequence(data),indent=2))
    else:
        data=json.loads(Path(a.sequence).read_text(encoding="utf-8"))
        out=retarget_sequence(data)
        Path(a.output).write_text(json.dumps(out,indent=2),encoding="utf-8")
        print(f"Saved retargeted sequence to {a.output}")

if __name__=="__main__": main()
