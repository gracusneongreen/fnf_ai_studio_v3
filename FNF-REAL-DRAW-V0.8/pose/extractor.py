"""Backend-neutral pose extraction contract.

A real detector can implement extract(image_path)->frame.
This module deliberately does not force one ML backend.
"""
from pathlib import Path

class PoseExtractor:
    name="manual-json"
    def extract(self,image_path: str)->dict:
        raise NotImplementedError("Install/configure a pose backend adapter.")

def discover_images(folder):
    exts={".png",".jpg",".jpeg",".webp"}
    return sorted(str(p) for p in Path(folder).rglob("*") if p.suffix.lower() in exts)
