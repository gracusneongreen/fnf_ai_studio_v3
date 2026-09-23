import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image

from fnf_video_engine import (
    ARCHITECTURE_NAME,
    BODY_EDGES,
    FNFHUDCompositor,
    FNFOmniVideoV1Config,
    FNFOmniVideoV1Pipeline,
    PoseGuideRenderer,
    milliseconds_to_frame,
    parse_chart,
)


class ChartParserTests(unittest.TestCase):
    def _write_chart(self, payload):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "chart.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_timing_bpm_changes_and_sides(self):
        path = self._write_chart(
            {
                "song": {
                    "song": "Test",
                    "bpm": 120,
                    "notes": [
                        {
                            "lengthInSteps": 16,
                            "mustHitSection": False,
                            "sectionNotes": [[500, 0, 0], [750, 4, 100]],
                        },
                        {
                            "lengthInSteps": 16,
                            "mustHitSection": True,
                            "changeBPM": True,
                            "bpm": 150,
                            "sectionNotes": [[2100, 2, 0], [2300, 7, 0, "Alt"]],
                        },
                    ],
                }
            }
        )
        timeline = parse_chart(path, fps=24, tail_ms=0)

        self.assertEqual(milliseconds_to_frame(500, 24), 12)
        self.assertEqual(
            [note.singer for note in timeline.notes],
            ["opponent", "player", "player", "opponent"],
        )
        self.assertEqual([note.direction for note in timeline.notes], [0, 0, 2, 3])
        self.assertEqual(timeline.notes[-1].note_type, "Alt")
        self.assertEqual(len(timeline.bpm_segments), 2)
        self.assertAlmostEqual(timeline.bpm_segments[1].start_ms, 2000.0)
        self.assertAlmostEqual(timeline.duration_ms, 3600.0)

    def test_unwrapped_song_and_default_bpm(self):
        path = self._write_chart({"song": "Bare", "notes": []})
        timeline = parse_chart(path, fps=60, tail_ms=250)
        self.assertEqual(timeline.song_name, "Bare")
        self.assertEqual(timeline.initial_bpm, 120)
        self.assertEqual(timeline.duration_ms, 250)

    def test_psych_v1_uses_absolute_lane_ownership(self):
        path = self._write_chart(
            {
                "song": "Psych V1",
                "format": "psych_v1",
                "bpm": 120,
                "notes": [
                    {
                        "lengthInSteps": 16,
                        "mustHitSection": False,
                        "sectionNotes": [[500, 0, 0], [750, 4, 0]],
                    },
                    {
                        "lengthInSteps": 16,
                        "mustHitSection": True,
                        "sectionNotes": [[2500, 0, 0], [2750, 4, 0]],
                    },
                ],
            }
        )
        timeline = parse_chart(path, fps=24, tail_ms=0)
        self.assertEqual(
            [note.singer for note in timeline.notes],
            ["player", "opponent", "player", "opponent"],
        )

    def test_first_section_bpm_override_replaces_zero_time_segment(self):
        path = self._write_chart(
            {
                "song": {
                    "bpm": 120,
                    "notes": [
                        {
                            "lengthInSteps": 16,
                            "changeBPM": True,
                            "bpm": 150,
                            "sectionNotes": [],
                        }
                    ],
                }
            }
        )
        timeline = parse_chart(path, fps=24, tail_ms=0)
        self.assertEqual(len(timeline.bpm_segments), 1)
        self.assertEqual(timeline.bpm_at(0).bpm, 150)
        self.assertAlmostEqual(timeline.duration_ms, 1600)


class RenderingTests(unittest.TestCase):
    def setUp(self):
        example = Path(__file__).parents[1] / "examples" / "sample_chart.json"
        self.timeline = parse_chart(example, fps=24, tail_ms=0)

    def test_pose_guide_is_square_rgb_and_nonempty(self):
        guide = PoseGuideRenderer(self.timeline, size=256).render(500)
        self.assertEqual(guide.mode, "RGB")
        self.assertEqual(guide.size, (256, 256))
        self.assertIsNotNone(guide.getbbox())

    def test_pose_topology_uses_canonical_front_facing_sides(self):
        self.assertEqual(BODY_EDGES[:4], ((1, 2), (1, 5), (2, 3), (3, 4)))
        renderer = PoseGuideRenderer(self.timeline, size=256)
        body = renderer._base_body(0.5)
        self.assertLess(body[2][0], body[1][0])
        self.assertGreater(body[5][0], body[1][0])
        self.assertLess(renderer._posed_body("player", 0, 500)[4][0], 0.71)
        self.assertGreater(renderer._posed_body("player", 3, 500)[7][0], 0.71)

    def test_hud_compositor_returns_bgr_frame(self):
        background = Image.new("RGB", (256, 256), (10, 20, 30))
        frame = FNFHUDCompositor(self.timeline, size=256).compose(background, 0)
        self.assertEqual(frame.shape, (256, 256, 3))
        self.assertGreater(int(frame.max()), 30)
        self.assertEqual(FNFHUDCompositor.NOTE_COLORS[1], (255, 194, 75))


class PipelineNamingTests(unittest.TestCase):
    def _config(self, weights_path=None):
        return FNFOmniVideoV1Config(
            base_model="base",
            motion_adapter="motion",
            controlnet_model="controlnet",
            weights_path=weights_path,
            weights_scale=0.8,
            prompt="prompt",
            negative_prompt="negative",
            inference_steps=1,
            guidance_scale=1.0,
            controlnet_scale=1.0,
            seed=1,
        )

    def test_architecture_name_and_explicit_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            weights = Path(directory) / "custom.safetensors"
            weights.write_bytes(b"placeholder")
            config = self._config(weights)
            self.assertEqual(config.architecture, ARCHITECTURE_NAME)
            self.assertEqual(config.resolved_weights_path(), weights.resolve())
            self.assertIsInstance(
                FNFOmniVideoV1Pipeline(config), FNFOmniVideoV1Pipeline
            )

    def test_pipeline_rejects_wrong_architecture(self):
        config = replace(self._config(), architecture="not-the-architecture")
        with self.assertRaisesRegex(ValueError, "expected architecture"):
            FNFOmniVideoV1Pipeline(config)


if __name__ == "__main__":
    unittest.main()
