import argparse
import os
from pathlib import Path

from diffusers import DiffusionPipeline
import torch


def dtype_from_env():
    return torch.float16 if os.getenv("FNF_DTYPE", "float16") == "float16" else torch.float32


def load_pipeline():
    model_id = os.getenv("FNF_IMAGE_MODEL")
    if not model_id:
        raise RuntimeError("Set FNF_IMAGE_MODEL to an authorized Diffusers-compatible model.")

    device = os.getenv("FNF_DEVICE", "cuda")
    pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype_from_env())
    pipe = pipe.to(device)
    return pipe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--negative", default="photorealistic, 3d render, watermark, text, malformed anatomy")
    parser.add_argument("--output", default="output")
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    Path(args.output).mkdir(parents=True, exist_ok=True)
    pipe = load_pipeline()

    generator = torch.Generator(device=os.getenv("FNF_DEVICE", "cuda")).manual_seed(args.seed)
    image = pipe(
        prompt=args.prompt,
        negative_prompt=args.negative,
        num_inference_steps=args.steps,
        generator=generator,
    ).images[0]

    path = Path(args.output) / "character_master.png"
    image.save(path)
    print(path)


if __name__ == "__main__":
    main()
