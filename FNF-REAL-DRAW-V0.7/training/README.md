# Motion dataset

Use temporal motion sequences, not only single reference images.

Recommended data:
- multiple frames per action;
- consistent FPS metadata;
- joint coordinates and confidence;
- sequence IDs;
- license/rights metadata;
- optional segmentation/body-part masks.

Do not add copyrighted FNF artwork or scraped datasets unless you have the rights required for the intended use. The pipeline can learn motion structure from authorized human-pose data without copying a particular character's artwork.

Suggested dataset layout:
training/datasets/<dataset_id>/sequences/<sequence_id>/*.json
training/datasets/<dataset_id>/frames/<sequence_id>/*.png
