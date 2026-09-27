from __future__ import annotations
import argparse, json
from pathlib import Path
from chat.provider import load_config, list_models, chat
from motion.constraints import bone_lengths, bone_error
from motion.interpolation import resample

SYSTEM = """You are FNF-REAL-DRAW V0.7, an original 2D rhythm-game production assistant.
Use FNF animation labels only as technical schema. Plan temporal motion sequences, preserve character-lock metadata, and return JSON when requested.
Do not claim copyrighted artwork is available as training data."""

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("models")
    sub.add_parser("chat")
    m=sub.add_parser("motion"); m.add_argument("path")
    args=parser.parse_args()

    if args.cmd=="models":
        cfg=load_config()
        print(f"provider={cfg.provider} base_url={cfg.base_url}")
        for model in list_models(cfg): print(model)
    elif args.cmd=="chat":
        cfg=load_config()
        print(f"provider={cfg.provider} model={cfg.model or '<auto>'}")
        content=chat(cfg,[{"role":"system","content":SYSTEM},{"role":"user","content":"Return JSON with a short plan for a smooth idle-to-sing animation."}])
        print(content)
    else:
        data=json.loads(Path(args.path).read_text(encoding="utf-8"))
        frames=data.get("frames",[])
        print(json.dumps({"frames":len(frames),"bone_lengths_first":bone_lengths(frames[0]) if frames else {}} ,indent=2))
        if len(frames)>=2:
            print(json.dumps({"resampled_8":len(resample(frames,8)),"bone_error_frame_1":bone_error(frames[0],frames[1])},indent=2))

if __name__=="__main__":
    main()
