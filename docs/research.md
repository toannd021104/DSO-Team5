# Research notes

Checked against AWS documentation on 2026-11-03. AWS service behavior and workshop content can change; recheck before implementation.

## Current terminology and findings

- **EKS Protection** covers Kubernetes audit log based detection and is a separate GuardDuty protection plan; it does not require the Runtime Monitoring agent.
- **Runtime Monitoring** is the consolidated feature name. For EKS it uses the GuardDuty security agent/add-on. Terraform AWS provider feature configuration uses the `RUNTIME_MONITORING` feature name with `EKS_ADDON_MANAGEMENT`; this differs from the older `EKS_RUNTIME_MONITORING` API feature name. AWS docs describe runtime observation such as process execution, file access, and network connections. Coverage must be monitored; unhealthy coverage means runtime telemetry may not reach GuardDuty.
- **Extended Threat Detection** is enabled automatically for GuardDuty accounts and correlates available signals. For EKS attack sequence detection, AWS says at least EKS Protection or Runtime Monitoring with the EKS add-on is required; both give broader coverage. Attack-sequence findings are sent to EventBridge like other findings.
- The finding `AttackSequence:EKS/CompromisedCluster` represents correlated suspicious activity, not a complete forensic root-cause report. The workflow should preserve signals and add resource ownership/context before selecting a response.
- GuardDuty sends new and aggregated findings to EventBridge. Rules should match the actual event schema and be tested with captured sample events.
- Older EKS Runtime Monitoring settings do not automatically migrate to consolidated Runtime Monitoring; migration/configuration should be checked when using an account with legacy settings.

## Workshop notes from project research

- Container Security Workshop module 5.3.2: [Generate and Respond to an EKS Attack Sequence](https://catalog.workshops.aws/containersecurity/en-US/module5/module5-3/module5-3-2). Reported project notes say it applies `mitre-attack-sequence.yaml` and runs `nmap`, then observes the attack sequence. Verify prerequisites and exact steps in the current workshop before running.
- GuardDuty + Detective workshop: [Respond to EKS attack sequence findings](https://catalog.workshops.aws/security/en-US/amazon-guardduty-and-amazon-detective-workshop/respond-to-eks-attack-sequence-findings). Use it to understand investigation and resource relationships.
- Container Security Workshop module 6: [Detective and incident response](https://catalog.workshops.aws/containersecurity/en-US/module6). Useful for correlation and Finding Groups.
- Workshop environment requirements, EC2/EKS cost, regions, and teardown steps need validation before choosing the lab design. The workshop's dedicated account/cluster may differ from our eventual Terraform lab.

### Run note: reduced runtime exercise

The current [official module 5.3.2](https://catalog.workshops.aws/containersecurity/en-US/module5/module5-3/module5-3-2) manifest includes privileged containers, a host filesystem mount, secret-reading RBAC, Tor traffic, metadata requests, broad subnet scans, log manipulation, and a resource stress loop. We reviewed it but did not apply it to the project cluster. Instead, `examples/safe-eks-runtime-simulation/` runs a scoped pod-list API request and a one-port TCP connect scan against a demo service in an isolated namespace. The exercise completed successfully (HTTP 200, TCP 80 open, scoped API query) but did not generate a finding. We deleted the simulation namespace and verified the demo workload remained healthy. This does not validate attack-sequence correlation.

As a separate documented canary, one DNS lookup to `guarddutyc2activityb.com` from the opted-in demo pod produced a real `Backdoor:Runtime/C&CActivity.B!DNS` finding. GuardDuty included `nslookup`, the exact EKS cluster, pod, container, and DNS request. We deployed a separate EventBridge rule for EKS Runtime Monitoring findings and confirmed its event pattern matches the finding. A replay of the canonical GuardDuty event through Step Functions completed analysis, stored evidence in S3/DynamoDB, created a medium-confidence root-cause hypothesis, chose `NOTIFY_ONLY`, and successfully published a structured SNS message (MessageId returned). The canary finding was created before the EventBridge rule, so automatic EventBridge-to-Step-Functions delivery of this exact event was not observed. SNS has no subscriber. This runtime finding does not exercise attack-sequence correlation or quarantine.

A separate synthetic `AttackSequence:EKS/CompromisedCluster` sample was routed through EventBridge and Step Functions. The analyzer recognized its existing finding ID as a duplicate and selected `NOTIFY_ONLY`, since the fixture references a different account and cluster. This confirms duplicate handling and the safety gate, but it is not a fresh finding analysis or evidence of a real attack sequence.


## Bài học thiết kế cho incident workflow

- AWS chia incident operations thành detect, analyze, contain, eradicate, recover; các pha có thể quay lại nhau khi verification đưa ra evidence mới. Vì vậy workflow cần có nhánh failure/re-analysis, không chỉ một Lambda chạy tuyến tính.
- Attack-sequence finding tổng hợp nhiều signal và có mức Critical, nhưng vẫn là cảnh báo về potential compromise. Phải xem `Actors`, `Resources`, `Signals`, timeline và context account trước khi tác động workload.
- Detective finding groups nhóm evidence theo thời gian, entity và TTP. Dùng để tìm scope/root-cause; không block containment chỉ để chờ nhóm dữ liệu được tạo.
- Response nên staged và reversible. Với EKS, NetworkPolicy quarantine chỉ an toàn khi VPC CNI feature được bật, pod selector rõ, blast radius đoán được và policy đã test đúng traffic paths.
- Reusable AWS project patterns khuyên tách event routing, workflow orchestration, playbook và target action. GuardDuty Automated Response Sample dùng EventBridge/Step Functions/Lambda nhưng tập trung EC2; Incident Response Playbooks có kịch bản Container/EKS riêng. Dùng chúng làm pattern, không sao chép nguyên action EC2 vào EKS.
- AI có thể hỗ trợ tóm tắt triage và nêu evidence gaps. Quyền hành động phải ở deterministic policy/action adapter, được test và version-control.

## Dự án tham khảo

- [aws-samples/amazon-guardduty-automated-response-sample](https://github.com/aws-samples/amazon-guardduty-automated-response-sample) — orchestration pattern EventBridge + Step Functions + Lambda; sample tập trung remediation EC2.
- [aws-samples/aws-incident-response-playbooks](https://github.com/aws-samples/aws-incident-response-playbooks) — triage guide, template playbook, Container/EKS compromise và automation patterns.
- [Container Security Workshop 5.3.2](https://catalog.workshops.aws/containersecurity/en-US/module5/module5-3/module5-3-2) — tạo attack-sequence finding để diễn tập detect/respond.

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

## Open decisions before enabling response

- AWS lab hiện chạy ở `us-east-1`; discovery và deploy của stack thành công. Lần thử ở `ap-southeast-1` bị Organizations policy chặn một số API; giữ region lab ở `us-east-1`.
- Xác định quyền quản trị GuardDuty detector thuộc stack lab hay được team quản lý tập trung; không tạo detector trùng hoặc chiếm state ngoài ý muốn.
- Bật và xác minh network-policy feature trong Amazon VPC CNI; kiểm thử egress, DNS, AWS API và traffic paths trước khi chọn selector cho quarantine.
- Chốt TTL quarantine, owner, recovery criteria và đường khẩn cấp để tắt auto-response.
- Chốt incident store retention, encryption/KMS ownership và notification target.
- Chọn AI model/provider sau khi có finding fixtures và baseline; AI chỉ read-only.

## Primary sources

- [GuardDuty Extended Threat Detection](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty-extended-threat-detection.html)
- [Processing GuardDuty findings with EventBridge](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings_eventbridge.html)
- [How Runtime Monitoring works](https://docs.aws.amazon.com/guardduty/latest/ug/how-does-runtime-monitoring-work.html)
- [Runtime Monitoring coverage for EKS](https://docs.aws.amazon.com/guardduty/latest/ug/eks-runtime-monitoring-coverage.html)
- [Runtime Monitoring finding types](https://docs.aws.amazon.com/guardduty/latest/ug/findings-runtime-monitoring.html)
- [GuardDuty attack sequence finding types](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty-attack-sequence-finding-types.html)
- [EKS GuardDuty integration](https://docs.aws.amazon.com/eks/latest/userguide/integration-guardduty.html)
- [Amazon Detective finding groups](https://docs.aws.amazon.com/detective/latest/userguide/groups-about.html)
- [Amazon Detective with EKS](https://docs.aws.amazon.com/eks/latest/userguide/integration-detective.html)
- [AWS incident response containment guidance](https://docs.aws.amazon.com/security-ir/latest/userguide/contain.html)
- [AWS Well-Architected automated response](https://docs.aws.amazon.com/wellarchitected/2023-10-03/framework/sec_detect_investigate_events_auto_response.html)
- [EKS VPC CNI network policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
