from pathlib import Path

IMAGE_EXTENSIONS={".png",".jpg",".jpeg",".webp"}

class DetectorAdapter:
    """Backend-neutral detector interface. Plug a real local detector into extract()."""
    name="manual-json-compatible"
    def extract(self,image_path):
        raise NotImplementedError("Configure a pose detector adapter before processing images.")
    def extract_sequence(self,paths):
        return [self.extract(path) for path in paths]

def discover_frames(folder):
    return sorted(str(p) for p in Path(folder).rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)
