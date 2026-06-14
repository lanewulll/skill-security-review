from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install-reviewed-skill"


class InstallReviewedSkillTests(unittest.TestCase):
    def test_installs_reviewed_skill_and_writes_attestation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "sample-skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\n"
                "name: sample-skill\n"
                "description: Small harmless sample skill for installer verification.\n"
                "---\n"
                "\n"
                "# Sample Skill\n",
                encoding="utf-8",
            )
            skills_dir = base / "skills"

            result = subprocess.run(
                [sys.executable, str(INSTALLER), str(source), str(skills_dir)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            enabled = skills_dir / "sample-skill"
            self.assertTrue(enabled.is_dir())
            self.assertFalse((skills_dir / "_pending" / "sample-skill").exists())
            attestation = json.loads((enabled / ".skill-review.json").read_text(encoding="utf-8"))
            self.assertEqual(attestation["reviewed_by"], "skill-security-review")
            self.assertEqual(attestation["review_level"], "weak")
            self.assertEqual(attestation["highest_severity"], "none")
            self.assertEqual(attestation["findings_count"], 0)
            self.assertIn("target_hash", attestation)

    def test_blocks_high_risk_skill_in_pending_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "risky-skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\n"
                "name: risky-skill\n"
                "description: Sample skill used to verify install blocking.\n"
                "---\n",
                encoding="utf-8",
            )
            risky_phrase = "r" + "m -rf /"
            (source / "README.md").write_text(
                f"Do not run this example command: {risky_phrase}\n",
                encoding="utf-8",
            )
            skills_dir = base / "skills"

            result = subprocess.run(
                [sys.executable, str(INSTALLER), str(source), str(skills_dir)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 3, result.stderr)
            enabled = skills_dir / "risky-skill"
            pending = skills_dir / "_pending" / "risky-skill"
            self.assertFalse(enabled.exists())
            self.assertTrue(pending.is_dir())
            attestation = json.loads((pending / ".skill-review.json").read_text(encoding="utf-8"))
            self.assertIn(attestation["highest_severity"], {"critical", "high"})
            self.assertGreater(attestation["findings_count"], 0)
            self.assertTrue((pending / ".skill-review-output" / "report.json").is_file())


if __name__ == "__main__":
    unittest.main()
