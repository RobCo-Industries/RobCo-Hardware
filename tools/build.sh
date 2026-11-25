#!/usr/bin/env bash
# One entry point to generate, check and export a board.
#
#   tools/build.sh <command> [board]
#
# Commands:
#   gen     regenerate the KiCad files of the board from <board>/gen/
#   check   regen-diff, ERC, pin check, DRC; fails on any difference or violation
#   regen   only the "regenerated files equal committed files" check
#   erc     only ERC
#   pins    only the pin check
#   pintable  only the check that the pin table in spec/SPEC.md matches pins.yaml
#   nettest the board's netlist tests, the file NETTEST in board.env names
#   drc     only DRC
#   docs    schematic PDF and SVG, netlist, BOM
#   render  3D renders: top, bottom, isometric
#   fab     gerbers and drill files
#   out     docs, render and fab
#   test    the Python tests, in a venv under build/
#
# The board defaults to "toy". Outputs go to build/<board>/.
#
# Variables, all optional:
#   KICAD_CLI            path to kicad-cli
#   KICAD_PY             a Python that can import pcbnew
#   ROBCO_BOARD_SUPPORT  path to RobCo-Core docs/spec/BOARD_SUPPORT.md, or "skip".
#                        Unset, the script looks for a RobCo-Core clone next to
#                        this repository, then two levels up, which finds it
#                        from a worktree under .worktrees/.
#   KICAD10_SYMBOL_DIR, KICAD10_FOOTPRINT_DIR, KICAD10_3DMODEL_DIR
#                        stock library folders; found from known places if unset
#
# A board folder may hold board.env with these flags:
#   ROUTED=yes        DRC fails on any violation or unrouted net. Without it
#                     DRC runs in report mode.
#   OWNER_ROUTED=yes  the owner routed the board in KiCad: the committed board
#                     file is the source. gen and regen then cover the
#                     schematic and project files only, never the board file.
#   NETTEST=tests/x.py  netlist tests, run with ROBCO_NETLIST set to the
#                     exported netlist; check fails when one fails.
# A board with no board file yet is checked as a schematic: regen, ERC and pin
# checks run, DRC and renders are skipped with a line that says so.
#
# ROBCO_BOARD_DIR overrides the board folder, for tests.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CMD="${1:-}"
BOARD="${2:-toy}"
BDIR="${ROBCO_BOARD_DIR:-$REPO/$BOARD}"
OUT="$REPO/build/$BOARD"

first_existing() {
  for p in "$@"; do
    if [ -e "$p" ]; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

MAC_APP=/Applications/KiCad/KiCad.app/Contents
KICAD_CLI="${KICAD_CLI:-$(first_existing "$MAC_APP/MacOS/kicad-cli" /usr/bin/kicad-cli /usr/local/bin/kicad-cli || echo kicad-cli)}"
KICAD_PY="${KICAD_PY:-$(first_existing "$MAC_APP/Frameworks/Python.framework/Versions/Current/bin/python3" /usr/bin/python3 || echo python3)}"

for kind in symbols footprints 3dmodels; do
  case "$kind" in
    symbols) var=KICAD10_SYMBOL_DIR ;;
    footprints) var=KICAD10_FOOTPRINT_DIR ;;
    3dmodels) var=KICAD10_3DMODEL_DIR ;;
  esac
  if [ -z "${!var:-}" ]; then
    if dir="$(first_existing "$MAC_APP/SharedSupport/$kind" "/usr/share/kicad/$kind" "/usr/local/share/kicad/$kind")"; then
      export "$var=$dir"
    fi
  fi
done

if [ -z "${ROBCO_BOARD_SUPPORT:-}" ]; then
  ROBCO_BOARD_SUPPORT="$(first_existing "$REPO/../RobCo-Core/docs/spec/BOARD_SUPPORT.md" \
    "$REPO/../../RobCo-Core/docs/spec/BOARD_SUPPORT.md" || echo "")"
fi

ROUTED=no
OWNER_ROUTED=no
NETTEST=""
if [ -f "$BDIR/board.env" ]; then
  # shellcheck disable=SC1090,SC1091
  . "$BDIR/board.env"
fi

say() { echo "build.sh: $*"; }
die() { echo "build.sh: error: $*" >&2; exit 1; }

# kicad-cli prints font warnings on stderr. Keep them in a log file.
kcli() {
  mkdir -p "$OUT"
  "$KICAD_CLI" "$@" 2>>"$OUT/kicad-cli.log"
}

sch() { echo "$BDIR/kicad/$BOARD.kicad_sch"; }
pcb() { echo "$BDIR/kicad/$BOARD.kicad_pcb"; }

netlist() {
  mkdir -p "$OUT"
  kcli sch export netlist -o "$OUT/$BOARD.net" "$(sch)" >/dev/null
}

# Generate into a folder: the schematic and project files, then the board.
gen_into() {
  local dest="$1"
  [ -d "$BDIR/gen" ] || die "no generator folder $BDIR/gen"
  "$KICAD_PY" "$BDIR/gen/circuit.py" "$dest"
  if [ "$OWNER_ROUTED" = yes ]; then
    say "board routed by the owner: the board generator does not run, $BOARD.kicad_pcb is the source"
  elif [ -f "$BDIR/gen/board.py" ]; then
    mkdir -p "$OUT"
    "$KICAD_CLI" sch export netlist -o "$OUT/gen.net" "$dest/$BOARD.kicad_sch" >/dev/null 2>>"$OUT/kicad-cli.log"
    "$KICAD_PY" "$BDIR/gen/board.py" "$OUT/gen.net" "$dest" 2>>"$OUT/pcbnew.log"
  fi
}

cmd_gen() {
  gen_into "$BDIR/kicad"
  say "generated $BOARD/kicad"
}

cmd_regen() {
  local tmp="$OUT/regen"
  rm -rf "$tmp"
  mkdir -p "$tmp"
  gen_into "$tmp"
  local bad=0
  for f in "$tmp"/*; do
    local name
    name="$(basename "$f")"
    case "$name" in *.kicad_prl) continue ;; esac
    if [ "$OWNER_ROUTED" = yes ]; then
      case "$name" in *.kicad_pcb) continue ;; esac
    fi
    if ! cmp -s "$f" "$BDIR/kicad/$name"; then
      echo "build.sh: $BOARD/kicad/$name differs from a fresh generation" >&2
      diff -u "$BDIR/kicad/$name" "$f" | head -40 >&2 || true
      bad=1
    fi
  done
  if [ "$OWNER_ROUTED" = yes ]; then
    say "board routed by the owner: $BOARD.kicad_pcb not compared"
  fi
  [ "$bad" = 0 ] || die "regenerated files differ from the committed files: run tools/build.sh gen $BOARD and commit"
  say "regenerated files equal the committed files"
}

cmd_erc() {
  mkdir -p "$OUT"
  if ! kcli sch erc --exit-code-violations --format report -o "$OUT/erc.rpt" "$(sch)" >/dev/null; then
    cat "$OUT/erc.rpt" >&2
    die "ERC found violations"
  fi
  say "ERC clean"
}

cmd_pins() {
  local args=(--pins "$BDIR/spec/pins.yaml")
  if [ -f "$(sch)" ]; then
    netlist
    args+=(--netlist "$OUT/$BOARD.net")
  else
    say "no schematic yet: pins.yaml checked against the software pin table only"
    [ "$ROBCO_BOARD_SUPPORT" != skip ] || die "no schematic and ROBCO_BOARD_SUPPORT=skip: nothing to check"
  fi
  if [ "$ROBCO_BOARD_SUPPORT" = skip ]; then
    say "pin check against the software pin table skipped: ROBCO_BOARD_SUPPORT=skip"
  elif [ -n "$ROBCO_BOARD_SUPPORT" ]; then
    args+=(--board-support "$ROBCO_BOARD_SUPPORT")
  else
    die "BOARD_SUPPORT.md not found: set ROBCO_BOARD_SUPPORT to its path, or to skip"
  fi
  "$KICAD_PY" "$REPO/tools/check_pins.py" "${args[@]}"
}

# The pin table in spec/SPEC.md must equal the one generated from pins.yaml.
cmd_pintable() {
  local doc="$BDIR/spec/SPEC.md"
  if [ ! -f "$doc" ] || ! grep -q 'pin-table:start' "$doc"; then
    say "no pin table markers in $BOARD/spec/SPEC.md, pin table check skipped"
    return 0
  fi
  "$KICAD_PY" "$REPO/tools/gen_pin_table.py" --check "$BDIR/spec/pins.yaml" "$doc"
}

# Netlist tests of a board, named by NETTEST in board.env, run on the exported netlist.
cmd_nettest() {
  [ -n "$NETTEST" ] || { say "no netlist tests for $BOARD"; return 0; }
  local t="$NETTEST"
  case "$t" in /*) ;; *) t="$REPO/$t" ;; esac
  [ -f "$t" ] || die "NETTEST file not found: $NETTEST"
  [ -f "$(sch)" ] || { say "no schematic yet: netlist tests skipped"; return 0; }
  netlist
  ROBCO_NETLIST="$OUT/$BOARD.net" "$KICAD_PY" "$t" || die "netlist tests failed"
}

cmd_drc() {
  mkdir -p "$OUT"
  local pcbfile
  pcbfile="$(pcb)"
  [ -f "$pcbfile" ] || { say "no board file yet, schematic only: DRC skipped"; return 0; }
  if [ "$ROUTED" = yes ]; then
    if ! kcli pcb drc --exit-code-violations --refill-zones --format report -o "$OUT/drc.rpt" "$pcbfile" >/dev/null; then
      cat "$OUT/drc.rpt" >&2
      die "DRC found violations or unrouted nets"
    fi
    say "DRC clean"
  else
    kcli pcb drc --refill-zones --format report -o "$OUT/drc.rpt" "$pcbfile" >/dev/null
    say "DRC in report mode, board not routed yet: see build/$BOARD/drc.rpt"
  fi
}

cmd_check() {
  if [ -d "$BDIR/gen" ]; then
    cmd_regen
    cmd_erc
  else
    say "no generator yet for $BOARD: regen-diff and ERC skipped"
  fi
  cmd_pins
  cmd_pintable
  cmd_nettest
  cmd_drc
}

cmd_docs() {
  mkdir -p "$OUT/svg"
  kcli sch export pdf -o "$OUT/$BOARD-schematic.pdf" "$(sch)" >/dev/null
  kcli sch export svg -o "$OUT/svg" "$(sch)" >/dev/null
  netlist
  # "Off board" marks parts to buy that do not sit on the board, such as a module or a speaker.
  kcli sch export bom --fields 'Reference,Value,Footprint,QUANTITY,DNP,EXCLUDE_FROM_BOARD' \
    --labels 'Refs,Value,Footprint,Qty,DNP,Off board' -o "$OUT/$BOARD-bom.csv" "$(sch)" >/dev/null
  say "schematic PDF, SVG, netlist and BOM in build/$BOARD"
}

cmd_render() {
  [ -f "$(pcb)" ] || { say "no board file yet, schematic only: renders skipped"; return 0; }
  mkdir -p "$OUT/render"
  # Warns, with a ::warning:: line per missing model and the count.
  "$KICAD_PY" "$REPO/tools/check_models.py" "$(pcb)"
  kcli pcb render --side top -w 1600 -h 900 -o "$OUT/render/$BOARD-top.png" "$(pcb)" >/dev/null
  kcli pcb render --side bottom -w 1600 -h 900 -o "$OUT/render/$BOARD-bottom.png" "$(pcb)" >/dev/null
  kcli pcb render --rotate '-45,0,45' --quality high --floor --perspective -w 1600 -h 900 \
    -o "$OUT/render/$BOARD-iso.png" "$(pcb)" >/dev/null
  for v in top bottom iso; do
    [ -s "$OUT/render/$BOARD-$v.png" ] || die "render $v produced no image"
  done
  say "renders in build/$BOARD/render"
}

cmd_fab() {
  [ -f "$(pcb)" ] || { say "no board file yet, schematic only: gerbers and drill skipped"; return 0; }
  mkdir -p "$OUT/fab"
  kcli pcb export gerbers -o "$OUT/fab/" "$(pcb)" >/dev/null
  kcli pcb export drill -o "$OUT/fab/" "$(pcb)" >/dev/null
  ls "$OUT/fab/"*.gbr >/dev/null 2>&1 || die "no gerber files written"
  say "gerbers and drill files in build/$BOARD/fab"
}

cmd_test() {
  local venv="$REPO/build/venv"
  if [ ! -x "$venv/bin/python" ]; then
    python3 -m venv "$venv"
    "$venv/bin/pip" install --quiet pytest==8.3.4
  fi
  "$venv/bin/python" -m pytest -q "$REPO/tests"
}

case "$CMD" in
  gen) cmd_gen ;;
  regen) cmd_regen ;;
  erc) cmd_erc ;;
  pins) cmd_pins ;;
  pintable) cmd_pintable ;;
  nettest) cmd_nettest ;;
  drc) cmd_drc ;;
  check) cmd_check ;;
  docs) cmd_docs ;;
  render) cmd_render ;;
  fab) cmd_fab ;;
  out) cmd_docs; cmd_render; cmd_fab ;;
  test) cmd_test ;;
  *) sed -n '2,45p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
