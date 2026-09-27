from __future__ import annotations
import os
from pathlib import Path

IMAGE_EXTENSIONS={".png",".jpg",".jpeg",".webp"}
COCO={"nose":0,"left_shoulder":5,"right_shoulder":6,"left_elbow":7,"right_elbow":8,"left_wrist":9,"right_wrist":10,"left_hip":11,"right_hip":12,"left_knee":13,"right_knee":14,"left_ankle":15,"right_ankle":16}

def _mid(a,b):
    return [(a[0]+b[0])/2.0,(a[1]+b[1])/2.0]

class DetectorAdapter:
    """Real local Ultralytics YOLO pose detector mapped to the 13-joint project rig."""
    name="ultralytics-yolo-pose"
    def __init__(self,model_name=None,device=None,conf=0.25):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Ultralytics is not installed. Run: pip install -r requirements.txt") from exc
        self.model_name=model_name or os.getenv("FNF_POSE_MODEL","yolo26n-pose.pt")
        self.device=device or os.getenv("FNF_POSE_DEVICE","")
        self.conf=float(os.getenv("FNF_POSE_CONF",conf))
        self.model=YOLO(self.model_name)
    def extract(self,image_path):
        results=self.model.predict(source=str(image_path),conf=self.conf,device=self.device or None,verbose=False,save=False)
        if not results or results[0].keypoints is None or len(results[0].keypoints.xy)==0:
            return {"source":str(image_path),"detector":self.name,"confidence":0.0,"joints":{}}
        result=results[0]
        person_index=0
        if result.boxes is not None and len(result.boxes)>1:
            boxes=result.boxes.xyxy.cpu().numpy()
            areas=(boxes[:,2]-boxes[:,0])*(boxes[:,3]-boxes[:,1])
            person_index=int(areas.argmax())
        points=result.keypoints.data[person_index].cpu().numpy()
        def p(name):
            x,y,c=points[COCO[name]]
            return [float(x),float(y)],float(c)
        joints={}
        confs=[]
        for name in ("left_shoulder","right_shoulder","left_elbow","right_elbow","left_wrist","right_wrist","left_knee","right_knee","left_ankle","right_ankle"):
            xy,c=p(name); joints[name]=xy; confs.append(c)
        ls,lc=p("left_shoulder"); rs,rc=p("right_shoulder")
        lh,lhc=p("left_hip"); rh,rhc=p("right_hip"); nose,nc=p("nose")
        joints["neck"]=_mid(ls,rs); joints["head"]=nose; joints["hip"]=_mid(lh,rh)
        confs.extend([lc,rc,lhc,rhc,nc])
        return {"source":str(image_path),"detector":self.name,"confidence":sum(confs)/len(confs),"joints":joints}
    def extract_sequence(self,paths):
        return [self.extract(path) for path in paths]

def discover_frames(folder):
    return sorted(str(p) for p in Path(folder).rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)
