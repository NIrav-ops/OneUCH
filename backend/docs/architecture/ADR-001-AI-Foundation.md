# ADR-001 – AI Foundation

Status: Accepted

---

## Context

One UCH integrates multiple AI providers.

Direct SDK usage throughout the codebase would tightly couple business logic to vendor implementations.

---

## Decision

All AI execution must go through:

- AIRequest
- AIExecutionService
- AIProviderRouter
- AIResult

Provider SDKs remain isolated inside provider implementations.

---

## Consequences

Advantages

- Easy provider replacement
- Consistent response model
- Easier testing
- Better maintainability
- Enterprise-ready architecture

Tradeoffs

- Small abstraction layer
- Additional adapter code for providers

---

## Compatibility

Older workflow modules continue to use

workflow.services.ai.models

which now acts as a compatibility layer.