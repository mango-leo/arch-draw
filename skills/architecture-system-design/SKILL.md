---
name: architecture-system-design
description: Draw architecture from a design document, requirements, an ADR or notes that specify components and relationships. Use for design and system context diagrams, or to show proposals alongside implemented architecture.
---

# System-design architecture

## Analysis

- Extract explicitly named actors, systems, boundaries, component responsibilities and relationships. Cite the page, section, heading or line as evidence; work from the available document text or request an excerpt if text is unavailable.
- Mark document-derived objects and relationships `designed`. Note the document version or status when available. Keep proposed, decided and implemented views identifiable, especially when code and documentation disagree.
- Preserve ambiguous direction, unknown connections and alternative proposals. Use the user's chosen variant or ask if conflicting alternatives would change the picture.

- A requirement that two systems integrate establishes design intent. Keep direction, protocol and ownership open unless the document specifies them.

Read the sibling `../architecture-svg/SKILL.md` for the shared workflow and graph contract. When invoked directly, use this specialist as the primary view. Deliver through the shared renderer and review the resulting SVGs.
