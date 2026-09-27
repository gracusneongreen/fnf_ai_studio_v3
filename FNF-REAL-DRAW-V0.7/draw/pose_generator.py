"""Build render-ready pose jobs from a motion sequence."""
def build_pose_jobs(sequence: dict) -> list[dict]:
    master=sequence.get("character_master", {})
    jobs=[]
    for frame in sequence.get("frames", []):
        jobs.append({
            "frame": frame["frame"],
            "fps": sequence.get("fps", 24),
            "joints": frame["joints"],
            "character_master": master,
            "action": frame.get("action", "idle")
        })
    return jobs
