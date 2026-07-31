---
name: security-lens
description: Run a repository-grounded security review of a diff or codebase. Discover the project's assets, trust boundaries, authentication and authorization rules, sensitive data, persistence, external integrations, deployment controls, and documented exceptions before reviewing. Use as a security lens during code review, for security-sensitive changes, or for a repository security sweep. Report verified findings and explicitly identify checks that could not be completed.
---

# Security Lens

Review security against the repository's actual architecture and enforcement mechanisms. Do not substitute a generic checklist for project evidence.

## Modes

- **Diff mode:** Read every changed file and enough surrounding code to understand the affected trust boundaries. Run applicable checks below.
- **Sweep mode:** Map the repository's security surface, then run every applicable check across the codebase.

Return findings as `{check, severity, file, line, issue, fix}`, with severity `blocking`, `non-blocking`, or `nit`. Cite code that was read. Before reporting a missing control, run the cheapest search or test that could disprove the finding.

## Establish repository context

Before judging code:

1. Discover and read the active agent's repository instruction files and repo-local skills. Do not assume a particular filename or agent home.
2. Identify languages, frameworks, entry points, deployment configuration, and test commands.
3. Find security documentation, threat models, accepted risks, tracked exceptions, and tests that enforce security invariants.
4. Map trust boundaries: users, services, public endpoints, background jobs, queues, storage, third-party callbacks, AI systems, and administrative surfaces.
5. Identify sensitive assets from repository evidence: credentials, personal data, financial data, health data, customer content, cryptographic material, and privileged operations.
6. Record project-specific invariants and accepted exceptions. Never invent multitenancy, ownership, compliance, or authorization requirements the product does not claim.

If repository context cannot be established, label the affected checks unverified instead of presenting assumptions as findings.

## Checks

### 1. Authentication and authorization

Verify new and changed endpoints, commands, jobs, and administrative operations use the repository's established authentication and authorization mechanisms. Check policy strength, privilege boundaries, anonymous access, object-level access rules when the product has them, and fail-closed behavior.

### 2. Public and anonymous surfaces

For public endpoints, callbacks, shared links, uploads, and lookup routes, verify caller validation, unguessable or verified credentials, rate limits, request-size limits, replay protection where relevant, minimal responses, and constant-time secret comparison.

### 3. Sensitive data and logging

Trace sensitive fields through requests, storage, logs, audit trails, analytics, queues, caches, exports, and third parties. Verify the repository's redaction, encryption, retention, and minimization mechanisms. Treat URLs containing secrets as sensitive data.

### 4. Injection and unsafe interpretation

Review database queries, shell execution, templates, HTML rendering, file paths, deserialization, regular expressions, and dynamically evaluated content. Require parameterization, sanitization, escaping, allowlists, or structural APIs appropriate to the sink.

### 5. External requests and callbacks

Verify webhooks and callbacks authenticate callers before causing effects. For outbound requests, check destination validation, redirect behavior, DNS and private-network exposure, content-type and size validation, timeouts, and safe filenames.

### 6. Secrets and configuration

Check tracked files and diffs for credentials and unsafe defaults. Verify secrets use the project's secret store or ignored local configuration, examples contain placeholders, privileged configuration fails closed, and cross-origin or network policy changes preserve existing constraints.

### 7. State changes, audit, and integrity

Verify privileged writes follow established transaction, audit, validation, concurrency, and idempotency mechanisms. Look for bulk operations or alternate persistence paths that bypass interceptors, hooks, policies, or audit capture.

### 8. Cryptography and token handling

Use established, reviewed primitives. Check randomness, key management, nonce and IV rules, comparison behavior, token lifetime, rotation, storage, and algorithm parameters. Flag custom cryptography unless repository evidence justifies it.

### 9. Files, parsers, and untrusted content

Review uploads, archives, documents, images, and parser inputs for traversal, decompression bombs, content spoofing, resource exhaustion, unsafe metadata, and persistence before validation.

### 10. Async, queue, and workflow boundaries

Assume job arguments, queue messages, workflow histories, traces, and retry metadata may persist. Avoid secrets or large sensitive payloads when identifiers or protected storage references suffice. Verify replay safety, duplicate delivery handling, and authorization at execution time.

### 11. AI and automation boundaries

Treat model inputs and outputs as untrusted. Minimize data sent externally and validate outputs before using them in HTML, SQL, file paths, commands, URLs, permissions, or irreversible actions. Check retention and staging cleanup against repository guarantees.

### 12. Dependencies and deployment

Review dependency, container, CI, infrastructure, and deployment changes for provenance, privilege, secret exposure, unsafe permissions, public reachability, unpinned executable inputs, and weakened security checks.

## Reporting

In diff mode, list findings most severe first, then state which checks ran, which were not applicable, and which were required but unverified. In sweep mode, group findings by check and include the evidence or disproof command used.

End every response with:

- `Checks run`
- `Checks not applicable`
- `Required checks not completed`, including the missing repository context, tool, permission, or dependent skill for each omission

When invoked as a subagent, preserve this completion section in the final return so the parent agent can report missing coverage accurately.
