---
name: architecture-board
description: Draw board electronics architecture from a KiCad schematic or exported netlist. Use for sheet hierarchy, component groups, power rails, connectors, and major signal nets.
---

# Board architecture

## Analysis

- Prefer an exported netlist for exact pin membership when available. In a schematic, use sheet instances, scoped labels, explicit junctions and known pins; a crossing without a junction is not a connection. Preserve component reference designators and distinguish repeated sheet instances.
- Group components by schematic sheet or explicit functional role. Select major ICs, connectors, power domains, buses and meaningful passives. Use named nets or connector pin mappings to show off-board boundaries.
- Use a direction only where the evidence establishes it. Leave passive, ambiguous, or unresolved nets undirected. Mark any missing sheet or netlist that prevents resolving an endpoint.

- Matching local net names across sheets do not establish connectivity. Resolve scope, sheet pins and global labels before merging nets.

Read the sibling `../architecture-svg/SKILL.md` for the shared workflow and graph contract. When invoked directly, use this specialist as the primary view. Deliver through the shared renderer and review the resulting SVGs.
