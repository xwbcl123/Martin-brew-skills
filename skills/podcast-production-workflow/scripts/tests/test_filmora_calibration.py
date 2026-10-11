import importlib.util
import pathlib
import unittest


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class FilmoraCalibrationTests(unittest.TestCase):
    def test_reference_edl_keeps_uncertainty_and_never_authorizes_production(self):
        module = load("reconstruct_reference_edl")
        alignment = {
            "alignment_valid": True,
            "run_key": "a" * 64,
            "provenance": {"source_render": {"sha256": "b" * 64}, "filmora_reference": {"sha256": "c" * 64}},
            "reference_transitions": [
                {"reference_transition_id": "R1", "source_start_sample_48k": 48000, "source_end_sample_48k": 96000, "boundary_uncertainty_seconds": 0.2},
                {"reference_transition_id": "R2", "source_start_sample_48k": 192000, "source_end_sample_48k": 240000, "boundary_uncertainty_seconds": 1.2},
            ],
        }
        result = module.reconstruct(alignment, "d" * 64, "episode", 0.4, 0.8)
        self.assertTrue(result["cuts"][0]["evaluation_eligible"])
        self.assertFalse(result["cuts"][1]["evaluation_eligible"])
        self.assertFalse(result["cuts"][0]["production_edl_eligible"])
        self.assertFalse(result["publish_authorized"])

    def test_delta_analysis_reports_match_and_disagreements(self):
        module = load("compare_edls")
        auto = {"episode_id": "episode", "cuts": [
            {"cut_id": "A1", "applied_interval": {"start_sample": 48000, "end_sample": 96000}, "categories": ["filler"]},
            {"cut_id": "A2", "applied_interval": {"start_sample": 300000, "end_sample": 320000}, "categories": ["silence"]},
        ]}
        reference = {"episode_id": "episode", "provenance": {"alignment": {"sha256": "e" * 64}}, "cuts": [
            {"reference_cut_id": "R1", "interval": {"start_sample": 47000, "end_sample": 97000}, "boundary_uncertainty_seconds": 0.1, "evaluation_eligible": True, "duration_seconds": 50000 / 48000},
            {"reference_cut_id": "R2", "interval": {"start_sample": 200000, "end_sample": 220000}, "boundary_uncertainty_seconds": 0.1, "evaluation_eligible": True, "duration_seconds": 20000 / 48000},
        ]}
        report, feedback = module.compare(auto, reference, "a" * 64, "b" * 64)
        self.assertEqual(report["metrics"]["matched_count"], 1)
        self.assertEqual(report["metrics"]["auto_only_count"], 1)
        self.assertEqual(report["metrics"]["reference_only_count"], 1)
        self.assertEqual(len(feedback["labels"]), 2)
        self.assertFalse(report["publish_authorized"])

    def test_review_sampling_is_kind_stratified_and_bounded(self):
        module = load("render_calibration_review")
        items = []
        for kind in ("auto_only", "reference_only", "boundary_drift"):
            for index in range(20):
                items.append({"delta_id": f"{kind}-{index}", "kind": kind, "source_interval": {"start_sample": index * 48000, "end_sample": index * 48000 + 100}})
        sampled = module.timeline_sample(items, 12)
        self.assertEqual(len(sampled), 12)
        self.assertEqual({item["kind"] for item in sampled}, {"auto_only", "reference_only", "boundary_drift"})


if __name__ == "__main__":
    unittest.main()
