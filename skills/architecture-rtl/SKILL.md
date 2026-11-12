---
name: architecture-rtl
description: Draw RTL or UVM testbench architecture from Verilog or SystemVerilog. Use for modules, ports, interconnect, buses, UVM agents, sequencers and scoreboard connections.
---

# RTL architecture

## Analysis

- Resolve the top from an explicit request or project configuration, then from a unique root. Ask when real top candidates remain. Follow filelists and includes in scope, and distinguish testbench tops and libraries from the design.
- Use the instance path as identity. Read module port declarations and named or positional mappings. Trace net drivers and consumers, simple aliases and slices, and group buses only where endpoints and direction agree. Show known widths and distinguish control, data, clock and reset.
- Use supplied define/parameter settings to resolve simple generate branches and widths. Preserve conditional or unresolved instances, unknown widths, black boxes and undirected connections where evidence is incomplete. Keep the view at the block level.

- For UVM, separate the static `tb`/DUT and interface wiring from the class hierarchy. Trace factory creation, virtual sequencer handles, scoped `uvm_config_db` lookups and `connect_phase` analysis-port bindings. Label test-specific overrides or active/passive modes only when resolved.

Read the sibling `../architecture-svg/SKILL.md` for the shared workflow and graph contract. When invoked directly, use this specialist as the primary view. Deliver through the shared renderer and review the resulting SVGs.
