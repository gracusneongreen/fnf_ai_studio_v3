JOINTS=["head","neck","shoulder_l","shoulder_r","elbow_l","elbow_r","hand_l","hand_r","hip","knee_l","knee_r","foot_l","foot_r"]

def validate_frame(frame):
    missing=[j for j in JOINTS if j not in frame.get("joints",{})]
    return {"ok":not missing,"missing":missing}

def normalize_frame(frame,width,height):
    joints={}
    for name,p in frame.get("joints",{}).items():
        joints[name]=[p[0]/max(width,1),p[1]/max(height,1)]
    return {**frame,"coordinate_system":"normalized_0_1","joints":joints}
