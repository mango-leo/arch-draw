---
name: architecture-dataflow
description: Draw data models and workflow architecture from SQL DDL, dbt manifest, or Airflow DAG source. Use for table relations, dataset lineage, transformations and task dependencies.
---

# Dataflow architecture

## Analysis

- Trace declared foreign keys for entity relationships, model/source references or input/output declarations for data lineage, and task dependency expressions for workflow ordering. Label each relation by its type and preserve qualification such as schema and dataset.
- Show the major sources, transformations, storage and consumers. Preserve known read/write direction, triggers and branch conditions. Use the manifest's dependency data where supplied and read DAG source statically.
- Preserve uncertainty for dynamically constructed SQL, dependencies or tasks and for missing upstream definitions. Never infer data movement solely from task order.

- A matching column name does not prove a join or foreign key. Use the declared relationship or the actual query.

Read the sibling `../architecture-svg/SKILL.md` for the shared workflow and graph contract. When invoked directly, use this specialist as the primary view. Deliver through the shared renderer and review the resulting SVGs.
