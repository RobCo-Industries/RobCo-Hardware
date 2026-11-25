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
