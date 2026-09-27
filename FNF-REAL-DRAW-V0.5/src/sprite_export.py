from pathlib import Path
import xml.etree.ElementTree as ET


def build_sparrow_xml(frame_names: list[str], sheet_width: int, sheet_height: int) -> str:
    root = ET.Element("TextureAtlas", {
        "imagePath": "character.png",
        "width": str(sheet_width),
        "height": str(sheet_height)
    })

    for name in frame_names:
        ET.SubElement(root, "SubTexture", {
            "name": name,
            "x": "0",
            "y": "0",
            "width": str(sheet_width),
            "height": str(sheet_height),
            "frameX": "0",
            "frameY": "0",
            "frameWidth": str(sheet_width),
            "frameHeight": str(sheet_height)
        })

    return ET.tostring(root, encoding="unicode")


def save_xml(frame_names: list[str], output: str, sheet_width: int, sheet_height: int):
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(
        build_sparrow_xml(frame_names, sheet_width, sheet_height),
        encoding="utf-8"
    )
