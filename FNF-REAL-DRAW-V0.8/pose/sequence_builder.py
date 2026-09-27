import json
from pathlib import Path
from .schema import validate_frame

def build(frames,fps=24,sequence_id="sequence"):
    checked=[]
    for i,frame in enumerate(frames):
        result=validate_frame(frame)
        if not result["ok"]: raise ValueError(f"Frame {i} missing joints: {result['missing']}")
        checked.append({**frame,"frame":i,"time":i/fps})
    return {"version":"0.8","sequence_id":sequence_id,"fps":fps,"frame_count":len(checked),"frames":checked}

def save(sequence,path):
    Path(path).write_text(json.dumps(sequence,indent=2),encoding="utf-8")
