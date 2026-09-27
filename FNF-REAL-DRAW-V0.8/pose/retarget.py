"""Map normalized source joints into a character rig coordinate space."""

def retarget(frame, source_size=(1.0,1.0), target_size=(1.0,1.0), origin=(0.0,0.0)):
    sx=target_size[0]/max(source_size[0],1e-9)
    sy=target_size[1]/max(source_size[1],1e-9)
    joints={k:[origin[0]+p[0]*sx,origin[1]+p[1]*sy] for k,p in frame["joints"].items()}
    return {**frame,"joints":joints,"retargeted":True}
