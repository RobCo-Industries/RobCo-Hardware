"""Check the Mermaid diagrams in the Markdown files without a renderer."""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

KEYWORDS = (
    "flowchart", "graph", "sequenceDiagram", "stateDiagram-v2", "stateDiagram",
    "classDiagram", "erDiagram", "gantt", "pie", "timeline", "mindmap", "block-beta",
)

# Text blocks that stay text, keyed by (file, first line of the block), with
# the reason. Only text screen mock-ups belong here.
KEPT = {}

BOX = re.compile(r"\+-{3}|[─-╿]")
PAIRS = {"(": ")", "[": "]", "{": "}"}


def markdown_files():
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=REPO, capture_output=True, text=True, check=True)
    return [p for p in out.stdout.split() if (REPO / p).exists()]


def fenced_blocks(text):
    blocks, lang, body = [], None, None
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            if body is None:
                lang, body = line.strip()[3:].strip(), []
            else:
                blocks.append((lang, body))
                body = None
        elif body is not None:
            body.append(line)
    return blocks


def line_problem(line):
    if "\t" in line:
        return "tab character"
    if line.count('"') % 2:
        return "unbalanced quotes"
    stack = []
    for ch in re.sub(r'"[^"]*"', "", line):
        if ch in PAIRS:
            stack.append(PAIRS[ch])
        elif ch in PAIRS.values():
            if not stack or stack.pop() != ch:
                return "unbalanced brackets"
    return "unbalanced brackets" if stack else None


def mermaid_problems(body):
    lines = [l for l in body if l.strip()]
    if not lines:
        return ["empty block"]
    problems = []
    if lines[0].split()[0] not in KEYWORDS:
        problems.append(f"unknown diagram keyword: {lines[0]!r}")
    for line in body:
        why = line_problem(line)
        if why:
            problems.append(f"{why}: {line!r}")
    return problems


def all_blocks():
    for path in markdown_files():
        for lang, body in fenced_blocks((REPO / path).read_text()):
            yield path, lang, body


def test_mermaid_blocks_are_well_formed():
    found = 0
    for path, lang, body in all_blocks():
        if lang == "mermaid":
            found += 1
            assert not mermaid_problems(body), (path, mermaid_problems(body))
    assert found >= 2


def test_no_ascii_box_diagrams_outside_the_allow_list():
    for path, lang, body in all_blocks():
        if lang != "mermaid" and any(BOX.search(l) for l in body):
            assert (path, body[0]) in KEPT, f"{path}: ASCII diagram, draw it in Mermaid: {body[0]!r}"


@pytest.mark.parametrize("body", [[], ["flowhcart TB"], ["flowchart TB", 'A["x] --> B'], ["flowchart TB", "A[x --> B"], ["flowchart TB", "\tA --> B"]])
def test_checker_rejects_broken_blocks(body):
    assert mermaid_problems(body)


# Path facts of the terminal controller block diagrams, read from its
# schematic. Each pair is a direct edge that must exist, or must not.
TC_SPEC = "terminal-controller/spec/SPEC.md"
TC_EDGES = [
    ("J2", "JP1"), ("P5V", "JP1"), ("JP1", "F1"), ("F1", "D1"), ("D1", "Q1"),
    ("Q1", "VSW"), ("VSW", "J3"), ("VSW", "U4"), ("D1", "JP8"), ("JP8", "VSW"), ("D1", "F2"), ("F2", "J4"), ("ARM", "Q2"), ("Q2", "Q1"),
    ("P5V", "M1"), ("U1", "U4"), ("U4", "J3"), ("J4", "U5"), ("U5", "U2"),
]
TC_NO_EDGES = [("JP1", "J3"), ("D1", "J3"), ("JP1", "Q1"), ("D1", "J4"), ("U2", "U4"), ("U1", "U5"),
    ("Q1", "JP8"), ("JP8", "Q1")]

LINK = re.compile(r'\s*(?:--\s*"[^"]*"\s*(-->|---)|(-->|---|-\.->|-\.-))\s*')
NODE = re.compile(r'([A-Za-z0-9_]+)')


def mermaid_graph(body):
    """Directed edges and the nodes of one flowchart. An undirected link counts both ways."""
    nodes, edges, linked = set(), set(), set()
    for line in body:
        text = re.sub(r'"[^"]*"', '""', line.strip())
        if not text or text.split()[0] in ("flowchart", "graph", "subgraph", "end", "direction"):
            continue
        parts = LINK.split(text)
        ids = [NODE.match(p.strip()).group(1) for p in parts[0::3]]
        ops = [a or b for a, b in zip(parts[1::3], parts[2::3])]
        nodes.update(ids)
        for a, op, b in zip(ids, ops, ids[1:]):
            edges.add((a, b))
            if ">" not in op:
                edges.add((b, a))
            linked.update((a, b))
    return nodes, edges, linked


def tc_graphs():
    blocks = [b for lang, b in fenced_blocks((REPO / TC_SPEC).read_text()) if lang == "mermaid"]
    assert blocks, "no Mermaid block in " + TC_SPEC
    return [mermaid_graph(b) for b in blocks]


def test_terminal_controller_diagram_follows_the_schematic():
    edges = set().union(*(e for _, e, _ in tc_graphs()))
    missing = [e for e in TC_EDGES if e not in edges]
    wrong = [e for e in TC_NO_EDGES if e in edges]
    assert not missing and not wrong, f"missing edges {missing}, wrong edges {wrong}"


def test_terminal_controller_diagram_has_no_lonely_node():
    for nodes, _, linked in tc_graphs():
        assert nodes <= linked, f"nodes without an edge: {sorted(nodes - linked)}"


def test_graph_parser_reads_labels_and_chains():
    nodes, edges, _ = mermaid_graph(['A["a"] -- "V_X" --> B --> C', "C --- D", 'E["e"]'])
    assert edges == {("A", "B"), ("B", "C"), ("C", "D"), ("D", "C")} and "E" in nodes
