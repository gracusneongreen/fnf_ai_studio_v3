def filter_low_confidence(frame,threshold=0.5):
    confidence=frame.get("confidence",{})
    joints={k:v for k,v in frame.get("joints",{}).items() if confidence.get(k,1.0)>=threshold}
    return {**frame,"joints":joints,"filtered":True}

def sequence_confidence(sequence):
    values=[]
    for frame in sequence.get("frames",[]):
        values.extend(frame.get("confidence",{}).values())
    return sum(values)/len(values) if values else 0.0
