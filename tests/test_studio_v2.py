import tempfile
import unittest
from pathlib import Path

from cloud_ai_connector import CloudAIConfig, FreeAIConnector
from pose_generator import FNFOpenPoseGenerator
from studio import FNFOMNIStudioV2, StudioConfig
from fnf_video_engine import parse_chart


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


if __name__ == "__main__":
    unittest.main()
