# Architecture

## Incident lifecycle

1. **Detect** — GuardDuty emits a finding to EventBridge. EKS Protection observes Kubernetes control-plane activity; Runtime Monitoring observes OS-level process, file, and network activity through the GuardDuty agent. The enabled plans determine the available evidence.
2. **Normalize and deduplicate** — validate the event envelope and finding fields, reject malformed events, and use the GuardDuty finding ID plus response playbook version as an idempotency key.
3. **Enrich** — retain the raw finding and query only permitted context: affected cluster/workload/pod/container/process, relevant EKS audit details, tags/ownership, and nearby signals. Record source and timestamp for every field. Avoid inventing missing attribution.
4. **Classify** — apply explicit rules to finding type, severity, account/cluster environment, resource ownership, confidence, and action allow-list. Unknowns fall back to notify-only.
5. **Respond** — invoke one scoped playbook via a workflow. Every action receives a unique incident/action ID and records request, result, and actor role.
6. **Verify and recover** — check that the intended containment took effect, alert on failure, and provide a rollback path. Preserve evidence before disruptive actions where feasible.
7. **Learn** — track time to detect/contain, duplicate rate, false positives, action failures, and rollback frequency. Review playbooks after each demo.

## AWS components proposed for Terraform

- GuardDuty detector and protection plan configuration, subject to region and account support.
- EventBridge rule for selected findings and a separate rule for Runtime Monitoring coverage changes.
- Step Functions Standard workflow for durable, visible branching and retries.
- Lambda functions for validation/enrichment and a separate response adapter.
- IAM roles with separate permissions for read-only enrichment and write-capable response.
- CloudWatch logs/metrics and an encrypted incident/audit store with a defined retention period.
- Optional SNS/email notification for the first demo; later integrate a team incident system if available.

The exact persistence service and retention need a decision before implementation. Avoid storing secrets or unnecessary personal data in incident records.

## Trust boundaries

- GuardDuty/EventBridge event is untrusted input: validate `source`, `detail-type`, account, region, finding ID, finding type, and affected resource before action.
- AI output is untrusted advice: it may summarize evidence but cannot mint permissions, widen scope, or bypass policy gates.
- EKS action credentials are separate from enrichment credentials. Scope namespace and verbs; do not put long-lived kubeconfig credentials in Lambda environment variables.
- The lab account and cluster are disposable. Production environments remain observe-only until safety criteria and approvals are defined.

## Event handling requirements

- Handle duplicate delivery and retries safely.
- Bound API calls and execution time; use backoff for throttling.
- Preserve the original event, normalized incident, enrichment provenance, policy decision, and action result.
- Fail closed to notification when enrichment is unavailable, target identity is ambiguous, or policy evaluation fails.
- Alert on dead-lettered events, failed workflow executions, and unhealthy GuardDuty coverage.
