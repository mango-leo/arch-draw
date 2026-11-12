import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "architecture-svg" / "scripts"
INPUTS = ROOT / "examples" / "inputs"
GRAPHS = ROOT / "examples" / "graphs"
sys.path.insert(0, str(SCRIPTS))

from classify import classify, inspect
from graph import project, validate
from layout import Box, Node, route_of, route_problem
from render_svg import render


SVG = {"svg": "http://www.w3.org/2000/svg"}
DOMAINS = ("software", "rtl", "board", "infra", "interfaces", "dataflow", "ai", "system-design")


def payload(name):
    return json.loads((GRAPHS / f"{name}.json").read_text(encoding="utf-8"))


def preview(name):
    graph = validate(payload(name))
    return {view.filename: ET.fromstring(render(graph, view)[0]) for view in project(graph)}


class ClassificationTests(unittest.TestCase):
    def test_each_domain_has_a_primary_and_a_skill(self):
        for domain in DOMAINS:
            with self.subTest(domain=domain):
                report = inspect([INPUTS / domain])
                self.assertEqual(report["suggested_primary"], domain)
                entry = report["candidates"][0]
                self.assertTrue(entry["files"])
                skill = ROOT / "skills" / entry["skill"] / "SKILL.md"
                self.assertIn("## Analysis", skill.read_text(encoding="utf-8"))

    def test_mixed_inputs_and_explicit_focus(self):
        for project, expected in (("app", {"software", "infra", "interfaces"}),
                                  ("device", {"software", "rtl", "board"})):
            report = inspect([INPUTS / "mixed" / project], "software")
            self.assertEqual({item["domain"] for item in report["candidates"]}, expected)
            self.assertEqual(report["suggested_primary"], "software")

    def test_cli_reports_both_specialists_when_mixed_evidence_ties(self):
        cases = {
            "app": {"infra": "compose.yaml", "interfaces": "api.yaml"},
            "device": {"board": "controller.net", "rtl": "led_top.sv"},
        }
        for project, expected in cases.items():
            with self.subTest(project=project):
                result = subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / "classify.py"), str(INPUTS / "mixed" / project)],
                    check=True, capture_output=True,
                )
                report = json.loads(result.stdout)
                self.assertIsNone(report["suggested_primary"])
                for candidate in report["candidates"][:2]:
                    filename = expected[candidate["domain"]]
                    self.assertIn(filename, {Path(match["file"]).name for match in candidate["files"]})
                self.assertEqual({item["domain"] for item in report["candidates"]}, {*expected, "software"})

    def test_routes_standalone_uvm_classes_to_rtl(self):
        cases = (
            "class env extends uvm_env;\nendclass",
            "class vseq extends local_base_vseq;\n  `uvm_object_utils(vseq)\nendclass",
            "class item #(int W = 32);\n  `uvm_object_param_utils(item #(W))\nendclass",
        )
        for content in cases:
            self.assertEqual([hit["domain"] for hit in classify(Path("uvm_component.sv"), content)], ["rtl"])
        self.assertEqual(classify(Path("plain_class.sv"), "class data extends container;\nendclass"), [])

    def test_filename_and_nested_json_keys_do_not_prove_format(self):
        self.assertEqual(classify(Path("deployment.yaml"), "title: ordinary YAML"), [])
        self.assertEqual(classify(Path("api.json"), '{"example":{"openapi":"3.1.0"}}'), [])


class GraphTests(unittest.TestCase):
    def test_examples_reference_source_and_render_deterministically(self):
        for name in [*DOMAINS, "app-stack", "device-stack"]:
            with self.subTest(name=name):
                data = payload(name)
                location = {"app-stack": "mixed/app", "device-stack": "mixed/device"}.get(name, name)
                for item in data["blocks"] + data["connections"]:
                    for ref in item["evidence"]:
                        source = (INPUTS / location / ref["path"]).read_text(encoding="utf-8").splitlines()
                        self.assertTrue(source[ref["line"] - 1].strip(), ref)
                graph = validate(data)
                for view in project(graph):
                    first, _ = render(graph, view)
                    self.assertEqual(first, render(graph, view)[0])
                    self.assertEqual(ET.fromstring(first).tag, "{http://www.w3.org/2000/svg}svg")

    def test_mixed_overview_projects_children_without_losing_endpoints(self):
        app = preview("app-stack")
        self.assertIn("detail-service.svg", app)
        self.assertFalse(app["overview.svg"].findall(".//svg:g[@data-style='paired-ports']", SVG))
        self.assertIsNotNone(app["overview.svg"].find(".//svg:a[@href='detail-service.svg']", SVG))
        entry = app["overview.svg"].find(".//svg:g[@data-connection='implements']/svg:title", SVG)
        self.assertIn("Orders API contract → checkout", entry.text)
        detail = app["detail-service.svg"]
        self.assertIsNotNone(detail.find(".//svg:g[@data-block='contract'][@data-role='external']", SVG))

        device = preview("device-stack")
        self.assertIsNotNone(device["overview.svg"].find(".//svg:g[@data-connection='pin']", SVG))
        self.assertIsNone(device["overview.svg"].find(".//svg:g[@data-connection='state']", SVG))
        self.assertIsNotNone(device["detail-top.svg"].find(".//svg:g[@data-connection='state']", SVG))

    def test_unresolved_edge_is_undirected_and_visible_in_legend(self):
        data = payload("device-stack")
        edge = data["connections"][0]
        edge.update(status="unresolved", direction="none", evidence=edge["evidence"][:1])
        graph = validate(data)
        svg = ET.fromstring(render(graph, next(project(graph)))[0])
        entry = svg.find(".//svg:g[@data-connection='mmio']", SVG)
        self.assertIn("set_led — led_top.u_reg", entry.find("svg:title", SVG).text)
        wire = svg.find(f".//svg:g[@data-wire='{entry.get('data-wire')}'][@data-direction]", SVG)
        if wire is not None:
            self.assertEqual(wire.get("data-direction"), "none")
            self.assertIsNone(wire.find("svg:polygon", SVG))

    def test_rejects_parent_cycles_invalid_ports_and_direction_claims(self):
        graph = payload("rtl")
        graph["blocks"][0]["parent"] = "first"
        with self.assertRaisesRegex(ValueError, "parent cycle"):
            validate(graph)
        graph = payload("rtl")
        graph["connections"][0]["source"]["port"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown source port"):
            validate(graph)
        graph = payload("rtl")
        graph["connections"][0]["status"] = "unresolved"
        with self.assertRaisesRegex(ValueError, "direction must be none"):
            validate(graph)


class GeometryTests(unittest.TestCase):
    def test_detects_block_penetration_and_a_crossing(self):
        nodes = {
            ("block", "a"): Node(("block", "a"), Box(0, 0, 20, 30), (), {}),
            ("block", "b"): Node(("block", "b"), Box(80, 0, 100, 30), (), {}),
        }
        a, b = nodes
        wire = route_of(((20, 15), (80, 15)), "forward")
        self.assertIsNone(route_problem(wire, a, b, nodes, []))
        self.assertEqual(route_problem(wire, a, b, nodes, [Box(50, 0, 50, 40)]), "wires intersect")
        self.assertEqual(route_problem(wire, a, b, nodes, [Box(25, 15, 50, 15)]), "wires intersect")
        nodes[("block", "middle")] = Node(("block", "middle"), Box(42, 8, 58, 22), (), {})
        self.assertEqual(route_problem(wire, a, b, nodes, []), "wire intersects a block")

    def test_dense_layout_preserves_every_connection_with_paired_ports(self):
        block = {"kind": "pipeline stage", "status": "inferred", "evidence": []}
        edge = {"label": "Wide connection payload", "kind": "message", "direction": "forward", "status": "inferred"}
        data = {"title": "촘촘한 연결과 긴 제목 " * 6, "blocks": [], "connections": []}
        for index in range(4):
            for side in ("left", "right"):
                data["blocks"].append(dict(block, id=f"{side}{index}", label="Very-long-component-label_" * 5))
        for i in range(4):
            for j in range(4):
                data["connections"].append(dict(edge, id=f"link{i}{j}", source={"block": f"left{i}"}, target={"block": f"right{j}"}))
        data["connections"].append(dict(edge, id="feedback", source={"block": "right0"}, target={"block": "left0"}))
        graph = validate(data)
        svg, paired = render(graph, next(project(graph)))
        self.assertGreater(paired, 0)
        document = ET.fromstring(svg)
        self.assertEqual(len(document.findall(".//svg:g[@data-connection]", SVG)), 17)
        nodes = document.find("svg:g[@id='blocks']", SVG)
        for group in document.findall(".//svg:g[@data-style='paired-ports']", SVG):
            identifier = group.get("data-wire")
            ends = [item for item in nodes.findall(".//svg:text", SVG) if item.text.startswith(f"{identifier} ·")]
            self.assertEqual(len(ends), 2, identifier)

    def test_svg_escapes_source_text(self):
        data = copy.deepcopy(payload("board"))
        data["blocks"][0]["label"] = "<script> & \"component\""
        graph = validate(data)
        svg, _ = render(graph, next(project(graph)))
        self.assertIn(b"&lt;script&gt; &amp;", svg)
        self.assertIsNone(ET.fromstring(svg).find(".//svg:script", SVG))


class InstallAndCliTests(unittest.TestCase):
    def test_install_conflict_preserves_existing_skill_and_installs_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            existing = project / ".claude/skills/architecture-rtl/SKILL.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("# Local edits\n", encoding="utf-8")
            command = [sys.executable, "-B", str(ROOT / "install_skills.py"), temporary]
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"existing skill differs", result.stderr)
            self.assertIn(b"architecture-rtl", result.stderr)
            self.assertEqual(existing.read_text(encoding="utf-8"), "# Local edits\n")
            self.assertFalse((project / ".agents").exists())
            self.assertEqual(list(existing.parent.parent.iterdir()), [existing.parent])

    def test_both_host_installations_are_identical_and_can_render(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            for _ in range(2):
                subprocess.run([sys.executable, "-B", str(ROOT / "install_skills.py"), temporary],
                               check=True, capture_output=True)
            for host in (".agents", ".claude"):
                installed = project / host / "skills"
                self.assertEqual(len(list(installed.glob("*/SKILL.md"))), 9)
                output = project / (host[1:] + "-example")
                subprocess.run([sys.executable, "-B", str(installed / "architecture-svg/scripts/render_svg.py"),
                                str(GRAPHS / "app-stack.json"), "--out", str(output)], check=True, capture_output=True)
                self.assertTrue((output / "detail-service.svg").is_file())
            self.assertEqual((project / "agents-example/overview.svg").read_bytes(),
                             (project / "claude-example/overview.svg").read_bytes())


if __name__ == "__main__":
    unittest.main()
