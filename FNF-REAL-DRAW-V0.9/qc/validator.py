from pose.confidence import sequence_confidence

def validate_sequence(sequence,min_confidence=0.45):
    frames=sequence.get("frames",[])
    missing=[]
    for f in frames:
        if not f.get("joints"): missing.append(f.get("frame"))
    avg=sequence_confidence(sequence)
    return {
        "ok":bool(frames) and not missing and avg>=min_confidence,
        "frame_count":len(frames),
        "average_confidence":avg,
        "missing_joint_frames":missing
    }
