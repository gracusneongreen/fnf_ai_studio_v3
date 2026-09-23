# FNF-OMNI-VIDEO-V1 weights

Place the custom Diffusers-compatible LoRA at:

```text
models/FNF-OMNI-VIDEO-V1/fnf-omni-video-v1.safetensors
```

Weight binaries are intentionally ignored by Git. After publishing the weights,
either fill in `source` and `weights.sha256` in `model_manifest.json`, or install
them explicitly:

```bash
python models/download_weights.py \
  --repo-id OWNER/FNF-OMNI-VIDEO-V1 \
  --filename fnf-omni-video-v1.safetensors \
  --revision COMMIT_OR_TAG \
  --sha256 EXPECTED_SHA256
```

An HTTPS download is also supported:

```bash
python models/download_weights.py \
  --url https://example.com/fnf-omni-video-v1.safetensors \
  --sha256 EXPECTED_SHA256
```

The main pipeline discovers the conventional file automatically. `--weights`
can override it with another local `.safetensors` file.
