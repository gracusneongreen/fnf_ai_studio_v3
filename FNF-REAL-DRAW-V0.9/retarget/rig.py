DEFAULT_SCALE=1.0

def retarget_frame(frame,scale=DEFAULT_SCALE,offset=(0,0)):
    joints={k:[p[0]*scale+offset[0],p[1]*scale+offset[1]] for k,p in frame.get("joints",{}).items()}
    return {**frame,"joints":joints,"retargeted":True}

def retarget_sequence(sequence,scale=DEFAULT_SCALE,offset=(0,0)):
    return {**sequence,"frames":[retarget_frame(f,scale,offset) for f in sequence.get("frames",[])]}
