# Response playbooks

P0 is the default branch for every GuardDuty EKS attack-sequence event routed by the EventBridge rule. P1 is implemented for the opted-in `guarduty-demo` sandbox pod and has been tested with a traffic probe and rollback. P2 remains a design candidate.

## P0 — Analyze and notify (active default)

**Trigger:** a new `AttackSequence:EKS/CompromisedCluster` finding.

1. Validate event source, account, region, finding ID, resource type, and schema.
2. Deduplicate and store the raw event plus normalized incident.
3. Enrich with cluster and workload metadata; preserve source and timestamp.
4. Store analysis and workflow status. Alarms notify through SNS only for workflow failures and DLQ messages; per-finding notifications are not implemented yet.

No Kubernetes mutation occurs on this branch. The sample fixture tested in AWS correctly selected this path because its account/cluster did not match the lab.

## P1 — Quarantine identified demo workload (implemented, tightly gated)

**Trigger:** critical EKS attack-sequence finding, exact allow-listed lab cluster, unambiguous workload target, enrichment complete, and policy version enabled.

1. Capture incident evidence and identify the owning controller/workload.
2. Confirm target is in the dedicated demo namespace and not on an exclusion list.
3. Apply a narrow, reversible quarantine control supported by the lab CNI: an action-specific NetworkPolicy selecting the observed pod labels. Avoid deleting pods.
4. Adapter verifies NetworkPolicy persistence and exact pod selector; a separate probe test verified traffic blocking.
5. Step Functions records containment and waits 15 minutes, then removes only the policy labeled with this finding ID.
6. Record action/release status in DynamoDB; CloudWatch workflow failure/DLQ alarms publish to SNS (topic still needs a subscription).

**Fail safe:** unknown namespace, ambiguous ownership, unsupported policy behavior, timeout, or verification failure results in alert-only and a failed-action record. The policy must define whether to leave a partially applied control in place or roll it back.

## P2 — High-impact containment (out of MVP)

Examples include scaling a deployment to zero, isolating a node, or revoking credentials. These may interrupt service or destroy evidence. Require an explicit approval path, impact analysis, and tested recovery procedure before automation.

## Rollback checklist

- Confirm incident commander/workload owner and current incident state.
- Remove only the quarantine object created by the action ID; do not remove pre-existing policies.
- Verify connectivity and workload health.
- Mark incident recovered and retain action/rollback audit records.
- Review whether the finding was accurate and tune the policy without suppressing correlated signals broadly.
