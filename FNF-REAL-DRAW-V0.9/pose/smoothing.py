def smooth(sequence,alpha=0.25):
    frames=sequence.get("frames",[])
    if len(frames)<3:return sequence
    out=[frames[0]]
    for i in range(1,len(frames)-1):
        prev,cur,nxt=frames[i-1],frames[i],frames[i+1]
        joints={}
        for name,p in cur.get("joints",{}).items():
            a=prev.get("joints",{}).get(name,p); n=nxt.get("joints",{}).get(name,p)
            joints[name]=[(1-alpha)*p[0]+alpha*(a[0]+n[0])/2,(1-alpha)*p[1]+alpha*(a[1]+n[1])/2]
        out.append({**cur,"joints":joints})
    out.append(frames[-1])
    return {**sequence,"frames":out,"smoothed":True}
