# ADR 0001: Cloud-360 Repository Scope

- Status: Accepted
- Date: 2026-05-02
- Amendment 2026-05-09: paths updated by ADR-0006 PR2 — SDD artifacts moved from `docs/` into `aidlc-docs/inception/{requirements,application-design,user-stories,decisions}/`. Scope unchanged.

## Context

Cloud-360 is being defined through Spec-Driven Development before application implementation begins. The repository needs a clear contract so future changes can extend the platform safely without introducing production configuration, secrets, or uncontrolled cloud operations.

The platform vision is an AI-native multi-cloud architecture, governance, security and operations platform for Cloud Architects, SRE, FinOps and Security teams.

## Decision

This repository tracks the Cloud-360 SDD baseline:

1. Product README.
2. System Requirement Specification under `aidlc-docs/inception/requirements/`.
3. System architecture documents under `aidlc-docs/inception/application-design/`.
4. User stories under `aidlc-docs/inception/user-stories/`.
5. Architecture Decision Records under `aidlc-docs/inception/decisions/`.
6. Repository validation script under `scripts/`.
7. Baseline GitHub Actions CI under `.github/workflows/`.

Cloud-360 scope includes:

- AWS / GCP / Azure multi-cloud architecture design.
- Cross-cloud component selection.
- FinOps and cost estimation.
- Terraform / OpenTofu IaC generation.
- Operations optimization.
- AI Chat driven cloud management.
- Agentic AI proactive operations analysis.
- Cloud Security Posture & Policy Advisory.
- draw.io / diagrams.net compatible architecture canvas.
- Web-based desktop and mobile experience.

## Guardrails

The repository must not introduce the following without a future explicit ADR and approval:

- Plaintext cloud credentials or secrets.
- Production-specific deployment configuration.
- Direct production Terraform state or backend configuration.
- Autonomous destructive cloud actions.
- Unreviewed IAM/RBAC, firewall, KMS, storage policy or production-impacting changes.

All write/delete/deploy/permission-changing cloud operations must include:

- plan
- impact analysis
- affected resources
- rollback strategy
- verification steps
- human approval gate
- audit log

## Branch Collaboration Constraint

`feature/cloud_architecture` is a collaborative branch and must remain read-only unless Danniel explicitly authorizes modifications. Do not clean, rebase, force-push, delete, or rewrite that branch.

## Consequences

- README is now allowed to represent Cloud-360 product direction.
- SDD documents become the source of truth for initial implementation.
- CI validates that required contract documents exist and contain key platform concepts.
- Future implementation work should extend this contract through new ADRs and tests.
