"""Character-lock metadata. Keeps generated frames tied to one original character master."""
from dataclasses import dataclass, asdict

@dataclass
class CharacterMaster:
    identity_id: str
    rig_id: str
    outfit_id: str
    palette_id: str
    reference_asset: str | None = None

    def to_dict(self):
        return asdict(self)
