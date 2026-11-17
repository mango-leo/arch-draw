"""Lay out blocks, allocate ports and route nonintersecting orthogonal wires."""

from dataclasses import dataclass
from itertools import combinations
import unicodedata

from graph import boundary_role


WIDTH = 320
MARGIN = 32
LEADING = 23
PORT_PITCH = 23
CLEARANCE = 4
HEAD_LENGTH = 9
HEAD_HALF = 4


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    right: int
    bottom: int

    def intersects(self, other, pad=0):
        return (self.left <= other.right + pad and self.right + pad >= other.left
                and self.top <= other.bottom + pad and self.bottom + pad >= other.top)

    def contains(self, other):
        return (self.left <= other.left <= other.right <= self.right
                and self.top <= other.top <= other.bottom <= self.bottom)


@dataclass(frozen=True)
class Text:
    x: int
    baseline: int
    value: str
    size: int
    css: str = ""

    @property
    def box(self):
        return Box(self.x, self.baseline - self.size, self.x + text_width(self.value, self.size), self.baseline + 4)


def text_width(value, size):
    cells = sum(1.24 if unicodedata.east_asian_width(char) in {"W", "F"} else 0.83 for char in value)
    return int(cells * size + 1)


def wrap(value, max_width, size):
    line = ""
    for word in value.split():
        joined = f"{line} {word}" if line else word
        if text_width(joined, size) <= max_width:
            line = joined
            continue
        if line:
            yield line
        line = ""
        for char in word:
            if line and text_width(line + char, size) > max_width:
                yield line
                line = ""
            line += char
    if line:
        yield line


def short(value, max_width, size):
    if text_width(value, size) <= max_width:
        return value
    result = ""
    for char in value:
        if text_width(result + char + "…", size) > max_width:
            break
        result += char
    return result + "…"


@dataclass(frozen=True)
class Node:
    key: tuple
    box: Box
    text: tuple
    anchors: dict


@dataclass(frozen=True)
class Route:
    points: tuple
    heads: tuple

    @property
    def segments(self):
        return tuple(segment(a, b) for a, b in zip(self.points, self.points[1:]))

    @property
    def shapes(self):
        return self.segments + tuple(bounds(points) for points in self.heads)


def bounds(points):
    return Box(min(x for x, _ in points), min(y for _, y in points),
               max(x for x, _ in points), max(y for _, y in points))


def segment(a, b):
    if a == b or (a[0] != b[0] and a[1] != b[1]):
        raise ValueError("wire segment must be nonempty and orthogonal")
    return bounds((a, b))


def simplify(points):
    result = []
    for point in points:
        if result and point == result[-1]:
            continue
        if len(result) > 1:
            for axis in (0, 1):
                other = 1 - axis
                a, b = result[-2:]
                if a[other] == b[other] == point[other] and (b[axis] - a[axis]) * (point[axis] - b[axis]) > 0:
                    result.pop()
                    break
        result.append(point)
    return tuple(result)


def arrow(point, back):
    x, y = point
    return (point, (x + back * HEAD_LENGTH, y - HEAD_HALF), (x + back * HEAD_LENGTH, y + HEAD_HALF))


def route_of(points, direction):
    heads = []
    if direction in {"forward", "both"}:
        heads.append(arrow(points[-1], -1))
    if direction == "both":
        heads.append(arrow(points[0], 1))
    return Route(points, tuple(heads))


def route_problem(route, start, end, nodes, prior):
    points = route.points
    if len(points) < 2 or points[1][0] <= points[0][0] or points[-2][0] >= points[-1][0]:
        return "wire approaches a port from inside a block"
    pieces = route.segments
    for i, piece in enumerate(pieces):
        if any(piece.intersects(other) for other in pieces[i + 2:]):
            return "wire crosses itself"
        for key, node in nodes.items():
            if (i == 0 and key == start) or (i == len(pieces) - 1 and key == end):
                continue
            if piece.intersects(node.box, CLEARANCE):
                return "wire intersects a block"
    for points in route.heads:
        key = start if points[0] == route.points[0] else end
        head = bounds(points)
        if any(head.intersects(node.box, CLEARANCE) for other, node in nodes.items() if other != key):
            return "arrow intersects a block"
    if any(shape.intersects(other, CLEARANCE) for shape in route.shapes for other in prior):
        return "wires intersect"
    return None


def rank_nodes(view):
    outgoing = {key: set() for key in view.nodes}
    incoming = {key: set() for key in view.nodes}
    inputs = {key for key, block in view.nodes.items() if boundary_role(key, block) == "input"}
    outputs = {key for key, block in view.nodes.items() if boundary_role(key, block) == "output"}
    main_nodes = {key for _, source, target, edge in view.edges if edge.get("primary") for key in (source, target)}
    for _, source, target, edge in view.edges:
        if (source != target and edge["direction"] == "forward"
                and source not in outputs and target not in inputs
                and (target not in main_nodes or edge.get("primary"))):
            outgoing[source].add(target)
            incoming[target].add(source)
    ranks = {key: int(bool(inputs) and key not in inputs) for key in view.nodes}
    remaining = set(view.nodes)
    while remaining:
        ready = sorted(key for key in remaining if not incoming[key] & remaining)
        if not ready:
            ready = [min(remaining)]
        for key in ready:
            remaining.remove(key)
            for target in outgoing[key] & remaining:
                ranks[target] = max(ranks[target], ranks[key] + 1)
    if outputs:
        last = max((rank for key, rank in ranks.items() if key not in outputs), default=-1) + 1
        ranks.update(dict.fromkeys(outputs, last))
    return ranks


def position(graph, view, top, column_gap, row_gap):
    ranks = rank_nodes(view)
    columns = {}
    ordered_edges = sorted(view.edges, key=lambda item: not item[3].get("primary", False))
    main_nodes = {key for _, source, target, edge in ordered_edges if edge.get("primary") for key in (source, target)}
    port_rows = {key: {"source": [], "target": []} for key in view.nodes}
    for wire, source, target, edge in ordered_edges:
        for key, side in ((source, "source"), (target, "target")):
            endpoint = edge[side]
            port = graph.ports[endpoint["block"]].get(endpoint.get("port"))
            primary = edge.get("primary", False)
            label = edge["label"] if primary or not port else port["label"]
            port_rows[key][side].append((wire, f"{wire} · {label}", primary))

    sizes = {}
    for key, block in view.nodes.items():
        columns.setdefault(ranks[key], []).append(key)
        label = list(wrap(block["label"], WIDTH - 28, 16))
        kind = block["kind"] + " · " + block["status"]
        boundary = boundary_role(key, block)
        if boundary:
            kind = f"{boundary.title()} boundary · " + kind
        elif key[0] != "block":
            kind = ("Scope port · " if key[0] == "boundary" else "External · ") + kind
        elif graph.children[key[1]]:
            kind += " · detail"
        subtitle = list(wrap(kind, WIDTH - 28, 12))
        if boundary == "output":
            subtitle.extend(wrap(f"View · {view.scope}", WIDTH - 28, 12))
        port_top = 17 + LEADING * (len(label) + len(subtitle))
        rows = max(len(values) for values in port_rows[key].values())
        sizes[key] = label, subtitle, port_top, port_top + rows * PORT_PITCH + 10

    row_heights = {}
    rows_by_node = {}
    primary_port_tops = {}
    for keys in columns.values():
        keys.sort(key=lambda key: (key not in main_nodes, key))
        first_row = int(bool(main_nodes) and keys[0] not in main_nodes)
        for row, key in enumerate(keys, first_row):
            rows_by_node[key] = row
            if key in main_nodes:
                primary_port_tops[row] = max(primary_port_tops.get(row, 0), sizes[key][2])
    for key, row in rows_by_node.items():
        if key in main_nodes:
            label, subtitle, port_top, height = sizes[key]
            aligned_top = primary_port_tops[row]
            sizes[key] = label, subtitle, aligned_top, height + aligned_top - port_top
        row_heights[row] = max(row_heights.get(row, 0), sizes[key][3])
    row_tops = []
    cursor = top
    for row in sorted(row_heights):
        row_tops.append(cursor)
        cursor += row_heights[row] + row_gap

    nodes = {}
    for column, keys in sorted(columns.items()):
        for key in keys:
            x = MARGIN + 76 + column * (WIDTH + column_gap)
            y = row_tops[rows_by_node[key]]
            label, subtitle, port_top, height = sizes[key]
            text = []
            baseline = y + 25
            for values, size, css in ((label, 16, "node-title"), (subtitle, 12, "muted")):
                for value in values:
                    text.append(Text(x + 14, baseline, value, size, css))
                    baseline += LEADING
            anchors = {}
            for side, dx in (("target", 0), ("source", WIDTH)):
                for index, (wire, value, primary) in enumerate(port_rows[key][side]):
                    port_y = y + port_top + 12 + index * PORT_PITCH
                    anchors[wire, side] = (x + dx, port_y)
                    text_x = x + (14 if side == "target" else WIDTH // 2 + 5)
                    text.append(Text(text_x, port_y + 4, short(value, WIDTH // 2 - 20, 12), 12,
                                     "port primary" if primary else "port"))
            nodes[key] = Node(key, Box(x, y, x + WIDTH, y + height), tuple(text), anchors)
    lanes = [top - 20, top - 34]
    for index, y in enumerate(row_tops):
        end = y + row_heights[index]
        lanes.extend((end + 15, end + 30))
    return nodes, lanes


def find_route(a, b, direction, nodes, start, end, prior, lanes, column_gap):
    ax, ay = a
    bx, by = b
    if ay == by and ax < bx:
        direct = route_of((a, b), direction)
        if not route_problem(direct, start, end, nodes, prior):
            return direct
    offsets = (17, 32, min(60, column_gap // 2 + 7))
    if ay != by:
        for x in (ax + offsets[0], (ax + bx) // 2, bx - offsets[0]):
            if ax + HEAD_LENGTH < x < bx - HEAD_LENGTH:
                route = route_of((a, (x, ay), (x, by), b), direction)
                if not route_problem(route, start, end, nodes, prior):
                    return route
    tracks = sorted(set(lanes), key=lambda y: (abs(y - ay) + abs(y - by), y))[:24]
    for y in tracks:
        for left in offsets:
            for right in offsets:
                sx, tx = ax + left, bx - right
                points = simplify((a, (sx, ay), (sx, y), (tx, y), (tx, by), b))
                route = route_of(points, direction)
                if not route_problem(route, start, end, nodes, prior):
                    return route
    return None


def place(graph, view, top):
    best = None
    best_score = (-1, -1)
    ordered_edges = sorted(view.edges, key=lambda item: not item[3].get("primary", False))
    for column_gap, row_gap in ((104, 56), (180, 86)):
        nodes, lanes = position(graph, view, top, column_gap, row_gap)
        wires = {}
        occupied = []
        for wire, source, target, edge in ordered_edges:
            a = nodes[source].anchors[wire, "source"]
            b = nodes[target].anchors[wire, "target"]
            route = find_route(a, b, edge["direction"], nodes, source, target, occupied, lanes, column_gap)
            if route:
                wires[wire] = route
                occupied.extend(route.shapes)
        score = (sum(wire in wires for wire, _, _, edge in ordered_edges if edge.get("primary")), len(wires))
        if score > best_score:
            best = nodes, wires
            best_score = score
        if len(wires) == len(view.edges):
            break
    return best


def verify(view, nodes, wires, canvas, outside):
    for a, b in combinations(nodes.values(), 2):
        if a.box.intersects(b.box):
            raise ValueError(f"blocks overlap: {a.key[1]} and {b.key[1]}")
    for key, node in nodes.items():
        if not canvas.contains(node.box) or any(not node.box.contains(text.box) for text in node.text):
            raise ValueError(f"block or port label clipped: {key[1]}")
        if any(a.box.intersects(b.box) for a, b in combinations(node.text, 2)):
            raise ValueError(f"block labels overlap: {key[1]}")
    if any(not canvas.contains(text.box) for text in outside):
        raise ValueError("heading or connection table clipped")
    if any(a.box.intersects(b.box) for a, b in zip(outside, outside[1:])):
        raise ValueError("heading or connection table labels overlap")
    if any(node.box.intersects(text.box) for node in nodes.values() for text in outside):
        raise ValueError("heading or connection table intersects a block")
    occupied = []
    for wire, source, target, _ in view.edges:
        route = wires.get(wire)
        if not route:
            continue
        if route.points[0] != nodes[source].anchors[wire, "source"] or route.points[-1] != nodes[target].anchors[wire, "target"]:
            raise ValueError(f"{wire}: detached endpoint")
        problem = route_problem(route, source, target, nodes, occupied)
        if problem:
            raise ValueError(f"{wire}: {problem}")
        if any(not canvas.contains(shape) or any(shape.intersects(text.box) for text in outside) for shape in route.shapes):
            raise ValueError(f"{wire}: clipped or intersects a label")
        occupied.extend(route.shapes)
