"""Motion constraints used to reject implausible generated poses."""
import math

def distance(a,b):
    return math.hypot(a[0]-b[0],a[1]-b[1])

def bone_lengths(frame: dict) -> dict:
    j=frame["joints"]; pairs={
        "upper_arm_l":("shoulder_l","elbow_l"), "forearm_l":("elbow_l","hand_l"),
        "upper_arm_r":("shoulder_r","elbow_r"), "forearm_r":("elbow_r","hand_r"),
        "thigh_l":("hip","knee_l"), "shin_l":("knee_l","foot_l"),
        "thigh_r":("hip","knee_r"), "shin_r":("knee_r","foot_r")}
    return {k:distance(j[a],j[b]) for k,(a,b) in pairs if a in j and b in j}

def bone_error(reference: dict, frame: dict) -> float:
    ref=bone_lengths(reference); cur=bone_lengths(frame)
    if not ref: return 0.0
    errors=[abs(cur[k]-v)/max(v,1e-6) for k,v in ref.items() if k in cur]
    return sum(errors)/len(errors) if errors else 0.0
