# ADR 0001: Deterministic response before AI execution

- Status: accepted for the MVP
- Date: 2026-11-03

## Context

The project aims to detect incidents, analyze causes, and initiate corrective action without human intervention. A finding can be incomplete or ambiguous, and automated EKS changes can disrupt workloads. An LLM can produce plausible but incorrect interpretations and should not be an authorization boundary.

## Decision

Build event validation, enrichment, classification, and action authorization as deterministic, versioned policy. Default to observe-only. AI may later summarize evidence and recommend a playbook, but it cannot directly call mutation APIs or override policy. Enable write actions only for explicit resource allow-lists and reversible playbooks with verification and rollback.

## Consequences

- The first version has less autonomy but is easier to replay, audit, and validate.
- AI integration remains possible once event fixtures and action outcomes exist.
- The team must define resource ownership, containment scope, and recovery before enabling writes.
