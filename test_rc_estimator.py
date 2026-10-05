"""Regression check against the hand calculation for the NOR2 output node."""
import json
import rc_estimator as rc


def test_nor_y_matches_hand_calc():
    tech = rc.load_tech("tech_nspl.csv")
    with open("nodes/nor_y.json") as f:
        node = json.load(f)
    rows = rc.estimate_node(tech, node)
    c_junc = sum(c for cat, _, c, _ in rows if cat == "junction")
    c_wire = sum(c for cat, _, c, _ in rows if cat == "wiring")
    assert abs(c_junc - 20.5) < 0.1
    assert abs(c_wire - 5.4) < 0.1


def test_nand_y_matches_hand_calc():
    tech = rc.load_tech("tech_nspl.csv")
    with open("nodes/nand_y.json") as f:
        node = json.load(f)
    rows = rc.estimate_node(tech, node)
    c_junc = sum(c for cat, _, c, _ in rows if cat == "junction")
    assert abs(c_junc - 17.4) < 0.1


def test_junction_cap_single_drain():
    tech = {"ndiff": {"area": 1.0, "fringe": 0.5, "rsh": None}}
    # area 2*1 = 2, perimeter 2*1 + 2 = 4 -> 2*1.0 + 4*0.5 = 4.0
    assert rc.junction_cap(tech, "ndiff", w=2, l=1) == 4.0


if __name__ == "__main__":
    test_nor_y_matches_hand_calc()
    test_nand_y_matches_hand_calc()
    test_junction_cap_single_drain()
    print("all tests passed")
