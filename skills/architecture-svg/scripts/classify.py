"""Find likely architecture domains from readable project files without running them."""

import argparse
import json
import os
from pathlib import Path
import re
import sys


REGISTRY = Path(__file__).resolve().parents[1] / "registry.json"
MAX_SAMPLE = 128 * 1024
SKIP = {
    ".agents", ".claude", ".git", ".hg", ".svn", ".venv", "__pycache__",
    "node_modules", "vendor", "dist", "build", "target", "venv",
}
SOURCE = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".kt", ".php",
    ".py", ".rb", ".rs", ".swift", ".ts", ".tsx", ".zig",
}
STRUCTURED = {".yaml", ".yml", ".json"}


def matches(pattern, content):
    return re.search(pattern, content, re.IGNORECASE | re.MULTILINE) is not None


def key(name, content):
    return matches(r'^' + re.escape(name) + r'\s*:|"' + re.escape(name) + r'"\s*:', content)


def classify(path, content):
    suffix, name = path.suffix.lower(), path.name.lower()
    hits = []
    fields = None
    if suffix == ".json":
        try:
            document = json.loads(content)
        except ValueError:
            pass  # The sample may end before a large JSON file does.
        else:
            fields = document if isinstance(document, dict) else {}

    def has(field):
        return field in fields if fields is not None else key(field, content)

    def add(domain, score, marker):
        hits.append({"domain": domain, "strength": score, "marker": marker})

    if suffix in {".sv", ".svh"} and matches(r"^\s*(?:virtual\s+)?class\s+\w+", content) and matches(
        r"\bextends\s+(?:uvm_pkg::)?(?:uvm_|cip_base_|dv_base_)\w+|^\s*`uvm_(?:component|object)_(?:param_)?utils\w*\s*\(",
        content,
    ):
        add("rtl", 100, "SystemVerilog UVM testbench class")
    elif suffix in {".v", ".sv", ".vh", ".svh"} and matches(
        r"^\s*(?:(?:\(\*.*?\*\)|extern)\s*)?(?:module|interface|package)\s+\w+|^\s*`(?:include|define)\b",
        content,
    ):
        add("rtl", 100, "Verilog/SystemVerilog design declaration or directive")
    if suffix in {".f", ".flist"} and matches(r"\.s?v(?:\s|$)", content):
        add("rtl", 90, "RTL source file list")
    if suffix in {".kicad_sch", ".net", ".xml"} and matches(
        r"^\s*(?:\(kicad_sch\b|\(export\s|(?:<\?xml[^>]*\?>\s*)?<export\s)", content
    ):
        if suffix == ".kicad_sch" or matches(r"\bcomponents\b", content):
            add("board", 100, "KiCad schematic or netlist structure")
    if suffix == ".tf" and matches(r'^\s*(?:resource|data|module|provider)\s+"', content):
        add("infra", 100, "Terraform declaration")
    if name == "dockerfile" and matches(r"^\s*FROM\s+\S+", content):
        add("infra", 85, "Docker build and runtime definition")
    if suffix in STRUCTURED:
        if has("apiVersion") and has("kind"):
            add("infra", 100, "Kubernetes apiVersion and kind")
        if has("services") and (
            "compose" in name or matches(r"^\s+(?:image|build|depends_on|networks|ports)\s*:", content)
        ):
            add("infra", 100, "Compose services and runtime configuration")
        if has("openapi") or has("swagger"):
            add("interfaces", 100, "OpenAPI version declaration")
        if has("asyncapi"):
            add("interfaces", 100, "AsyncAPI version declaration")
        metadata = fields.get("metadata", {}) if fields is not None else {}
        if name == "manifest.json" and (
            (isinstance(metadata, dict) and "dbt_schema_version" in metadata) or has("dbt_schema_version")
        ):
            add("dataflow", 100, "dbt manifest metadata")
        if has("model_type") and any(
            has(field) for field in ("architectures", "hidden_size", "num_hidden_layers")
        ):
            add("ai", 100, "Model configuration and architecture parameters")
    if suffix == ".proto" and matches(r"\bservice\s+\w+\s*\{", content):
        add("interfaces", 100, "Protobuf service declaration")
    if suffix == ".sql" and matches(r"\bCREATE\s+(?:TABLE|VIEW)\b|\b(?:ref|source)\s*\(", content):
        add("dataflow", 95, "SQL schema or dataset lineage")
    if suffix == ".py":
        if matches(r"\b(?:from|import)\s+airflow\b", content) and matches(r"\b(?:DAG|dag)\s*\(", content):
            add("dataflow", 100, "Airflow import and DAG declaration")
        if matches(r"\b(?:from|import)\s+(?:torch|tensorflow|transformers|langgraph|langchain|agents)\b", content) and matches(
            r"\b(?:forward|predict|generate|fit|retriever|StateGraph|Agent|Runner|Sequential|from_pretrained)\s*\(", content
        ):
            add("ai", 100, "ML/agent library and model or workflow entry point")
    if suffix in SOURCE and content.strip():
        add("software", 60 if hits else 80, "Implementation source")
    if suffix in {".diff", ".patch"} and matches(r"^diff --git |^@@", content):
        add("software", 90, "Source diff; inspect affected paths for specialized inputs")
    if suffix in {".md", ".rst", ".txt", ".adoc"} and matches(
        r"\b(?:architecture|system design|requirements|component|interface|subsystem|connects to)\b|아키텍처|요구사항|구성 요소|인터페이스",
        content,
    ):
        add("system-design", 65, "Design or requirements language")
    return hits


def sample(path):
    with path.open("rb") as stream:
        data = stream.read(MAX_SAMPLE)
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    if b"\0" in data:
        return ""
    return data.decode("utf-8-sig", errors="replace")


def candidates(root):
    if root.is_file():
        yield root
        return
    for directory, subdirs, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        if "target" in subdirs and not (base / "target").is_symlink():
            manifest = base / "target" / "manifest.json"
            if manifest.is_file() and not manifest.is_symlink():
                yield manifest
        subdirs[:] = sorted(
            item for item in subdirs
            if item not in SKIP and not item.startswith(".") and not (base / item).is_symlink()
        )
        for name in sorted(filenames):
            path = base / name
            if not path.is_symlink() and (path.suffix or path.name in {"Dockerfile"}):
                yield path


def inspect(paths, focus=None, limit=4000):
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["domains"]
    findings = {domain: [] for domain in registry}
    seen = set()
    notices = []
    truncated = False
    for supplied in paths:
        root = Path(supplied)
        if not (root.is_file() or root.is_dir()):
            raise ValueError(f"input does not exist: {root}")
        for path in candidates(root):
            resolved = path.resolve()
            if resolved in seen:
                continue
            if len(seen) >= limit and not root.is_file():
                truncated = True
                break
            seen.add(resolved)
            try:
                for hit in classify(path, sample(path)):
                    findings[hit["domain"]].append({
                        "file": str(path), "strength": hit["strength"], "marker": hit["marker"],
                    })
            except OSError as error:
                if len(notices) < 10:
                    notices.append(f"Could not read {path}: {error.strerror}")

    ranked = []
    for domain, items in findings.items():
        if items:
            items.sort(key=lambda hit: (-hit["strength"], hit["file"]))
            ranked.append({"domain": domain, "skill": registry[domain]["skill"],
                           "strength": items[0]["strength"], "matches": len(items), "files": items[:8]})
    ranked.sort(key=lambda item: (-item["strength"], item["domain"]))
    if truncated:
        notices.append(f"Directory scan reached {limit} files; narrow the scope or name additional files explicitly.")
    strongest = [item["domain"] for item in ranked if item["strength"] == ranked[0]["strength"]]
    return {"focus": focus, "suggested_primary": focus or (strongest[0] if len(strongest) == 1 else None),
            "candidates": ranked, "files_scanned": len(seen), "notices": notices}


def main():
    domains = json.loads(REGISTRY.read_text(encoding="utf-8"))["domains"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=["."])
    parser.add_argument("--focus", choices=domains)
    args = parser.parse_args()
    try:
        payload = inspect(args.paths, args.focus)
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
