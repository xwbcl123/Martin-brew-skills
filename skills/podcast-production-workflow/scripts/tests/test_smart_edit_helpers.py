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


class SmartEditHelperTests(unittest.TestCase):
    def test_milliseconds_to_48k_samples_is_exact(self):
        module = load("generate_edit_candidates")
        self.assertEqual(module.milliseconds_to_sample(1250), 60000)

    def test_candidate_dedup_merges_detector_evidence(self):
        module = load("generate_edit_candidates")
        base = {
            "candidate_id": "pending",
            "category": "filler",
            "core_interval": {"start_sample": 10, "end_sample": 20},
            "detector_evidence": [{"lane": "standard"}],
        }
        duplicate = {**base, "detector_evidence": [{"lane": "prompted"}]}
        result = module.merge_duplicates([base, duplicate])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["candidate_id"], "C0001")
        self.assertEqual(len(result[0]["detector_evidence"]), 2)

    def test_alignment_lis_rejects_backward_source_mapping(self):
        module = load("align_filmora_reference")
        pairs = [(0, 10, 10), (1, 11, 10), (2, 9, 7), (3, 13, 10), (4, 15, 11)]
        result = module.longest_nondecreasing_delta(pairs)
        self.assertEqual(result, [(0, 10, 10), (1, 11, 10), (3, 13, 10), (4, 15, 11)])

    def test_repeated_segment_start_emits_candidate_not_cut(self):
        module = load("generate_edit_candidates")
        def seg(start, end, words):
            return {"text": "".join(words), "offsets": {"from": start, "to": end}, "tokens": [
                {"text": word, "offsets": {"from": start + i * 100, "to": start + (i + 1) * 100}, "p": 0.9}
                for i, word in enumerate(words)
            ]}
        segments = [seg(0, 1000, ["我们", "今天", "讨论", "A"]), seg(1200, 2600, ["我们", "今天", "讨论", "B"])]
        policy = {"protected_discourse_markers": [], "rough_cut_detectors": {"enabled": True, "repeated_start_token_count": 3, "restart_trigger_phrases": []}}
        common = {"episode_id": "e", "source_sha": "a", "analysis_sha": "b", "policy_sha": "c"}
        items = []
        module.add_restart_candidates(items, segments, "test", common, policy)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["category"], "repetition")
        self.assertEqual(items[0]["core_interval"], {"start_sample": 0, "end_sample": 48000})


if __name__ == "__main__":
    unittest.main()
