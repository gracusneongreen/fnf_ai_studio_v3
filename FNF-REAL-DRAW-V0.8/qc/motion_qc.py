from motion.constraints import bone_error

def sequence_report(frames,max_bone_error=0.25):
    reports=[]
    for i in range(1,len(frames)):
        error=bone_error(frames[0],frames[i])
        reports.append({"frame":i,"bone_error":error,"ok":error<=max_bone_error})
    return {"ok":all(x["ok"] for x in reports),"frames":reports}
