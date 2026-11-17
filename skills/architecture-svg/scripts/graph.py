"""Validate the shared architecture graph and project it into diagram views."""

from dataclasses import dataclass
from pathlib import PurePosixPath
import re


ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
STATUS = {"confirmed", "inferred", "unresolved", "designed"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def string(value, where):
    require(isinstance(value, str) and value.strip() and not INVALID_XML.search(value), f"{where}: expected SVG-safe text")
    return value


def identifier(value, where):
    require(isinstance(value, str) and ID.fullmatch(value), f"{where}: invalid ID {value!r}")
    return value


def array(value, where):
    require(isinstance(value, list), f"{where}: expected a list")
    return value


def object_(value, where):
    require(isinstance(value, dict), f"{where}: expected an object")
    return value


def indexed(values, where):
    result = {}
    for item in array(values, where):
        entry = object_(item, where)
        item_id = identifier(entry.get("id"), where)
        require(item_id not in result, f"{where}: duplicate ID {item_id}")
        result[item_id] = entry
    return result


def evidence_text(item):
    locations = []
    for entry in item.get("evidence", []):
        location = entry["path"]
        if "line" in entry:
            location += f":{entry['line']}"
        if "locator" in entry:
            location += f" ({entry['locator']})"
        locations.append(location)
    return "\n".join(locations)


def validate_evidence(item, where):
    status = string(item.get("status"), f"{where} status")
    require(status in STATUS, f"{where}: invalid status {status}")
    entries = array(item.get("evidence", []), f"{where} evidence")
    require(entries or status not in {"confirmed", "designed"}, f"{where}: {status} items require evidence")
    for entry in entries:
        object_(entry, f"{where} evidence")
        path = string(entry.get("path"), f"{where} evidence path").replace("\\", "/")
        if path.startswith("input:"):
            string(path.removeprefix("input:"), f"{where} input name")
        else:
            require(":" not in path and not path.startswith("/") and ".." not in PurePosixPath(path).parts,
                    f"{where}: evidence path must be project-relative")
        if "line" in entry:
            require(type(entry["line"]) is int and entry["line"] > 0, f"{where}: line must be a positive integer")
        if "locator" in entry:
            string(entry["locator"], f"{where} evidence locator")


@dataclass(frozen=True)
class Graph:
    title: str
    scope: str
    notes: list
    blocks: dict
    ports: dict
    children: dict
    connections: dict

    def endpoint_label(self, endpoint):
        block = endpoint["block"]
        label = self.blocks[block]["label"]
        if "port" in endpoint:
            label += " · " + self.ports[block][endpoint["port"]]["label"]
        return label


def validate(payload):
    object_(payload, "graph")
    title = string(payload.get("title"), "title")
    scope = string(payload.get("scope", title), "scope")
    notes = [string(note, "note") for note in array(payload.get("notes", []), "notes")]
    blocks = indexed(payload.get("blocks"), "blocks")
    require(blocks, "graph must contain at least one block")
    require(len({item.casefold() for item in blocks}) == len(blocks), "block IDs must also be unique ignoring case")
    ports = {}
    children = {block_id: [] for block_id in [None, *blocks]}
    for block_id, block in blocks.items():
        where = f"block {block_id}"
        for field in ("label", "kind"):
            string(block.get(field), f"{where} {field}")
        if "boundary" in block:
            require(block["boundary"] in ("input", "output"), f"{where}: boundary must be input or output")
        validate_evidence(block, where)
        parent = block.get("parent")
        if parent is not None:
            identifier(parent, f"{where} parent")
            require(parent in blocks, f"{where}: unknown parent {parent}")
        children[parent].append(block_id)
        ports[block_id] = indexed(block.get("ports", []), f"{where} ports")
        for port_id, port in ports[block_id].items():
            string(port.get("label"), f"{where} port {port_id} label")
            direction = string(port.get("direction"), f"{where} port {port_id} direction")
            require(direction in {"in", "out", "inout", "unknown"}, f"{where}: invalid port direction {direction}")

    visited = set()
    for block_id in blocks:
        branch = set()
        cursor = block_id
        while cursor is not None and cursor not in visited:
            require(cursor not in branch, f"block {block_id}: parent cycle at {cursor}")
            branch.add(cursor)
            cursor = blocks[cursor].get("parent")
        visited.update(branch)
    for block_id, block in blocks.items():
        require("boundary" not in block or not children[block_id], f"block {block_id}: a boundary must be a leaf")
    for group in children.values():
        group.sort()

    connections = indexed(payload.get("connections"), "connections")
    for connection_id, connection in connections.items():
        where = f"connection {connection_id}"
        for field in ("label", "kind"):
            string(connection.get(field), f"{where} {field}")
        validate_evidence(connection, where)
        direction = string(connection.get("direction"), f"{where} direction")
        require(direction in {"forward", "both", "none"}, f"{where}: invalid connection direction {direction}")
        require(connection["status"] != "unresolved" or direction == "none", f"{where}: unresolved direction must be none")
        primary = connection.get("primary", False)
        require(type(primary) is bool and (not primary or direction == "forward"),
                f"{where}: primary must be a boolean and requires forward direction when true")
        for end in ("source", "target"):
            endpoint = object_(connection.get(end), f"{where} {end}")
            block = identifier(endpoint.get("block"), f"{where} {end} block")
            require(block in blocks, f"{where}: unknown {end} block {block}")
            if "port" in endpoint:
                port = identifier(endpoint["port"], f"{where} {end} port")
                require(port in ports[block], f"{where}: unknown {end} port {block}.{port}")
    return Graph(title, scope, notes, blocks, ports, children, connections)


@dataclass(frozen=True)
class View:
    title: str
    scope: str
    filename: str
    nodes: dict
    edges: list


def boundary_role(key, block):
    return block.get("boundary") if key[0] == "block" else {"scope-input": "input", "scope-output": "output"}.get(key[0])


def project(graph):
    order = {edge: f"W{index:02d}" for index, edge in enumerate(sorted(graph.connections), 1)}
    roots = graph.children[None]
    overview = roots[0] if len(roots) == 1 and graph.children[roots[0]] else None
    scopes = [overview] + sorted(block for block in graph.blocks if graph.children[block] and block != overview)
    for index, scope in enumerate(scopes):
        visible = set(graph.children[scope])
        nodes = {("block", block): graph.blocks[block] for block in sorted(visible)}

        def map_endpoint(endpoint):
            original = endpoint["block"]
            cursor = original
            while cursor is not None:
                if cursor in visible:
                    return ("block", cursor)
                cursor = graph.blocks[cursor].get("parent")
            if original == scope:
                port = graph.ports[original].get(endpoint.get("port"), {})
                role = {"in": "scope-input", "out": "scope-output"}.get(port.get("direction"), "boundary")
                return (role, original)
            return ("external", original)

        edges = []
        for edge_id in sorted(graph.connections):
            edge = graph.connections[edge_id]
            source = map_endpoint(edge["source"])
            target = map_endpoint(edge["target"])
            if source[0] != "block" and target[0] != "block":
                continue
            if source == target and any(edge[end]["block"] != source[1] for end in ("source", "target")):
                continue
            for endpoint in (source, target):
                if endpoint not in nodes:
                    nodes[endpoint] = graph.blocks[endpoint[1]]
            edges.append((order[edge_id], source, target, edge))
        if index == 0:
            yield View(graph.title, graph.scope, "overview.svg", nodes, edges)
        else:
            block = graph.blocks[scope]
            yield View(block["label"], f"{block['kind']} · {block['label']}", f"detail-{scope}.svg", nodes, edges)
