# Research notes

Checked against AWS documentation on 2026-11-03. AWS service behavior and workshop content can change; recheck before implementation.

## Current terminology and findings

- **EKS Protection** covers Kubernetes audit log based detection and is a separate GuardDuty protection plan; it does not require the Runtime Monitoring agent.
- **Runtime Monitoring** is the consolidated feature name. For EKS it uses the GuardDuty security agent/add-on. AWS docs describe runtime observation such as process execution, file access, and network connections. Coverage must be monitored; unhealthy coverage means runtime telemetry may not reach GuardDuty.
- **Extended Threat Detection** is enabled automatically for GuardDuty accounts and correlates available signals. For EKS attack sequence detection, AWS says at least EKS Protection or Runtime Monitoring with the EKS add-on is required; both give broader coverage. Attack-sequence findings are sent to EventBridge like other findings.
- The finding `AttackSequence:EKS/CompromisedCluster` represents correlated suspicious activity, not a complete forensic root-cause report. The workflow should preserve signals and add resource ownership/context before selecting a response.
- GuardDuty sends new and aggregated findings to EventBridge. Rules should match the actual event schema and be tested with captured sample events.
- Older EKS Runtime Monitoring settings do not automatically migrate to consolidated Runtime Monitoring; migration/configuration should be checked when using an account with legacy settings.

## Workshop notes from project research

- Container Security Workshop module 5.3.2: [Generate and Respond to an EKS Attack Sequence](https://catalog.workshops.aws/containersecurity/en-US/module5/module5-3/module5-3-2). Reported project notes say it applies `mitre-attack-sequence.yaml` and runs `nmap`, then observes the attack sequence. Verify prerequisites and exact steps in the current workshop before running.
- GuardDuty + Detective workshop: [Respond to EKS attack sequence findings](https://catalog.workshops.aws/security/en-US/amazon-guardduty-and-amazon-detective-workshop/respond-to-eks-attack-sequence-findings). Use it to understand investigation and resource relationships.
- Container Security Workshop module 6: [Detective and incident response](https://catalog.workshops.aws/containersecurity/en-US/module6). Useful for correlation and Finding Groups.
- Workshop environment requirements, EC2/EKS cost, regions, and teardown steps need validation before choosing the lab design. The workshop's dedicated account/cluster may differ from our eventual Terraform lab.

## Improvement opportunities

1. **Close the feedback loop** — define objective acceptance measures: finding received, context completeness, correct policy branch, containment verified, rollback successful, and elapsed time for each stage.
2. **Treat coverage as an SLO** — alert when Runtime Monitoring coverage is unhealthy and expose coverage next to findings so absence of a runtime finding is not interpreted as absence of an attack.
3. **Make response proportional** — separate notify, simulate, reversible quarantine, and high-impact shutdown; apply environment-aware gates and require approval for high-impact actions.
4. **Build forensic context** — preserve raw finding, event time, resource IDs, process/container details, relevant audit trail, workload owner, and correlation links. Record uncertainty and provenance.
5. **Prevent unsafe repeats** — idempotency, deduplication, bounded retries, replay protection, dead-letter handling, and per-resource cooldowns.
6. **Validate policy with replay** — store sanitized sample events and replay them against policy in CI or locally; include benign, malformed, duplicate, and unknown-resource cases.
7. **Keep AI bounded** — use AI for incident summaries, evidence gaps, and playbook recommendation; require a deterministic policy engine to authorize any action. Log model/prompt version and cited evidence. Never pass raw credentials or unrestricted tools to an agent.
8. **Plan rollback and blast-radius limits** — define quarantine expiry, recovery ownership, exception handling, and an emergency disable switch before enabling writes.
9. **Manage cost and cleanup** — isolate demo workloads; set budget alerts and explicit teardown. EKS control plane, compute, NAT, GuardDuty plans, logs, and data retention can all affect cost.

## Open questions before Terraform

- Which AWS region and account are available, and can the team create EKS/GuardDuty/IAM/EventBridge/Step Functions resources there?
- Use workshop-provided cluster or create a minimal disposable cluster? Which CNI/network policy implementation will be used?
- What is the first automatic response: namespace-scoped quarantine, block egress, or another reversible action?
- Which workload types are safe to affect, who owns them, and how long can quarantine last?
- What incident record retention and notification target are acceptable?
- Is AI in the first demo limited to read-only summarization, or deferred until the deterministic pipeline is measured?

## Primary sources

- [GuardDuty Extended Threat Detection](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty-extended-threat-detection.html)
- [Processing GuardDuty findings with EventBridge](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings_eventbridge.html)
- [How Runtime Monitoring works](https://docs.aws.amazon.com/guardduty/latest/ug/how-does-runtime-monitoring-work.html)
- [Runtime Monitoring coverage for EKS](https://docs.aws.amazon.com/guardduty/latest/ug/eks-runtime-monitoring-coverage.html)
- [Runtime Monitoring finding types](https://docs.aws.amazon.com/guardduty/latest/ug/findings-runtime-monitoring.html)
- [GuardDuty attack sequence finding types](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty-attack-sequence-finding-types.html)
- [EKS GuardDuty integration](https://docs.aws.amazon.com/eks/latest/userguide/integration-guardduty.html)
