# AI Service Layer

## Purpose

The AI Service Layer provides a provider-agnostic abstraction for all AI execution within One UCH.

Instead of calling OpenAI, Azure OpenAI, Gemini, Claude, Ollama, or any future provider directly, the rest of the application communicates through a single interface.

---

## Responsibilities

- Validate AI requests
- Route requests to the correct provider
- Execute prompts
- Normalize responses
- Isolate provider-specific SDKs
- Preserve backward compatibility

---

## Public API

The following classes are considered stable.

- AIRequest
- AIResult
- AIExecutionService
- AIProviderRouter

---

## Provider Contract

Every provider must:

- inherit BaseAIProvider
- implement execute()
- return AIResult
- never return raw dictionaries

---

## Current Providers

- Mock Provider

---

## Planned Providers

- OpenAI
- Azure OpenAI
- Anthropic Claude
- Google Gemini
- Ollama
- MCP

---

## Design Principles

- Provider Agnostic
- Typed Contracts
- Enterprise First
- Backward Compatible
- Test Driven