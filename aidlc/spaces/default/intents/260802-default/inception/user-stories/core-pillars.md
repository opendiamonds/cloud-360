# Cloud-360 Core Pillars User Stories

> 本文件必須同時包含中文版與英文版。
> This document must include both Chinese and English versions.

## A. Architecture Design

### A1. Natural Language to Architecture

As a Cloud Architect, I want to describe requirements in natural language so that Cloud-360 can generate an initial cloud architecture blueprint.

Acceptance criteria:

- Extracts workload, HA, DR, scalability, region, security and compliance requirements.
- Produces Mermaid, PlantUML or draw.io output.
- Explains assumptions and trade-offs.

### A2. Well-Architected Review

As an SRE, I want Cloud-360 to check whether an architecture follows cloud provider best practices.

Acceptance criteria:

- Covers reliability, security, cost optimization, operational excellence and performance.
- Produces severity, impact and remediation recommendations.

### A3. AI + draw.io Co-editing

As a Cloud Architect, I want AI Chat to co-edit an online draw.io / diagrams.net architecture canvas.

Acceptance criteria:

- Supports `.drawio` / XML source format.
- AI can add/remove nodes, update connections and annotate data flow.
- Every AI modification includes a change summary and version history.
- Diagram structure can be parsed into shared architecture context.

## B. Cross-Cloud Component Selection

### B1. Service Comparison Matrix

As a technical decision maker, I want to compare equivalent AWS/GCP/Azure services.

Acceptance criteria:

- Includes SLA, limits, compatibility, cost risk, lock-in risk and operational complexity.
- Supports compute, database, storage, network, Kubernetes, messaging and AI/ML categories.

### B2. Workload-Based Recommendation

As an SRE, I want Cloud-360 to recommend cloud services based on workload profile.

Acceptance criteria:

- Uses QPS, concurrency, data size, latency target, region and compliance constraints.
- Provides rationale, alternatives and known limitations.

## C. Cost Estimation & FinOps

### C1. Monthly TCO Estimation

As a FinOps analyst, I want monthly cost estimation for a proposed architecture.

Acceptance criteria:

- Estimates compute, database, cache, storage, network, CDN, egress and observability.
- Shows pricing assumptions and source timestamp.

### C2. Spot / Preemptible Comparison

As an SRE, I want to compare on-demand and interruptible pricing options.

Acceptance criteria:

- Covers AWS Spot, Azure Spot and GCP Spot / Preemptible.
- Includes savings estimate and interruption risk.

### C3. Cross-Cloud Egress Analysis

As an architect, I want to understand data egress cost in multi-cloud designs.

Acceptance criteria:

- Distinguishes intra-region, inter-region, internet egress and cross-cloud traffic.
- Flags expensive or risky traffic paths.

## D. Terraform / OpenTofu IaC Generation

### D1. Modular IaC Generation

As a platform engineer, I want Cloud-360 to generate modular Terraform / OpenTofu code.

Acceptance criteria:

- Generates `providers.tf`, `main.tf`, `variables.tf`, `outputs.tf` and `modules/`.
- Supports `aws`, `google` and `azurerm` providers.
- Does not generate plaintext secrets.

### D2. IaC Security Scan

As a security reviewer, I want generated IaC to be scanned before use.

Acceptance criteria:

- Supports tfsec, trivy or Checkov.
- Flags public storage, overly broad ingress, missing encryption and excessive IAM/RBAC.
- Produces remediation guidance.

## E. Operations Optimization Review

### E1. Right-sizing Recommendation

As an SRE, I want right-sizing recommendations based on observed utilization.

Acceptance criteria:

- Analyzes CPU, memory, IOPS, network and storage.
- Estimates cost impact after changes.
- Requires approval before changing production resources.

### E2. Architecture Modernization

As a Cloud Architect, I want modernization recommendations based on new cloud services.

Acceptance criteria:

- Identifies legacy, high-maintenance or high-cost services.
- Suggests managed, serverless, container or event-driven alternatives.
- Includes migration risk and expected benefits.

## F. AI Multi-Cloud Operations

### F1. AI Chat Cloud Query

As an SRE, I want to query AWS/GCP/Azure status through AI Chat.

Acceptance criteria:

- Supports account/project/subscription and region selection.
- Can query resource inventory, cost, metrics, logs and IAM/security findings.
- Includes data source and query time.
- Redacts secrets.

### F2. AI Chat Cloud Operation

As a platform engineer, I want to request cloud operations through AI Chat.

Acceptance criteria:

- Read-only actions can execute after policy classification.
- Write/delete/deploy/permission changes require human approval.
- Shows plan, impact, rollback and verification steps.
- Records audit log.

### F3. Agentic AI Operations

As an operations lead, I want background agents to proactively identify issues.

Acceptance criteria:

- Detects cost spikes, security risks, availability gaps and performance bottlenecks.
- Produces recommendations and remediation plans.
- Does not execute high-risk changes without explicit approval.

## G. Cloud Security Posture & Policy Advisory

### G1. Multi-Cloud Security Review

As a Security Reviewer, I want Cloud-360 to inspect security posture across AWS/GCP/Azure.

Acceptance criteria:

- Checks IAM/RBAC, network exposure, storage access, encryption, audit logging and policy guardrails.
- Produces severity, evidence, impact and remediation.

### G2. Least-Privilege Analysis

As a platform admin, I want Cloud-360 to detect over-permissive identities.

Acceptance criteria:

- Detects wildcard permissions, stale identities and unused permissions.
- Generates least-privilege recommendations.

### G3. Policy-as-Code Recommendation

As a platform engineer, I want security policies expressed as maintainable policy code.

Acceptance criteria:

- Supports Terraform patch suggestions, OPA/Rego, Sentinel, Azure Policy, GCP Org Policy and AWS Config rule recommendations.
- Requires approval before applying policy changes.

## H. Web-Based Desktop and Mobile Experience

### H1. Desktop Web Full Workspace

As a Cloud Architect, I want the desktop browser experience to provide the full Cloud-360 workspace.

Acceptance criteria:

- Supports AI Chat, draw.io editor, IaC editor, FinOps dashboard, Security dashboard, Ops dashboard and agent trace.

### H2. Mobile Web Ops Companion

As an SRE, I want a mobile browser experience for quick operations and approvals.

Acceptance criteria:

- Delivered through responsive web / PWA.
- Supports AI Chat, alerts, approvals, health digest, findings and readonly architecture diagrams.
- Does not require native iOS or Android app.

### H3. Mobile Web Approval

As a platform owner, I want to approve or reject operations from mobile web safely.

Acceptance criteria:

- Shows plan, affected resources, risk, impact and rollback.
- High-risk approval requires MFA, passkey or WebAuthn.
- Records audit log and supports timeout/escalation.

## I. MCP & Skill Management

### I1. MCP Server Registry

As a platform engineer, I want to register and manage MCP servers so that Cloud-360 can safely expose external and internal tools to agents.

Acceptance criteria:

- Supports server name, endpoint/transport, owner, environment, auth scope, enabled status and version.
- Supports health checks for availability, schema compatibility, latency and recent errors.
- Disallows secrets in stored configuration or logs.

### I2. Skill Catalog

As an AI platform operator, I want to manage reusable AI Skills so that agents can reuse approved workflows.

Acceptance criteria:

- Tracks skill name, domain, owner, version, description, required tools, risk level and change log.
- Supports enable, disable, deprecate and rollback states.
- Shows dependencies between skills, MCP tools, SDK/CLI wrappers and cloud providers.

### I3. Tool Permission and Risk Model

As a security reviewer, I want every MCP tool and Skill to have a permission/risk classification.

Acceptance criteria:

- Classifies tools as read-only, write, deploy, delete, permission-change or production-impacting.
- High-risk tools require approval before enablement or execution.
- Agent Routing Layer must use this classification before selecting tools.

### I4. MCP / Skill Approval Workflow

As a platform owner, I want risky MCP/Skill changes to require approval.

Acceptance criteria:

- Adding a new high-risk tool requires review.
- Expanding auth scope requires approval.
- Disabling critical tools requires impact summary and rollback plan.
- All changes are written to audit log.

### I5. Agent Tool Selection Observability

As an SRE, I want to see why an agent selected a specific MCP tool or Skill.

Acceptance criteria:

- Shows selected tool/skill, reason, input summary, permission level, approval status and execution result.
- Redacts secrets and sensitive payloads.
- Links tool execution back to user request, agent trace and audit log.

## J. Identity Authentication & Role-Based Access Control

### J1. Unified Login Portal

As a platform user, I want a secure and independent login page to authenticate my credentials and start my session.

Acceptance criteria:

- Provides a dedicated web login page for username and password authentication.
- Implements secure token delivery and encrypted session storage in the browser with token expiration.
- Returns generic, obfuscated error messages for failed login attempts to prevent user enumeration.

### J2. Role-Based Page Visibility

As a logged-in user, I want my workspace navigation and page visibility to be restricted to my role's permissions.

Acceptance criteria:

- Dynamically hides or shows sidebar options and menus based on the current user role.
- Intercepts manual URL route changes and redirects unauthorized access attempts to a 403 Forbidden page.
- Back-end APIs must simultaneously validate user roles and token scopes to prevent front-end bypass.

### J3. Admin Permission Console

As a platform administrator, I want to edit and assign user roles and permissions dynamically so that I can enforce least privilege.

Acceptance criteria:

- Provides an administrator-only control panel listing all users and their assigned roles.
- Allows administrators to dynamically update a user's role, taking effect immediately upon the next user refresh.
- Enforces mandatory audit logging for every role change event, specifying the administrator, the target user, and the role changes.
