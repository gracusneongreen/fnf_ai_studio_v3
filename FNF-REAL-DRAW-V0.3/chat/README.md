# FNF-REAL-DRAW AI Chat

The chat is the control panel for the generator.

Example:

User:
> Zrób mi nową postać: czarna bluza, czerwone spodnie, 5 faz corruption.

The assistant should turn that into a structured generation job, then the
image backend produces the actual frames.

The V0.3 architecture separates:
- chat reasoning/orchestration
- image generation model
- consistency/QC
- sprite-sheet/XML export
