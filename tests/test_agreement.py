"""Agreement statistics (`capillary.agreement`) against published and hand-computed values."""

import math

import numpy as np
import pytest

from capillary.agreement import bland_altman, bland_altman_ratio, cohens_kappa, icc, same_direction

# Shrout & Fleiss (Psychol Bull 1979;86:420-8), table 2: six targets rated by four judges.
SHROUT_FLEISS = np.array([[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8], [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]], float)


def test_icc_reproduces_shrout_and_fleiss():
    result = icc(SHROUT_FLEISS)
    assert (result['n'], result['k']) == (6, 4)
    # ICC(2,1) = 0.29 and ICC(3,1) = 0.71 in the paper; the intervals are those of McGraw & Wong (1996),
    # as R's psych::ICC reports them for this table: 0.019-0.76 and 0.34-0.95.
    assert result['agreement'] == pytest.approx(0.290, abs=0.001)
    assert result['agreement_ci_low'] == pytest.approx(0.019, abs=0.001)
    assert result['agreement_ci_high'] == pytest.approx(0.761, abs=0.001)
    assert result['consistency'] == pytest.approx(0.715, abs=0.001)
    assert result['consistency_ci_low'] == pytest.approx(0.342, abs=0.001)
    assert result['consistency_ci_high'] == pytest.approx(0.946, abs=0.001)


def test_icc_leaves_out_incomplete_items_and_needs_two_of_each():
    table = np.vstack([SHROUT_FLEISS, [np.nan, 1, 2, 3]])
    assert icc(table)['agreement'] == pytest.approx(icc(SHROUT_FLEISS)['agreement'])
    assert math.isnan(icc(SHROUT_FLEISS[:1])['agreement'])
    assert math.isnan(icc(SHROUT_FLEISS[:, :1])['consistency'])


def test_icc_of_identical_raters_is_one_and_of_a_constant_offset_shows_in_agreement_only():
    rng = np.random.default_rng(1)
    truth = rng.normal(0.05, 0.02, 30)
    same = icc(np.column_stack([truth, truth]))
    assert same['agreement'] == pytest.approx(1.0) and same['consistency'] == pytest.approx(1.0)
    shifted = icc(np.column_stack([truth, truth + 0.02]))
    assert shifted['consistency'] == pytest.approx(1.0)
    assert shifted['agreement'] < 0.8


def test_bland_altman_by_hand():
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = a - np.array([0.1, -0.1, 0.2, 0.0, 0.3])
    result = bland_altman(a, b)
    # differences 0.1, -0.1, 0.2, 0, 0.3: mean 0.1, SD sqrt(0.025); t(0.975, 4) = 2.7764
    sd = math.sqrt(0.025)
    assert result['n'] == 5
    assert result['bias'] == pytest.approx(0.1)
    assert result['sd'] == pytest.approx(sd)
    assert result['loa_low'] == pytest.approx(0.1 - 1.96 * sd)
    assert result['loa_high'] == pytest.approx(0.1 + 1.96 * sd)
    assert result['bias_ci_high'] - result['bias'] == pytest.approx(2.7764 * sd / math.sqrt(5), rel=1e-4)
    assert result['loa_high_ci_high'] - result['loa_high'] == pytest.approx(2.7764 * sd * math.sqrt(3 / 5), rel=1e-4)


def test_bland_altman_ignores_incomplete_pairs_and_handles_too_few():
    assert bland_altman([1.0, np.nan, 3.0], [1.5, 2.0, np.nan])['n'] == 1
    one = bland_altman([1.0], [0.5])
    assert one['bias'] == pytest.approx(0.5) and math.isnan(one['sd'])
    assert bland_altman([], [])['n'] == 0
    with pytest.raises(ValueError):
        bland_altman([1, 2], [1])


def test_proportional_bias_is_found_and_disappears_on_the_ratio_scale():
    rng = np.random.default_rng(3)
    b = rng.uniform(0.01, 0.2, 60)
    a = 1.2 * b * np.exp(rng.normal(0, 0.03, 60))     # 20% higher, more so the faster the flow
    absolute = bland_altman(a, b)
    assert absolute['slope_ci_low'] > 0                # the difference grows with the velocity
    ratio = bland_altman_ratio(a, b)
    assert ratio['n'] == 60
    assert ratio['ratio'] == pytest.approx(1.2, rel=0.02)
    assert ratio['loa_low'] < 1.2 < ratio['loa_high'] and ratio['loa_high'] / ratio['loa_low'] < 1.2
    assert ratio['ratio_ci_low'] < ratio['ratio'] < ratio['ratio_ci_high']


def test_ratio_scale_compares_magnitudes_of_same_sign_pairs_only():
    result = bland_altman_ratio([-0.2, 0.1, 0.0, 0.3], [-0.1, -0.1, 0.1, 0.3])
    assert result['n'] == 2                            # (-0.2, -0.1) and (0.3, 0.3)
    assert result['ratio'] == pytest.approx(math.sqrt(2.0))


def test_cohens_kappa_by_hand():
    # 50 items: both yes 20, only the first 5, only the second 10, both no 15
    first = np.array([1] * 25 + [0] * 25, float)
    second = np.array([1] * 20 + [0] * 5 + [1] * 10 + [0] * 15, float)
    result = cohens_kappa(first, second)
    # observed 0.7, chance 0.5 x 0.6 + 0.5 x 0.4 = 0.5 -> kappa 0.4; SE sqrt(0.7 x 0.3 / (50 x 0.25))
    assert (result['both'], result['first_only'], result['second_only'], result['neither']) == (20, 5, 10, 15)
    assert result['agreement'] == pytest.approx(0.7)
    assert result['kappa'] == pytest.approx(0.4)
    se = math.sqrt(0.7 * 0.3 / (50 * 0.25))
    assert result['kappa_ci_high'] - result['kappa'] == pytest.approx(1.95996 * se, rel=1e-4)


def test_cohens_kappa_leaves_out_items_not_judged_and_is_undefined_without_variety():
    result = cohens_kappa([1, 0, np.nan, 1], [1, 0, 1, np.nan])
    assert result['n'] == 2 and result['kappa'] == pytest.approx(1.0)
    nearly = cohens_kappa([1] * 6 + [0] * 11 + [0], [1] * 6 + [0] * 11 + [1])
    assert nearly['kappa'] < 1 and nearly['kappa_ci_high'] == 1.0          # the interval stops at 1
    always = cohens_kappa([1, 1, 1], [1, 1, 1])
    assert always['agreement'] == 1.0 and math.isnan(always['kappa'])


def test_same_direction():
    result = same_direction([0.1, -0.2, 0.3, np.nan], [0.2, 0.1, 0.4, 0.5])
    assert result['n'] == 3 and result['fraction'] == pytest.approx(2 / 3)
