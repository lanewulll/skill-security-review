# Dynamic Review Expansion Implementation Plan

## Summary

Expand `skill-security-review` Docker strong review from the current dynamic bait/timeout checks into 12 telemetry-backed behavior categories. Weak review remains static and never executes target code. Strong review remains fail-closed and only executes target package behavior inside the existing Docker audit sandbox.

The public repository remains a release-package style repo: edit the extracted `assets/skill-security-review.pyz` runtime source, then rebuild the zipapp with deterministic timestamps while preserving the existing two runtime entries.

## Implementation Changes

- Preserve the existing Docker sandbox constraints: `--network none`, read-only root, `--cap-drop ALL`, `no-new-privileges`, memory/CPU/pids limits.
- Extend bait fixtures with provider token environment variables and writable decoy config paths under `/home/audit`.
- Run every dynamic probe through `strace -f -qq -s 256 -o /workspace/strace.log -e trace=file,process,network`.
- Emit structured telemetry in `dynamic_review.events`, `dynamic_review.telemetry_files`, and `dynamic_review.rule_counts`.
- Implement 12 dynamic rule IDs:
  - `dynamic-credential-bait-access`
  - `dynamic-network-attempt`
  - `dynamic-network-bait-exfiltration`
  - `dynamic-env-enumeration`
  - `dynamic-persistence-write`
  - `dynamic-agent-config-modification`
  - `dynamic-workspace-boundary-write`
  - `dynamic-dangerous-process`
  - `dynamic-privilege-escalation`
  - `dynamic-package-manager-side-effect`
  - `dynamic-sandbox-escape-probe`
  - `dynamic-resource-abuse`
- Keep `dynamic-command-timeout` as a compatibility finding when timeout/resource-abuse behavior is detected.
- Redact bait values before writing JSON reports, Markdown reports, dynamic events, violation evidence, stdout, or stderr.

## Public Interfaces

- Preserve existing report fields: `dynamic_review.ran`, `dynamic_review.events`, `dynamic_review.violations`, top-level `docker`, and top-level `findings`.
- Add `dynamic_review.telemetry_files`, `dynamic_review.rule_counts`, and per-event `signals`.
- Event shape includes `test_id`, `action`, `target`, `argv`, `exit_code`, `timed_out`, `stdout`, `stderr`, `signals`, and `metadata`.
- Strong review remains fail-closed when Docker CLI, Docker daemon, or the audit image is unavailable.

## Test Plan

- Add `unittest` coverage that extracts and imports the zipapp runtime, then tests dynamic rule functions with synthetic telemetry.
- Cover all 12 dynamic rule IDs, timeout compatibility, finding conversion, and redaction.
- Keep the Docker fail-closed regression test.
- Add optional Docker integration coverage gated by `SKILL_REVIEW_RUN_DOCKER_TESTS=1`.

## Verification

- `python3 scripts/verify-runtime`
- `python3 -m unittest discover -s tests -v`
- `docker build -f docker/audit-sandbox.Dockerfile -t skill-review-audit:local .`
- `scripts/skill-security-review scan <fixture-skill> --review-level strong --json-only`
- `scripts/skill-security-review scan . --review-level weak --out <tmp>`
