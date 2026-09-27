def build_sequence(frames,fps=24,sequence_id="capture"):
    return {
        "version":"0.9",
        "sequence_id":sequence_id,
        "fps":fps,
        "frame_count":len(frames),
        "frames":[{**f,"frame":i,"time":i/fps} for i,f in enumerate(frames)]
    }
