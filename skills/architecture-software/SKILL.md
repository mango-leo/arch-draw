---
name: architecture-software
description: Draw architecture from implementation, repository source, or a working tree/diff. Use for software component hierarchy, service boundaries, calls, events, and storage access.
---

# Software architecture

## Analysis

- Start at build metadata and reachable entry points. Derive service/package ownership from code and configuration. Use stable component IDs across versions.
- Trace actual callers to callees, route registrations to handlers, producer and consumer bindings to the same event channel, and clients to configured stores. Draw runtime calls separately from static imports and label each connection with its actual mechanism.
- For a diff, read relevant unchanged entry points and neighbors too. Identify changed blocks/edges with a `changed` label or note. If asked to show removals, use a separate before/after graph or explicitly label a removed item as historical. Mark dynamic dispatch or configuration-dependent edges unresolved when they cannot be traced.

- An installed SDK or dependency in a lockfile does not establish a runtime connection. Look for an actual call or binding.

Read the sibling `../architecture-svg/SKILL.md` for the shared workflow and graph contract. When invoked directly, use this specialist as the primary view. Deliver through the shared renderer and review the resulting SVGs.
