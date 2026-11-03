# Response playbooks (proposed)

These are design candidates, not deployed actions. Confirm Kubernetes networking semantics and workload ownership in the selected lab before implementation.

## P0 — Observe and notify (default)

**Trigger:** any new GuardDuty finding.

1. Validate event source, account, region, finding ID, resource type, and schema.
2. Deduplicate and store the raw event plus normalized incident.
3. Enrich with cluster and workload metadata; preserve source and timestamp.
4. Notify with severity, finding type, affected resource, console link, missing evidence, and workflow status.

No Kubernetes mutation occurs.

## P1 — Quarantine identified demo workload (candidate)

**Trigger:** critical EKS attack-sequence finding, exact allow-listed lab cluster, unambiguous workload target, enrichment complete, and policy version enabled.

1. Capture incident evidence and identify the owning controller/workload.
2. Confirm target is in the dedicated demo namespace and not on an exclusion list.
3. Apply a narrow, reversible quarantine control supported by the lab's CNI (candidate: namespace/workload-scoped NetworkPolicy). Avoid deleting all pods.
4. Verify intended traffic is restricted and unrelated namespaces remain healthy.
5. Record action result and notify the operator.
6. Apply an expiry or require an explicit recovery workflow; do not silently leave quarantine indefinite.

**Fail safe:** unknown namespace, ambiguous ownership, unsupported policy behavior, timeout, or verification failure results in alert-only and a failed-action record. The policy must define whether to leave a partially applied control in place or roll it back.

## P2 — High-impact containment (out of MVP)

Examples include scaling a deployment to zero, isolating a node, or revoking credentials. These may interrupt service or destroy evidence. Require an explicit approval path, impact analysis, and tested recovery procedure before automation.

## Rollback checklist

- Confirm incident commander/workload owner and current incident state.
- Remove only the quarantine object created by the action ID; do not remove pre-existing policies.
- Verify connectivity and workload health.
- Mark incident recovered and retain action/rollback audit records.
- Review whether the finding was accurate and tune the policy without suppressing correlated signals broadly.
