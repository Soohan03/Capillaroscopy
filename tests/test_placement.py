"""Whether two lines follow the same capillary (`capillary.placement`)."""

from capillary import placement

LIMB = [(60.0, 200.0), (63.0, 150.0), (66.0, 100.0), (70.0, 50.0)]           # 150 px up a capillary limb


def shifted(points, dx=0.0, dy=0.0):
    return [(x + dx, y + dy) for x, y in points]


def test_lines_along_each_other_and_their_direction():
    assert placement.line_overlap(LIMB, LIMB) == (1.0, 1.0, 1)
    covered_a, covered_b, direction = placement.line_overlap(LIMB, list(reversed(shifted(LIMB, dx=2))))
    assert covered_a == 1.0 and covered_b == 1.0 and direction == -1
    other_limb = shifted(LIMB, dx=26)
    assert placement.line_overlap(LIMB, other_limb)[:2] == (0.0, 0.0)
    upper_half = LIMB[2:]                                                     # the top 50 px only
    covered_a, covered_b, _ = placement.line_overlap(LIMB, upper_half)
    assert covered_b == 1.0 and 0.25 < covered_a < 0.5


def test_the_same_capillary_placed_a_little_differently_matches():
    again = shifted(LIMB, dx=1.5)
    covered_a, covered_b, direction = placement.line_overlap(LIMB, again)
    assert max(covered_a, covered_b) >= placement.MIN_LINE_OVERLAP and direction == 1
    assert max(placement.line_overlap(LIMB, shifted(LIMB, dx=placement.MATCH_PX + 3))[:2]) < placement.MIN_LINE_OVERLAP
