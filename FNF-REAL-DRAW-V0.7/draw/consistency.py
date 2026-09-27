"""Lightweight frame consistency checks; rendering backends can add stronger metrics."""
def compare_character_lock(reference: dict, frame: dict) -> list[str]:
    problems=[]
    for key in ("identity_id","outfit_id","palette_id","rig_id"):
        if reference.get(key) and frame.get(key) != reference[key]:
            problems.append(f"{key} changed")
    return problems

def validate_sequence(frames: list[dict]) -> dict:
    return {"ok": len(frames) > 0, "frame_count": len(frames), "problems": [] if frames else ["empty sequence"]}
