"""Pose refinement contracts for temporal smoothing and constraints."""
def refine(frames: list[dict], smoothing=0.25) -> list[dict]:
    if len(frames) < 3:
        return frames
    # Keep this deterministic and backend-agnostic; ML refiners can plug in later.
    output=[frames[0]]
    for prev, cur, nxt in zip(frames, frames[1:-1], frames[2:]):
        f={**cur, "joints": {}}
        for joint, p in prev["joints"].items():
            c=cur["joints"].get(joint,p); n=nxt["joints"].get(joint,c)
            f["joints"][joint]=[
                (1-smoothing)*c[0] + smoothing*(p[0]+n[0])/2,
                (1-smoothing)*c[1] + smoothing*(p[1]+n[1])/2
            ]
        output.append(f)
    output.append(frames[-1])
    return output
