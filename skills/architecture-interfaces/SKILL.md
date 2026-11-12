---
name: architecture-interfaces
description: Draw integration architecture from OpenAPI, AsyncAPI, or Protobuf service definitions. Use for API contracts, RPC, events, producers, consumers, and message channels.
---

# Interfaces architecture

## Analysis

- Read service/server definitions, operations, channels, role and direction fields. Use method plus path for HTTP, service plus method for RPC, and channel plus operation for events. Resolve local references within the supplied scope.
- Distinguish contract operations from concrete clients. A documented operation establishes an interface; label an unnamed or unverified caller as unresolved. Keep event broker boundaries and request/reply semantics when specified.
- For mixed inputs, join contracts to implemented handlers and configured clients only when operation identity and context match. Preserve contradictory contracts and implementation observations as scoped notes.

- For AsyncAPI, interpret send and receive from the application described by the contract. An operation alone does not identify the remote peer.

Read the sibling `../architecture-svg/SKILL.md` for the shared workflow and graph contract. When invoked directly, use this specialist as the primary view. Deliver through the shared renderer and review the resulting SVGs.
