#!/usr/bin/env python3
"""
Parasitic RC estimator for a single circuit node.

Estimates the parasitic capacitance (junction + wiring) and wiring resistance
of a node from layout geometry and per-unit process targets, then checks how
much of a measured pre/post-layout delay shift that capacitance can explain.

Usage:
    python rc_estimator.py --tech tech.csv --node nodes/nor_y.json
"""
import argparse
import csv
import json
import sys


def load_tech(path):
    """Read per-layer process targets from CSV.

    Columns: layer, area_ff_um2, fringe_ff_um, sheet_ohm_sq
    (empty sheet_ohm_sq is allowed for diffusion layers)
    """
    tech = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            tech[row["layer"].strip()] = {
                "area": float(row["area_ff_um2"]),
                "fringe": float(row["fringe_ff_um"]),
                "rsh": float(row["sheet_ohm_sq"]) if row["sheet_ohm_sq"].strip() else None,
            }
    return tech


def junction_cap(tech, layer, w, l):
    """Drain/source junction capacitance in fF.

    w: transistor width (um), l: S/D region length from gate edge (um).
    The edge facing the gate is excluded from the perimeter.
    """
    t = tech[layer]
    area = w * l
    perim = 2 * l + w
    return area * t["area"] + perim * t["fringe"]


def wire_cap(tech, layer, length, width):
    """Wire capacitance to substrate in fF (area + fringe on both sides)."""
    t = tech[layer]
    return length * width * t["area"] + 2 * length * t["fringe"]


def wire_res(tech, layer, length, width):
    """Wire resistance in ohms."""
    rsh = tech[layer]["rsh"]
    if rsh is None:
        raise ValueError(f"no sheet resistance for layer '{layer}'")
    return length / width * rsh


def estimate_node(tech, node):
    """Return a list of (category, name, C_fF, R_ohm) rows for one node."""
    rows = []
    for d in node.get("diffusions", []):
        c = junction_cap(tech, d["layer"], d["w"], d["l"])
        rows.append(("junction", d["name"], c, None))
    for wr in node.get("wires", []):
        c = wire_cap(tech, wr["layer"], wr["length"], wr["width"])
        r = wire_res(tech, wr["layer"], wr["length"], wr["width"])
        rows.append(("wiring", wr["name"], c, r))
    return rows


def required_delta_c(delay):
    """Capacitance (fF) needed to explain a delay shift, using dt = C * dV / I.

    Returns one value per drive current given (mA), so the result is a range.
    """
    dt = (delay["post_ps"] - delay["pre_ps"]) * 1e-12
    return [i_ma * 1e-3 * dt / delay["swing_v"] * 1e15 for i_ma in delay["drive_ma"]]


def report(node, rows):
    print(f"\n=== Node: {node['node']} ===")
    print(f"{'category':<10}{'element':<28}{'C (fF)':>9}{'R (ohm)':>10}")
    print("-" * 57)
    for cat, name, c, r in rows:
        r_txt = f"{r:.1f}" if r is not None else "-"
        print(f"{cat:<10}{name:<28}{c:>9.2f}{r_txt:>10}")

    c_junc = sum(c for cat, _, c, _ in rows if cat == "junction")
    c_wire = sum(c for cat, _, c, _ in rows if cat == "wiring")
    r_wire = sum(r for _, _, _, r in rows if r is not None)
    print("-" * 57)
    print(f"junction total : {c_junc:7.2f} fF")
    print(f"wiring total   : {c_wire:7.2f} fF   (wire R {r_wire:.1f} ohm)")
    if c_wire > 0:
        print(f"junction / wiring ratio: {c_junc / c_wire:.1f}x")

    delays = node.get("delays", [])
    if "delay" in node:
        delays = [node["delay"]] + delays
    est = c_junc + c_wire
    for d in delays:
        lo, hi = sorted(required_delta_c(d))
        print(f"\n[{d.get('edge', 'delay')}] {d['pre_ps']} -> {d['post_ps']} ps "
              f"(+{d['post_ps'] - d['pre_ps']} ps), drive {d['drive_ma'][0]}-{d['drive_ma'][-1]} mA")
        print(f"  needed dC      : {lo:.0f} - {hi:.0f} fF")
        print(f"  estimate covers: {est / hi * 100:.0f} - {est / lo * 100:.0f} %")
    return c_junc, c_wire


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--tech", required=True, help="process targets CSV")
    p.add_argument("--node", required=True, nargs="+", help="node geometry JSON file(s)")
    args = p.parse_args(argv)

    tech = load_tech(args.tech)
    for path in args.node:
        with open(path) as f:
            node = json.load(f)
        report(node, estimate_node(tech, node))


if __name__ == "__main__":
    sys.exit(main())
