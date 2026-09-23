import json
import struct
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from PIL import Image

from fnf_video_engine import parse_chart
from universe_ai_fnf import (
    ALL_SKILLS,
    UNIVERSE_ARCHITECTURE_NAME,
    UniverseAIFNF,
    UniverseAIFNFConfig,
    resolve_skill_order,
)

CHART = Path(__file__).parents[1] / "examples" / "sample_chart.json"


class SkillOrderTests(unittest.TestCase):
    def test_dependencies_are_pulled_in_registry_order(self):
        self.assertEqual(
            resolve_skill_order(["mods"]),
            ("eyes", "audio", "coder", "draw", "mods"),
        )
        self.assertEqual(resolve_skill_order(["computer_use"])[-1], "computer_use")

    def test_unknown_skill_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown skills: telepathy"):
            resolve_skill_order(["telepathy"])


class ConfigTests(unittest.TestCase):
    def test_rejects_empty_and_unknown_skills(self):
        with self.assertRaisesRegex(ValueError, "at least one skill"):
            UniverseAIFNFConfig(skills=()).validate()
        with self.assertRaisesRegex(ValueError, "unknown skills"):
            UniverseAIFNFConfig(skills=("draw", "telepathy")).validate()

    def test_rejects_odd_sprite_size_and_path_like_names(self):
        with self.assertRaisesRegex(ValueError, "sprite size"):
            UniverseAIFNFConfig(skills=("draw",), sprite_size=129).validate()
        with self.assertRaisesRegex(ValueError, "mod name"):
            UniverseAIFNFConfig(skills=("draw",), mod_name="../evil").validate()


class UniverseRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.timeline = parse_chart(CHART, fps=24, tail_ms=0)
        cls._directory = tempfile.TemporaryDirectory()
        root = Path(cls._directory.name)

        reference = root / "reference.png"
        image = Image.new("RGB", (64, 64), (20, 20, 30))
        image.paste(Image.new("RGB", (32, 48), (60, 200, 230)), (16, 8))
        image.paste(Image.new("RGB", (32, 16), (240, 210, 180)), (16, 8))
        image.save(reference)

        audio = root / "song.wav"
        with wave.open(str(audio), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(8000)
            handle.writeframes(
                b"".join(struct.pack("<h", 12000) for _ in range(8000 * 6))
            )

        config = UniverseAIFNFConfig(
            skills=ALL_SKILLS,
            mod_name="TestUniverse",
            character_name="test-bf",
            sprite_size=128,
            reference_image=reference,
            audio_path=audio,
        )
        cls.output = root / "out"
        cls.report = UniverseAIFNF(cls.timeline, config).run(cls.output)
        cls.data = {result.skill: result.data for result in cls.report.results}

    @classmethod
    def tearDownClass(cls):
        cls._directory.cleanup()

    def test_report_covers_every_skill(self):
        self.assertEqual(self.report.architecture, UNIVERSE_ARCHITECTURE_NAME)
        self.assertEqual(self.report.skills, ALL_SKILLS)
        saved = json.loads((self.output / "universe_report.json").read_text())
        self.assertEqual(
            [entry["skill"] for entry in saved["results"]], list(ALL_SKILLS)
        )
        for result in self.report.results:
            for artifact in result.artifacts:
                self.assertTrue(artifact.is_file(), artifact)

    def test_eyes_extracts_reference_palette(self):
        eyes = self.data["eyes"]
        self.assertEqual(len(eyes["palette"]), 5)
        self.assertTrue(all(value.startswith("#") for value in eyes["palette_hex"]))
        self.assertGreater(eyes["subject_coverage"], 0.0)

    def test_audio_maps_tempo_changes_and_loudness(self):
        audio = self.data["audio"]
        self.assertEqual(
            [change["bpm"] for change in audio["bpm_changes"]], [120.0, 150.0]
        )
        self.assertEqual(audio["beat_count"], len(audio["beats"]))
        self.assertTrue(audio["beats"][0]["downbeat"])
        self.assertGreater(audio["beats"][0]["rms"], 0.0)
        windows = audio["hit_windows_ms"]
        self.assertLess(windows["sick"], windows["good"])
        self.assertLess(windows["good"], windows["bad"])

    def test_hands_target_every_note_inside_the_frame(self):
        targets = self.data["hands"]["targets"]
        self.assertEqual(len(targets), len(self.timeline.notes))
        for target in targets:
            for hand in (target["left_hand"], target["right_hand"]):
                self.assertTrue(all(0.0 <= value <= 1.0 for value in hand), hand)
            self.assertIn(target["lead_hand"], ("left", "right"))

    def test_coder_emits_psych_hooks_and_tempo_map(self):
        script = (self.output / "coder" / "universe.lua").read_text()
        self.assertIn("onBeatHit", self.data["coder"]["hooks"])
        self.assertIn("bpm = 150", script)
        self.assertIn("focus = 'player'", script)

    def test_draw_produces_atlas_matching_the_sheet(self):
        draw = self.data["draw"]
        with Image.open(draw["sheet"]) as sheet:
            self.assertEqual(sheet.size, (128 * len(draw["poses"]), 128))
        frames = ElementTree.parse(draw["atlas"]).getroot().findall("SubTexture")
        self.assertEqual(len(frames), len(draw["poses"]))
        self.assertEqual(frames[1].get("x"), "128")
        with Image.open(draw["icons"]) as icons:
            self.assertEqual(icons.size, (300, 150))

    def test_mods_folder_is_installable(self):
        root = Path(self.data["mods"]["root"])
        song_id = self.data["mods"]["song_id"]
        for relative in (
            "pack.json",
            f"data/{song_id}/{song_id}.json",
            "characters/test-bf.json",
            "images/characters/test-bf.png",
            "images/characters/test-bf.xml",
            "images/icons/icon-test-bf.png",
            "scripts/universe.lua",
            "weeks/universe.json",
        ):
            self.assertTrue((root / relative).is_file(), relative)
        self.assertEqual(
            (root.parent / "modsList.txt").read_text(), "TestUniverse|1\n"
        )
        chart = json.loads((root / f"data/{song_id}/{song_id}.json").read_text())
        self.assertEqual(chart["song"]["format"], "psych_v1")
        exported = sum(
            len(section["sectionNotes"]) for section in chart["song"]["notes"]
        )
        self.assertEqual(exported, len(self.timeline.notes))
        character = json.loads((root / "characters/test-bf.json").read_text())
        self.assertEqual(
            [animation["anim"] for animation in character["animations"]],
            list(self.data["draw"]["poses"]),
        )

    def test_computer_use_plan_launches_and_verifies_the_song(self):
        plan = json.loads((self.output / "computer_use" / "actions.json").read_text())
        actions = [step["action"] for step in plan["steps"]]
        self.assertEqual(actions[0], "shell")
        self.assertIn("launch", actions)
        self.assertIn("assert_screen", actions)
        self.assertEqual(plan["song"], self.timeline.song_name)
        script = Path(self.data["computer_use"]["script"])
        self.assertTrue(script.stat().st_mode & 0o111)
        self.assertIn("FNF_GAME_DIR", script.read_text())


if __name__ == "__main__":
    unittest.main()
