#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "plan_incremental_invalidation.py"
LOCK_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "build_artifact_lock.py"
DAG = pathlib.Path(__file__).resolve().parents[2] / "references" / "artifact-dependency-dag.json"


class IncrementalInvalidationTests(unittest.TestCase):
    def test_artifact_lock_is_deterministic_and_hashes_live_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary); note = root / "notes.md"; first = root / "first.json"; second = root / "second.json"
            note.write_text("初稿\n", encoding="utf-8")
            command = [sys.executable, str(LOCK_SCRIPT), "--dag", str(DAG), "--episode-id", "20260822_odyssey",
                       "--artifact", f"show_notes={note}"]
            subprocess.run(command + ["--output", str(first)], check=True)
            subprocess.run(command + ["--output", str(second)], check=True)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            value = json.loads(first.read_text())
            self.assertEqual(value["artifacts"]["show_notes"], value["records"]["show_notes"]["sha256"])
            self.assertEqual(value["records"]["show_notes"]["bytes"], len("初稿\n".encode()))

    def test_show_notes_typo_does_not_invalidate_master_or_asr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary); previous = root / "previous.json"; current = root / "current.json"; report = root / "report.json"
            ids = ["source_media", "release_audio", "archive_master", "postcut_raw_asr", "reviewed_verbatim", "show_notes",
                   "episode_metadata", "metadata_approval", "release_candidate", "release_candidate_approval", "acceptance_report", "preview_html"]
            old = {node: f"{index:064x}"[-64:] for index, node in enumerate(ids, 1)}; new = dict(old); new["show_notes"] = "f" * 64
            previous.write_text(json.dumps({"schema_version": "1.0", "artifacts": old})); current.write_text(json.dumps({"schema_version": "1.0", "artifacts": new}))
            subprocess.run([sys.executable, str(SCRIPT), "--dag", str(DAG), "--previous-lock", str(previous),
                            "--current-lock", str(current), "--output", str(report)], check=True)
            value = json.loads(report.read_text()); self.assertEqual(value["changed_roots"], ["show_notes"])
            self.assertNotIn("release_audio", value["impacted_nodes"]); self.assertNotIn("postcut_raw_asr", value["impacted_nodes"])
            self.assertNotIn("artwork", value["impacted_nodes"]); self.assertNotIn("artwork_approval", value["must_reapprove"])
            self.assertIn("release_audio", value["reusable_nodes"]); self.assertIn("postcut_raw_asr", value["reusable_nodes"])
            self.assertIn("metadata_approval", value["must_reapprove"]); self.assertIn("release_candidate_approval", value["must_reapprove"])


if __name__ == "__main__": unittest.main()
