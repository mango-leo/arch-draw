---
name: architecture-infra
description: Draw deployment and infrastructure architecture from Docker Compose, Kubernetes or Terraform configuration. Use for workloads, service exposure, networking, environments, and storage.
---

# Infra architecture

## Analysis

- Identify the provided environment, selected overlay or variable context. Trace explicit workload selectors, service targets, ingress/backend references, port mappings, networks, attached volumes and Terraform references.
- Group by declared environment, cluster, namespace or network boundary. Use declared image, labels or build context to link to implementation when available. Distinguish deployment dependency from an observed or configured traffic path.
- Represent unresolved module outputs, dynamic values, missing overlays and externally managed resources explicitly. Describe configuration as declared, and require observed evidence before claiming live state.

- A declared dependency such as Compose `depends_on` establishes startup order. Require a configured endpoint or route to show network traffic.

Read the sibling `../architecture-svg/SKILL.md` for the shared workflow and graph contract. When invoked directly, use this specialist as the primary view. Deliver through the shared renderer and review the resulting SVGs.
