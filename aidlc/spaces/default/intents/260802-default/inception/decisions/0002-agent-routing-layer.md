# ADR 0002: Agent Routing Layer

- Status: Accepted
- Date: 2026-05-02

## Context

Cloud-360 must coordinate multiple AI capabilities: architecture design, cross-cloud service selection, FinOps, Terraform generation, operations review, security policy advisory and cloud tool execution.

A single monolithic agent would make routing, permission checks, auditability and context reuse difficult. Cloud-360 therefore needs an explicit Agent Routing Layer.

## Decision

Cloud-360 will use an OpenClaw-like multi-agent routing layer.

Initial agent roles:

- **Routing Agent**：classifies intent and orchestrates task flow。
- **Intent Parser Agent**：extracts requirements, assumptions and missing inputs。
- **Design Agent**：creates architecture candidates and diagrams。
- **Component Selection Agent**：maps workloads to AWS/GCP/Azure services。
- **FinOps Agent**：estimates cost and compares pricing strategies。
- **IaC Agent**：generates Terraform / OpenTofu modules。
- **Operations Agent**：reviews performance, reliability and modernization opportunities。
- **Security Policy Advisor Agent**：reviews security posture and recommends policies。
- **Tool Execution Agent**：executes approved MCP / SDK / CLI / Skill calls。
- **Guardrail Agent**：enforces permission, approval and safety policies。

## Shared Context

Agents must share structured context through memory and artifact stores:

- user requirement
- assumptions
- architecture graph
- draw.io XML
- cost model
- selected cloud components
- generated IaC
- security findings
- approval decisions
- audit records

## Safety Model

Read-only queries may execute after policy classification. High-risk actions require human approval:

- write / delete / deploy
- IAM/RBAC or permission changes
- firewall / security group / NSG changes
- KMS / key policy changes
- storage access changes
- production Terraform apply
- scaling changes with cost or availability impact

## Consequences

- Agents can be developed and tested independently.
- Tool execution is isolated behind policy and approval gates.
- All recommendations can be traced to source context and tool output.
- Future agents can be added through ADRs without changing the core platform contract.
