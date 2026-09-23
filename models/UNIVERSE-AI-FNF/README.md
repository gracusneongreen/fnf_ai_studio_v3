# Universe-ai-fnf

`UNIVERSE-AI-FNF` is a skill router, not a checkpoint: every skill is
deterministic Python driven by the parsed chart, so no weight binaries are
required and runs are reproducible.

| Skill | Requires | Produces |
| --- | --- | --- |
| `eyes` | – | palette, brightness, contrast, subject coverage |
| `audio` | – | beat grid, tempo map, hit windows, per-beat RMS |
| `hands` | `audio` | per-note wrist targets and a hand-trail preview |
| `coder` | – | Psych Engine Lua with tempo and camera cues |
| `draw` | `eyes` | FNF sprite sheet, Sparrow atlas, 150x150 health icons |
| `mods` | `audio`, `coder`, `draw` | installable Psych mod folder |
| `computer_use` | `mods` | GUI action plan and playtest launch script |

Requesting a skill also runs its prerequisites, and skills always execute in
registry order.

Optional diffusion weights can be layered on top later by pointing the `draw`
skill's palette at `FNF-OMNI-VIDEO-V1` renders; the router itself stays
weight-free and is safe to run on CPU.
