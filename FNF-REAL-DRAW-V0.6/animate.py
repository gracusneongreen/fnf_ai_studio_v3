import argparse
import os
from pathlib import Path

from PIL import Image
from diffusers import AutoPipelineForImage2Image
import torch

POSES = ["idle", "singLEFT", "singDOWN", "singUP", "singRIGHT"]


def load_pipe():
    model_id = os.getenv("FNF_IMAGE_MODEL")
    if not model_id:
        raise RuntimeError("Set FNF_IMAGE_MODEL to an authorized image-to-image model.")

    device = os.getenv("FNF_DEVICE", "cuda")
    dtype = torch.float16 if os.getenv("FNF_DTYPE", "float16") == "float16" else torch.float32

    pipe = AutoPipelineForImage2Image.from_pretrained(model_id, torch_dtype=dtype)
    return pipe.to(device)


def pose_prompt(pose: str) -> str:
    return (
        "original 2D rhythm-game character, same identity as source image, "
        "same clothing, hair, palette and proportions, clean readable game sprite, "
        f"animation pose {pose}, transparent-looking simple background"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="output")
    parser.add_argument("--strength", type=float, default=0.55)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    source = Path(args.input)
    if not source.exists():
        raise FileNotFoundError(source)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    pipe = load_pipe()
    image = Image.open(source).convert("RGB")
    device = os.getenv("FNF_DEVICE", "cuda")
    generator = torch.Generator(device=device).manual_seed(args.seed)

    for index, pose in enumerate(POSES):
        result = pipe(
            prompt=pose_prompt(pose),
            image=image,
            strength=args.strength,
            num_inference_steps=args.steps,
            generator=generator,
        ).images[0]

        result.save(out / f"{pose}_{index:02d}.png")
        print(out / f"{pose}_{index:02d}.png")


if __name__ == "__main__":
    main()
