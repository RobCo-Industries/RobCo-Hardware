#!/usr/bin/env python3
"""Make a kicad-cli board SVG fit for the docs.

    board_svg.py <exported.svg> <out.svg> <title>

kicad-cli writes the file name and the export date into <title>, so two
exports of the same board differ. It also leaves the background transparent,
and its default theme draws light lines meant for a dark canvas. This step
replaces the title, gives the picture a display width and puts KiCad's dark
board background behind it, so it reads on GitHub's light and dark pages.
"""

import re
import sys

BACKGROUND = "#001023"  # the board editor's default background
WIDTH = "600"  # px, the default display width; the viewBox keeps the scale


def normalise(svg: str, title: str) -> str:
    svg, n = re.subn(r"<title>.*?</title>", f"<title>{title}</title>", svg, count=1, flags=re.S)
    if n != 1:
        raise ValueError("no <title> in the SVG")
    svg, n = re.subn(r'width="[^"]*" height="[^"]*" (viewBox="[^"]*")', rf'width="{WIDTH}" \1', svg, count=1)
    if n != 1:
        raise ValueError("no width, height and viewBox on <svg>")
    box = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', svg)
    x, y, w, h = box.groups()
    rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{BACKGROUND}"/>\n'
    end = svg.index("</desc>") + len("</desc>\n")
    return svg[:end] + rect + svg[end:]


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst, title = argv
    with open(src, encoding="utf-8") as fh:
        svg = normalise(fh.read(), title)
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
