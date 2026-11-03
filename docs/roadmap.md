# Roadmap

## Milestone 0 — Repository and design (current)

- [x] Define detect/analyze/respond loop and initial architecture.
- [x] Record current GuardDuty terminology, source links, and research gaps.
- [x] Define safe response principles and candidate playbooks.
- [x] Decide lab region: `ap-southeast-1`; use profile `guru`.
- [x] Add the first Terraform stack for EKS, GuardDuty, EventBridge, and observe-only event handling.
- [ ] Decide budget and first containment action.

## Milestone 1 — Validate detection manually

- Provision or use an isolated disposable EKS lab.
- Enable EKS Protection; optionally enable Runtime Monitoring and verify healthy coverage.
- Follow the current Container Security Workshop module 5.3.2 attack-sequence lab.
- Capture sanitized GuardDuty EventBridge events and record required prerequisites and cleanup.

**Acceptance:** reproducible finding; event payload retained; coverage status documented; all lab resources can be torn down; measured cost assumptions recorded.

## Milestone 2 — Terraform detection and observe-only workflow

Starter Terraform is in `infra/dev/`. It is not yet applied to AWS.

- Implement reusable Terraform modules for GuardDuty configuration, event routing, workflow, least-privilege IAM, logging, and notifications.
- Add event validation, deduplication, incident record, and deterministic classification.
- Keep all remediation disabled; add a `dry_run`/observe-only default.

**Acceptance:** real finding reaches workflow once logically; duplicate deliveries do not duplicate incident/action; malformed or unknown events notify without mutation; failures are visible.

## Milestone 3 — One scoped automatic containment

- Select one reversible action with namespace/workload-level scope.
- Add explicit environment allow-list, action TTL, audit record, verification, rollback, and emergency disable.
- Test positive, negative, duplicate, timeout, and partial-failure cases using representative events.

**Acceptance:** only the intended demo workload changes; action can be verified and reversed; missing context never causes a write action.

## Milestone 4 — AI-assisted analysis

- Add a read-only summarizer over curated incident evidence.
- Require evidence references and mark uncertainty; compare summaries to a human-reviewed baseline.
- Keep deterministic policy as sole action authorization point.

**Acceptance:** AI cannot directly invoke mutation tools; summary quality and latency are measured; sensitive fields are minimized.

## Milestone 5 — Operational hardening

- Add multi-account strategy only if needed, dashboards/SLOs, cost controls, retention policy, runbooks, and incident ownership.
- Review IAM, encryption, logging access, data handling, and failure modes.

## First implementation task

Before writing Terraform, run the workshop scenario and save a sanitized event fixture (remove account IDs, ARNs, IPs, names, and identifiers as needed). This fixture will guide EventBridge filters, normalization, and policy tests.
