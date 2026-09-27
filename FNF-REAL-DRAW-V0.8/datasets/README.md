# Dataset layout

datasets/<dataset_id>/
  metadata.json
  sequences/
    <sequence_id>.json
  frames/
    <sequence_id>/
      000001.png
      000002.png

metadata must record source, license, rights holder and whether processing/training is authorized.

Recommended motion coverage:
idle, walk, run, jump, fall, turn, crouch, lean, dance, singing, reaction and transitions.

More data helps only when it is high quality, diverse, correctly labeled and legally usable. Temporal sequences are more valuable for motion than a pile of unrelated images.
