from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "assets" / "skill-security-review.pyz"


class GitleaksDerivedRulesTests(unittest.TestCase):
    def test_detects_vendored_provider_secret_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skill = base / "sample-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\n"
                "name: sample-skill\n"
                "description: Sample skill with provider token fixtures.\n"
                "---\n",
                encoding="utf-8",
            )
            (skill / "tokens.txt").write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY="
                        + "sk-proj-"
                        + "A" * 74
                        + "T3BlbkFJ"
                        + "B" * 74,
                        "ANTHROPIC_API_KEY="
                        + "sk-ant-api03-"
                        + "C" * 93
                        + "AA",
                        "GITLAB_TOKEN=glpat-" + "D" * 20,
                        "NPM_TOKEN=npm_" + "e" * 36,
                        "PYPI_TOKEN=pypi-AgEIcHlwaS5vcmc" + "f" * 60,
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNTIME),
                    "scan",
                    str(skill),
                    "--review-level",
                    "weak",
                    "--json-only",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            rule_ids = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("gitleaks-derived:openai-api-key", rule_ids)
            self.assertIn("gitleaks-derived:anthropic-api-key", rule_ids)
            self.assertIn("gitleaks-derived:gitlab-pat", rule_ids)
            self.assertIn("gitleaks-derived:npm-access-token", rule_ids)
            self.assertIn("gitleaks-derived:pypi-upload-token", rule_ids)
            for finding in report["findings"]:
                if finding["rule_id"].startswith("gitleaks-derived:"):
                    self.assertEqual(finding["severity"], "critical")
                    self.assertIn("gitleaks-derived", finding["categories"])
                    self.assertIn("Gitleaks", finding["standards"])


if __name__ == "__main__":
    unittest.main()
