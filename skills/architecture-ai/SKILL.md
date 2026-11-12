---
name: architecture-ai
description: Draw AI/ML and agent architecture from model configuration, training or inference source, RAG or tool workflows. Use for model blocks, retrieval, orchestration, and data/control flow.
---

# AI architecture

## Analysis

- Identify the task: model structure, training, inference, RAG or agent execution. Start with constructors/configuration and trace the actual forward path, training stages, tool registration and dispatch, retrieval and context assembly relevant to that view.
- Group model components and orchestration stages. Label data, control and feedback separately. Show branch conditions or shape information only when supported by source or configuration. Draw external model, tool or index boundaries explicitly.
- Distinguish declarations from invoked steps. Mark dynamically selected tools, model layers, prompts, or tensor dimensions unresolved when missing evidence prevents tracing them.

- A tool definition or model name alone does not establish a call. Trace invocation or routing before adding a connection.

Read the sibling `../architecture-svg/SKILL.md` for the shared workflow and graph contract. When invoked directly, use this specialist as the primary view. Deliver through the shared renderer and review the resulting SVGs.
