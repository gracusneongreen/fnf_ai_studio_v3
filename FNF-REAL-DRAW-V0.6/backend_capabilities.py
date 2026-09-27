from dataclasses import dataclass


@dataclass
class BackendCapabilities:
    text_to_image: bool
    image_to_image: bool
    controlnet: bool = False
    ip_adapter: bool = False


def require_animation_backend(caps: BackendCapabilities):
    if not caps.image_to_image:
        raise RuntimeError(
            "FNF-REAL-DRAW V0.6 requires an image-to-image backend for "
            "real source-image animation. Select a compatible authorized model."
        )
