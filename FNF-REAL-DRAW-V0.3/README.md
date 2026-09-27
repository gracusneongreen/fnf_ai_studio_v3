# FNF-REAL-DRAW V0.3

A real character-generation workbench for original FNF-inspired rhythm-game assets.

## Vision

Prompt or sketch -> character master -> controlled poses -> animation frames -> sprite sheet -> engine export.

### V0.3 features

- Original character generation from text
- User sketch/reference conditioning
- Character identity anchor
- BF/FNF animation schema reference: idle, singLEFT, singDOWN, singUP, singRIGHT
- Pose planning before image generation
- Corruption phase system
- Transparent PNG output contract
- Sprite-sheet assembly
- Sparrow XML generation
- Psych Engine export contract
- Quality-control metadata
- Pluggable image model backend

## Reference policy

Boyfriend is used only as a structural reference for the animation contract and
rhythm-game pose vocabulary. The generator must create original characters and
must not train on or reproduce copyrighted character artwork without permission.

## Planned UI

1. Character prompt
2. Reference/sketch upload
3. Character master
4. Pose board
5. Generate animation
6. Frame inspector
7. Sprite-sheet editor
8. Psych Engine export
