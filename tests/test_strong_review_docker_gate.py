from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "skill-security-review"


class StrongReviewDockerGateTests(unittest.TestCase):
    def test_strong_review_fails_closed_when_docker_daemon_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fake_bin = base / "bin"
            fake_bin.mkdir()
            docker = fake_bin / "docker"
            docker.write_text(
                "#!/usr/bin/env sh\n"
                "if [ \"$1\" = \"info\" ]; then\n"
                "  echo 'daemon unavailable' >&2\n"
                "  exit 1\n"
                "fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
            skill = base / "skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: sample\ndescription: sample\n---\n",
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
                "SKILL_REVIEW_DOCKER_WAIT_SECONDS": "0",
            }

            result = subprocess.run(
                [str(WRAPPER), "scan", str(skill), "--review-level", "strong", "--json-only"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 78, result.stderr)
            self.assertIn("Strong review requires Docker", result.stderr)
            self.assertIn("install Docker", result.stderr)
            self.assertIn("--review-level weak", result.stderr)


if __name__ == "__main__":
    unittest.main()
