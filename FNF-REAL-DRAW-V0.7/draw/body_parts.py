"""Character body-part contract used by the motion-to-render stage."""
BODY_PARTS = [
    "head", "hair", "torso", "left_arm", "right_arm", "left_hand",
    "right_hand", "left_leg", "right_leg", "left_foot", "right_foot"
]

def validate(parts: dict) -> list[str]:
    return [name for name in BODY_PARTS if name not in parts]
