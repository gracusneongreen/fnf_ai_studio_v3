"""Deterministic interpolation for joint trajectories."""
def lerp(a, b, t):
    return [a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t]

def resample(frames: list[dict], target_count: int) -> list[dict]:
    if not frames or target_count <= 1:
        return frames[:1] if frames else []
    result=[]
    for i in range(target_count):
        pos=i*(len(frames)-1)/(target_count-1)
        left=int(pos); right=min(left+1,len(frames)-1); t=pos-left
        joints={}
        for name,a in frames[left]["joints"].items():
            b=frames[right]["joints"].get(name,a)
            joints[name]=lerp(a,b,t)
        result.append({"frame":i,"time":i/(target_count-1),"joints":joints})
    return result
