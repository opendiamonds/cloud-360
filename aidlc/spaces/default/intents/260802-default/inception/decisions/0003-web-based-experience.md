# ADR 0003: Web-Based Desktop and Mobile Experience

- Status: Accepted
- Date: 2026-05-02

## Context

Cloud-360 must support both desktop usage and mobile usage, but the first phase should avoid native iOS and Android development complexity.

The platform also includes draw.io / diagrams.net editing, dashboards, AI Chat, approval workflows and audit trails. These capabilities can share one Web application architecture with responsive layouts.

## Decision

Cloud-360 will be delivered as a Web-first platform.

Supported first-phase UI surfaces:

- Desktop Web
- Tablet Web
- Mobile Web
- Responsive Web
- Optional PWA features

Out of initial scope:

- Native iOS app
- Native Android app

## Desktop Web Responsibilities

Desktop Web provides the full workspace:

- AI Chat
- draw.io / diagrams.net co-editing
- Terraform / policy code editor
- FinOps dashboard
- Security posture dashboard
- Operations dashboard
- Agent workflow trace
- Audit log
- Approval gate management

## Mobile Web Responsibilities

Mobile Web is an ops companion:

- AI Chat
- Alerts
- Approval / rejection workflow
- Cloud health digest
- Cost / security / operations findings
- Readonly architecture diagram review
- Incident quick triage

Mobile Web is not the primary interface for large-scale architecture diagram editing or deep Terraform development.

## Security Requirements

High-risk mobile approvals must support strong confirmation, such as:

- MFA
- passkey
- WebAuthn
- session re-authentication

All approvals and rejections must be written to audit log.

## Consequences

- The platform can share backend, API, authentication, RBAC, audit log and agent context across desktop and mobile web.
- UI implementation must prioritize responsive layout and mobile-readable summaries.
- Native app work can be reconsidered later through a separate ADR.
