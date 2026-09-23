import tempfile
import unittest
from pathlib import Path

from PIL import Image

from fnf_omni_preview import (
    PREVIEW_ARCHITECTURE_NAME,
    FNFOmniPreviewConfig,
    FNFOmniPreviewEngine,
)
from fnf_video_engine import FNFHUDCompositor, PoseGuideRenderer, parse_chart


class PreviewEngineTests(unittest.TestCase):
    def setUp(self):
        chart = Path(__file__).parents[1] / "examples" / "sample_chart.json"
        self.timeline = parse_chart(chart, fps=24, tail_ms=0)

    def _engine(self, max_frames=6, camera="wide"):
        size = 128
        return FNFOmniPreviewEngine(
            self.timeline,
            PoseGuideRenderer(self.timeline, size),
            FNFHUDCompositor(self.timeline, size),
            FNFOmniPreviewConfig(
                size=size,
                max_frames=max_frames,
                columns=2,
                beat_stride=4,
                gif_fps=2,
                camera_angle=camera,
                background_style="test neon stage",
            ),
        )

    def test_keyframes_prioritize_sections_and_bpm_boundaries(self):
        engine = self._engine(max_frames=8)
        keyframes = engine.select_keyframes()
        times = [round(keyframe.time_ms) for keyframe in keyframes]
        reasons = {reason for frame in keyframes for reason in frame.reasons}

        self.assertEqual(engine.config.architecture, PREVIEW_ARCHITECTURE_NAME)
        self.assertLessEqual(len(keyframes), 8)
        self.assertIn(0, times)
        self.assertIn(2000, times)
        self.assertIn(4000, times)
        self.assertIn("BPM 150", reasons)
        self.assertIn("turn switch: player", reasons)

    def test_camera_crops_preserve_square_aspect_ratio(self):
        for crop in FNFOmniPreviewEngine.CAMERA_CROPS.values():
            left, top, right, bottom = crop
            self.assertAlmostEqual(right - left, bottom - top)

    def test_frame_cap_keeps_bpm_and_turn_switches(self):
        keyframes = self._engine(max_frames=3).select_keyframes()
        self.assertEqual(
            [round(keyframe.time_ms) for keyframe in keyframes],
            [0, 2000, 4000],
        )

    def test_small_card_wraps_reason_and_camera_labels(self):
        engine = self._engine(max_frames=4, camera="medium")
        keyframe = engine.select_keyframes()[0]
        card = engine.render_keyframe(keyframe)
        self.assertEqual(card.width, 128)
        self.assertGreater(card.height, 128 + 48)

    def test_exports_png_contact_sheet(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "storyboard.png"
            keyframes = self._engine(max_frames=4).export(output)
            with Image.open(output) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 128)
                self.assertGreater(image.height, 128)
            self.assertEqual(len(keyframes), 4)

    def test_exports_animated_gif(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "storyboard.gif"
            keyframes = self._engine(max_frames=4, camera="close").export(output)
            with Image.open(output) as image:
                self.assertEqual(image.format, "GIF")
                self.assertEqual(image.n_frames, len(keyframes))
                self.assertGreater(image.info["duration"], 0)

    def test_rejects_unsupported_output_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "storyboard.mp4"
            with self.assertRaisesRegex(ValueError, ".png or .gif"):
                self._engine().export(output)


if __name__ == "__main__":
    unittest.main()
