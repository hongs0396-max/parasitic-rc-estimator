# Parasitic RC Estimator

[한국어](README.ko.md)

A small Python tool that estimates the parasitic capacitance and resistance of a
circuit node from layout geometry and per-unit process targets, and checks how
much of a measured pre- vs. post-layout delay shift that parasitic load explains.

Built to re-check a delay anomaly found in my own standard-cell layouts
(0.5 µm CMOS, Calibre PEX).

## Background

After Calibre PEX, the NOR2 fall delay went from **44 ps to 270 ps (+513%)**. That was
the largest percentage increase among six cells. My first explanation was oversized
output-to-VSS routing. This tool was built to test that explanation with numbers.

## Method

For one node, the tool adds up:

- **Junction capacitance** of each drain/source region: `area × C_area + perimeter × C_fringe`
  (the edge facing the gate is excluded from the perimeter)
- **Wiring capacitance** of each wire segment: `length × width × C_area + 2 × length × C_fringe`
- **Wiring resistance**: `length / width × R_sheet`

It then compares the total with the capacitance needed to explain the measured
delay shift, `ΔC = I × Δt / ΔV`, evaluated over a range of drive currents.

## Findings (NOR2 vs. NAND2 output nodes)

| | NOR2.Y | NAND2.Y |
|---|---|---|
| Junction / wiring capacitance | 3.8× | 4.1× |
| Wiring resistance | ~4 Ω | ~3 Ω |
| Fall delay increase | +226 ps | +360 ps |
| Estimate covers (fall) | 33–54% of needed ΔC | 34–58% of needed ΔC |
| Estimate covers (rise) | 29–48% | 21–35% |

1. **The NOR outlier was mostly a percentage effect.** In absolute terms the NOR fall
   delay grew less than the NAND fall delay; the +513% came from the small 44 ps baseline.
   NOR rise (+250 ps) and fall (+226 ps) grew by similar amounts, which points to load
   added at the output node rather than a VSS-path-specific problem.
2. **Both cells show the same pattern.** Junction capacitance is ~4× the routing
   capacitance in both, and the estimate explains a similar share of the shift. NOR is
   not a special case. The schematic netlist carried only W/L/m (no drain/source area),
   so junction capacitance would first appear after extraction.
3. **What remains open.** The estimate explains a third to a half of the shift.
   Internal stack nodes, input-node gate load and testbench effects are not modeled,
   the drive current is a crude Idsat-based range, and the geometry is approximate
   (measured by hand from the layout, not extracted). Confirming the cause needs the extracted netlist (per-node C).
4. **Why only the two gates.** Latches and flip-flops are multi-stage: their clk-to-Q
   delay depends on several internal nodes, so a single-node model does not apply and
   measuring every internal node by hand would add more error than insight.

## Usage

```bash
python rc_estimator.py --tech tech_template.csv --node nodes/nor_y.json nodes/nand_y.json
python test_rc_estimator.py
```

- `tech_template.csv`: illustrative per-unit values (not from any foundry PDK).
  Replace them with your own process targets locally.
- `nodes/*.json`: node geometry (diffusions, wires) and optional delay data.

Foundry process values are confidential and are not included in this repository.
