# ADR 0004: MCP and Skill Management

- Status: Accepted
- Date: 2026-05-02

## Context

Cloud-360 depends on MCP servers, MCP tools, cloud SDK/CLI wrappers, Terraform/OpenTofu utilities and reusable AI Skills to operate across AWS, GCP and Azure. These tool capabilities must be governed like platform infrastructure, not treated as ad-hoc prompt helpers.

Without a management layer, agents could select tools with unclear permissions, outdated schemas, unhealthy endpoints or excessive authorization scope.

## Decision

Cloud-360 will include a first-class **MCP & Skill Management** capability.

The platform will maintain registries for:

- MCP servers
- MCP tools
- AI Skills
- Cloud SDK / CLI wrappers
- Terraform / OpenTofu and security scanning tools
- Internal platform tools and workflows

Each registry entry must track:

- name
- description
- owner
- version
- enabled / disabled / deprecated status
- environment scope
- auth scope
- risk level
- dependencies
- health check status
- change history
- approval state

## Permission and Risk Classification

Every MCP tool and Skill must be classified as one or more of:

- read-only
- write
- deploy
- delete
- permission-change
- production-impacting

Read-only tools may be executed after policy classification. High-risk tools require approval before execution or before enablement.

## Agent Routing Integration

The Agent Routing Layer must consult the MCP / Skill Registry before selecting a tool. Tool selection must consider:

- user intent
- workspace/project context
- cloud provider and region
- required permission scope
- tool health
- tool version
- approval requirement
- audit requirements

## Health Checks

Cloud-360 must be able to check:

- MCP server availability
- tool schema compatibility
- authentication scope
- latency
- error rate
- last successful invocation
- dependency availability

## Guardrails

- No plaintext secrets in registry configuration.
- Expanding auth scope requires approval.
- Adding high-risk tools requires approval.
- Disabling critical tools requires impact analysis and rollback plan.
- Tool execution must write audit records.
- Agent responses must explain tool selection at a summary level while redacting sensitive payloads.

## Consequences

- Cloud-360 can safely grow its tool ecosystem.
- Agents gain a governed source of truth for tool selection.
- Operators can troubleshoot MCP / Skill health and permission issues.
- Security reviewers can audit tool scope and high-risk capabilities.
