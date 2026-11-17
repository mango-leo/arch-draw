# Shared architecture graph

Create UTF-8 JSON with `title`, `blocks`, and `connections`. Use `scope` to describe the subject and layer for the reader. Existing graphs without `scope` use the title at the output boundary. An optional `notes` array records variant and material unknowns. Each block represents a recognizable boundary or role and carries the original identifier in its label or evidence.

```json
{
  "title": "Checkout service",
  "scope": "Backend · Checkout API",
  "notes": ["Current workspace, local profile"],
  "blocks": [
    {"id":"api","label":"Checkout API","kind":"service","status":"confirmed","evidence":[{"path":"src/routes.py","line":12}],"ports":[{"id":"db","label":"database client","direction":"out"}]},
    {"id":"store","label":"Order store","kind":"database","status":"confirmed","evidence":[{"path":"src/store.py","line":6}]},
    {"id":"response","label":"Order receipt","kind":"HTTP 201 response","boundary":"output","status":"confirmed","evidence":[{"path":"src/routes.py","line":20}]}
  ],
  "connections": [
    {"id":"write","source":{"block":"api","port":"db"},"target":{"block":"store"},"direction":"forward","kind":"SQL","label":"INSERT orders","status":"confirmed","evidence":[{"path":"src/routes.py","line":19}]},
    {"id":"receipt","source":{"block":"api"},"target":{"block":"response"},"direction":"forward","kind":"HTTP","label":"Order receipt","primary":true,"status":"confirmed","evidence":[{"path":"src/routes.py","line":20}]}
  ]
}
```

- IDs are ASCII letters, digits, dots, underscores or hyphens, beginning with a letter or digit, at most 80 characters. Block IDs and connection IDs are unique within their own lists. Port IDs are unique within a block. `parent`, if present, refers to another block. Give each RTL or schematic instance its own block ID even when its type repeats. Use `kind` for the role (e.g. `rtl module`, `deployment`, `RPC`, `net`, `task dependency`).
- `status` is `confirmed`, `inferred`, `unresolved`, or `designed`. Confirmed and designed items require evidence. `evidence` entries use a project-relative `path`, optionally a positive `line` and/or a `locator` such as a schematic reference, JSON pointer, or section. Keep paths relative and use `input:<name>` for inline material. State uncertainty about a block or connection through `status`, about a direction through `direction: "none"`, and about a wider limitation through `notes`.
- An endpoint always names a `block`; `port` names a declared port of that block. Port direction is `in`, `out`, `inout`, or `unknown`. Connection `direction` is `forward` (source to target), `both`, or `none`. An unresolved connection must use `none`. Record separate request and response edges only when both are distinct and useful, and each has evidence.
- Set `boundary` to `input` or `output` on a leaf block for the directional interface at the system or detail scope. Use `label` for the result, such as `Rendered order list`, `Order receipt` or `report.csv`. Use `kind` for the surface or destination, such as `Browser DOM`, `HTTP 201 response` or `Local filesystem`. The renderer places inputs on the left and outputs on the right. Each output includes the view scope. A detail diagram uses its own component as the scope. Declared directional ports on the scope block also render as separate boundaries. A bidirectional interface can keep its ordinary block and `both` connection.
- Set `primary: true` on forward connections that carry the main payload through the system. The renderer uses them to lay out the main path, routes them first and emphasizes their labels and lines. Leave `primary` unset on supporting paths. Evidence and direction rules still apply to every connection.
- Use parent relations for containment. For a bus, bundle signals into one connection when endpoints, direction and semantics agree. Include width only when known. Give each connection a short label and use notes or tooltips for longer context.
- A sole root with children is opened in the overview. Otherwise the overview shows the top-level blocks. A group gets its own detail file when collapsed in an overview or detail; it shows the group's immediate children and external endpoints for their connections. Connections crossing a collapsed group boundary are projected onto the group. Their full endpoints remain in the connection table. Use depth and grouping to keep overviews readable.
