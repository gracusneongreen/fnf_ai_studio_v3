import tempfile
import unittest
from pathlib import Path

from cloud_ai_connector import CloudAIConfig, FreeAIConnector
from osworld_bridge import HumanMotionConfig, OSWorldBridge
from pose_generator import FNFOpenPoseGenerator
from studio import FNFOMNIStudioV2, StudioConfig
from fnf_video_engine import parse_chart
from PIL import Image


class StudioV2Tests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]
        self.chart = self.root / "examples" / "sample_chart.json"

    def test_status_exposes_studio_and_reference_contract(self):
        status = FNFOMNIStudioV2(
            StudioConfig(references_dir=self.root / "assets" / "references")
        ).status()
        self.assertEqual(status["studio"], "FNF-OMNI-STUDIO-V2")
        self.assertIn("bf_reference.png", status["reference_files"])
        self.assertIn("background_stage.png", status["reference_files"])

    def test_pose_generator_reports_beat_and_direction(self):
        timeline = parse_chart(self.chart, fps=24, tail_ms=0)
        generator = FNFOpenPoseGenerator(timeline, size=128)
        pose = generator.pose_at(500)
        self.assertTrue(pose.is_beat)
        self.assertEqual(generator.direction_name(0), "left")

    def test_pose_generator_resets_phase_at_bpm_change(self):
        timeline = parse_chart(self.chart, fps=24, tail_ms=0)
        generator = FNFOpenPoseGenerator(timeline, size=128)
        segment = timeline.bpm_segments[1]
        self.assertTrue(generator.pose_at(segment.start_ms).is_beat)

    def test_cloud_free_status_is_explicit(self):
        connector = FreeAIConnector(CloudAIConfig(cloud_free=True))
        self.assertTrue(connector.status()["cloud_free"])

    def test_ollama_must_be_local(self):
        with self.assertRaisesRegex(ValueError, "local machine"):
            FreeAIConnector(CloudAIConfig(ollama_url="http://169.254.169.254"))

    def test_sneak_peek_writes_requested_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preview.png"
            studio = FNFOMNIStudioV2(StudioConfig(size=128))
            studio.render_sneak_peek(self.chart, output, max_frames=2)
            self.assertTrue(output.is_file())

    def test_cursor_path_is_curved_and_ends_at_target(self):
        bridge = OSWorldBridge(
            motion=HumanMotionConfig(path_steps=8, jitter_px=2, overshoot_px=4)
        )
        path = bridge.cursor_path((0, 0), (100, 100))
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (100, 100))
        self.assertGreater(len(path), 8)
        self.assertTrue(any(point[0] != point[1] for point in path[1:-1]))

    def test_cursor_overlay_changes_image_pixels(self):
        image = Image.new("RGB", (64, 64), "black")
        OSWorldBridge._draw_cursor(image, (20, 20))
        self.assertIsNotNone(image.getbbox())

    def test_type_log_does_not_retain_plaintext(self):
        class FakePyAutoGUI:
            def write(self, _character, interval):
                return None

        bridge = OSWorldBridge(
            motion=HumanMotionConfig(typing_min_interval=0, typing_max_interval=0)
        )
        bridge._pyautogui = lambda: FakePyAutoGUI()
        bridge.type_text("secret-token")
        self.assertNotIn("secret-token", str(bridge.actions))


if __name__ == "__main__":
    unittest.main()
