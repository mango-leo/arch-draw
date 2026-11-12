"""Render and verify architecture diagrams using the Python standard library."""

import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from graph import evidence_text, project, validate
from layout import Box, MARGIN, Text, place, verify, wrap


CSS = """
text { font-family: 'Cascadia Mono', Consolas, monospace; fill: #142638; }
.title { font-weight: 700; }
.node-title, .table-heading { font-weight: 700; }
.muted { fill: #475d71; }
.port { fill: #284d69; }
.fallback { fill: #80501d; }
.canvas { fill: #f3f7fa; }
.block { fill: #fff; stroke: #31556d; stroke-width: 1.5; }
.block.external, .block.boundary { fill: #e9f1f6; }
.block.inferred, .block.unresolved { stroke-dasharray: 5 4; }
.block.designed { stroke: #745b96; }
.wire { fill: none; stroke: #305b74; stroke-width: 1.7; stroke-linejoin: round; }
.wire.inferred { stroke-dasharray: 5 4; }
.wire.unresolved { stroke: #80501d; stroke-dasharray: 2 4; }
.wire.designed { stroke: #745b96; stroke-dasharray: 8 3; }
.arrow { fill: #305b74; }
.arrow.designed { fill: #745b96; }
.anchor { fill: #305b74; }
"""


def element(parent, tag, attributes=None, value=None):
    node = ET.SubElement(parent, tag, attributes or {})
    if value is not None:
        node.text = value
    return node


def text_rows(value, x, y, size, css, max_width, leading):
    rows = [Text(x, y + index * leading, line, size, css)
            for index, line in enumerate(wrap(value, max_width, size))]
    return rows, y + len(rows) * leading


def text_element(parent, text):
    return element(parent, "text", {
        "x": str(text.x), "y": str(text.baseline), "font-size": str(text.size), "class": text.css,
    }, text.value)


def rect(parent, box, css, radius=0):
    return element(parent, "rect", {
        "x": str(box.left), "y": str(box.top), "width": str(box.right - box.left),
        "height": str(box.bottom - box.top), "rx": str(radius), "class": css,
    })


def points_attribute(points):
    return " ".join(f"{x},{y}" for x, y in points)


def edge_description(graph, wire, edge):
    left = graph.endpoint_label(edge["source"])
    right = graph.endpoint_label(edge["target"])
    relation = {"forward": "→", "both": "↔", "none": "—"}[edge["direction"]]
    return f"{wire}  {left} {relation} {right} | {edge['kind']} · {edge['label']} · {edge['status']}"


def render(graph, view):
    heading = "Architecture overview" if view.filename == "overview.svg" else "Block detail"
    outside = [Text(MARGIN, 44, heading, 14, "muted")]
    rows, baseline = text_rows(view.title, MARGIN, 85, 27, "title", 760, 35)
    outside.extend(rows)
    for note in graph.notes:
        rows, baseline = text_rows(note, MARGIN, baseline + 5, 14, "muted", 760, 21)
        outside.extend(rows)
    nodes, wires = place(graph, view, baseline + 66)
    shapes = [shape for route in wires.values() for shape in route.shapes]
    max_right = max([node.box.right for node in nodes.values()] + [shape.right for shape in shapes])
    max_bottom = max([node.box.bottom for node in nodes.values()] + [shape.bottom for shape in shapes])
    width = max(840, max_right + MARGIN + 1)
    baseline = max_bottom + 46
    if view.edges:
        outside.append(Text(MARGIN, baseline, "Connections", 17, "table-heading"))
        baseline += 28
        rows, baseline = text_rows(
            "Solid: confirmed · dashed: inferred or designed · dotted: unresolved. Matching IDs join ends when no line is drawn.",
            MARGIN, baseline, 12, "muted", min(width - 2 * MARGIN, 1140), 19,
        )
        outside.extend(rows)
        baseline += 8
    table = []
    for wire, _, _, edge in view.edges:
        desc = edge_description(graph, wire, edge)
        if wire not in wires:
            desc += " | paired ports"
        rows, baseline = text_rows(desc, MARGIN, baseline, 13, "fallback" if wire not in wires else "",
                                   min(width - 2 * MARGIN, 1320), 20)
        table.append((wire, rows, edge))
        outside.extend(rows)
        baseline += 5
    canvas = Box(0, 0, width, baseline + MARGIN)
    verify(view, nodes, wires, canvas, outside)

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg", "width": str(width), "height": str(canvas.bottom),
        "viewBox": f"0 0 {width} {canvas.bottom}", "role": "img", "aria-labelledby": "diagram-title",
    })
    element(svg, "title", {"id": "diagram-title"}, view.title)
    element(svg, "style", value=CSS.strip())
    rect(svg, canvas, "canvas")
    table_count = sum(len(rows) for _, rows, _ in table)
    for text in outside[:len(outside) - table_count]:
        text_element(svg, text)

    wire_layer = element(svg, "g", {"id": "wires"})
    for wire, _, _, edge in view.edges:
        if wire not in wires:
            continue
        route = wires[wire]
        group = element(wire_layer, "g", {"data-wire": wire, "data-direction": edge["direction"]})
        element(group, "title", value=edge_description(graph, wire, edge) + "\n" + evidence_text(edge))
        element(group, "polyline", {"points": points_attribute(route.points), "class": f"wire {edge['status']}"})
        for head in route.heads:
            element(group, "polygon", {"points": points_attribute(head), "class": f"arrow {edge['status']}"})

    block_layer = element(svg, "g", {"id": "blocks"})
    for key, node in nodes.items():
        block = view.nodes[key]
        group = element(block_layer, "g", {"data-block": key[1], "data-role": key[0]})
        ports = [f"{port['label']} ({port['direction']})" for port in graph.ports[key[1]].values()]
        tooltip = "\n".join(filter(None, (block["label"], evidence_text(block), *ports)))
        element(group, "title", value=tooltip)
        rect(group, node.box, f"block {key[0]} {block['status']}", radius=9)
        for text in node.text:
            text_element(group, text)
        for (wire, side), (x, y) in node.anchors.items():
            if wire in wires:
                element(group, "circle", {"cx": str(x), "cy": str(y), "r": "2", "class": "anchor"})
        if key[0] == "block" and graph.children[key[1]]:
            # The link occupies the already validated title area.
            first = group.find("text")
            group.remove(first)
            element(group, "a", {"href": f"detail-{key[1]}.svg"}).append(first)

    table_layer = element(svg, "g", {"id": "connections"})
    for wire, rows, edge in table:
        group = element(table_layer, "g", {
            "data-connection": edge["id"], "data-wire": wire,
            "data-style": "line" if wire in wires else "paired-ports",
        })
        element(group, "title", value=edge_description(graph, wire, edge) + "\n" + evidence_text(edge))
        for text in rows:
            text_element(group, text)

    ET.indent(svg)
    result = ET.tostring(svg, encoding="utf-8", xml_declaration=True)
    ET.fromstring(result)
    return result, len(view.edges) - len(wires)


def output_directory(requested):
    if requested is not None:
        requested.mkdir()
        return requested
    sequence = 1
    while True:
        path = Path("architecture" if sequence == 1 else f"architecture-{sequence}")
        try:
            path.mkdir()
            return path
        except FileExistsError:
            sequence += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph", type=Path)
    parser.add_argument("--out", type=Path, help="new output directory, default: architecture[/numbered]")
    args = parser.parse_args()
    try:
        graph = validate(json.loads(args.graph.read_text(encoding="utf-8-sig")))
        diagrams = [(view.filename, *render(graph, view)) for view in project(graph)]
        output = output_directory(args.out)
        for name, svg, paired in diagrams:
            path = output / name
            path.write_bytes(svg)
            print(f"Verified {path} ({paired} paired connection(s))")
    except (OSError, ValueError) as error:
        print(f"Cannot render architecture: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
