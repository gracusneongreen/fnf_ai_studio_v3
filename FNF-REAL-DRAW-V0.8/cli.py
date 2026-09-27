import argparse,json
from pathlib import Path
from pose.schema import normalize_frame,validate_frame
from qc.motion_qc import sequence_report

def main():
    p=argparse.ArgumentParser()
    s=p.add_subparsers(dest="cmd",required=True)
    i=s.add_parser("inspect"); i.add_argument("path")
    n=s.add_parser("normalize"); n.add_argument("path"); n.add_argument("output"); n.add_argument("--width",type=int,default=1024); n.add_argument("--height",type=int,default=1024)
    a=p.parse_args()
    data=json.loads(Path(a.path).read_text(encoding="utf-8"))
    if a.cmd=="inspect":
        frames=data.get("frames",[])
        print(json.dumps({"sequence_id":data.get("sequence_id"),"fps":data.get("fps"),"frame_count":len(frames),"qc":sequence_report(frames) if frames else None},indent=2))
    else:
        data["frames"]=[normalize_frame(f,a.width,a.height) for f in data.get("frames",[])]
        Path(a.output).write_text(json.dumps(data,indent=2),encoding="utf-8")
        print(f"Saved normalized sequence: {a.output}")
if __name__=="__main__": main()
