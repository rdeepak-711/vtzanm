"""Step 1a: the report card. Spec rule 6 (spec/site.md), decision D5.

Input is a list of errors (forecast - actual, MW). Output is a Summary.
"""

import dataclasses

import pytest

from windapp.metrics import Summary, p90, summarise


# The 5-hour example from the walkthrough: four too high, one too low.
EXAMPLE = [900.0, 1200.0, -300.0, 600.0, 1500.0]


def test_example_count():
    assert summarise(EXAMPLE).n == 5


def test_avg_miss_ignores_direction():
    # (900 + 1200 + 300 + 600 + 1500) / 5
    assert summarise(EXAMPLE).mae_mw == 900.0


def test_lean_keeps_direction():
    # (900 + 1200 - 300 + 600 + 1500) / 5
    assert summarise(EXAMPLE).bias_mw == 780.0


def test_too_high_counts_positive_errors():
    s = summarise(EXAMPLE)
    assert s.too_high == 4
    assert s.share_too_high == pytest.approx(0.8)


def test_worst_high_and_worst_low():
    s = summarise(EXAMPLE)
    assert s.max_error_mw == 1500.0
    assert s.min_error_mw == -300.0


def test_example_buffer():
    # sorted: -300, 600, 900, 1200, 1500; rank ceil(0.9 * 5) = 5
    assert summarise(EXAMPLE).p90_mw == 1500.0


def test_zero_error_is_not_too_high():
    s = summarise([0.0, 0.0, 10.0])
    assert s.too_high == 1


def test_all_too_low():
    s = summarise([-100.0, -400.0, -250.0])
    assert s.too_high == 0
    assert s.share_too_high == 0.0
    assert s.bias_mw == -250.0
    assert s.mae_mw == 250.0
    assert s.max_error_mw == -100.0
    assert s.min_error_mw == -400.0


def test_lean_equals_avg_miss_when_every_hour_is_too_high():
    # The 15 Jan pattern: no hour below zero, so nothing cancels.
    s = summarise([800.0, 1000.0, 1300.0])
    assert s.bias_mw == s.mae_mw == pytest.approx(1033.3, abs=0.05)


def test_values_rounded_to_one_decimal():
    s = summarise([0.33, 0.33, 0.34])
    assert s.mae_mw == 0.3
    assert s.bias_mw == 0.3


# --- p90: nearest rank, no interpolation -------------------------------------


def test_p90_on_24_values_is_rank_22():
    # A day has 24 hours: ceil(0.9 * 24) = 22
    assert p90([float(v) for v in range(1, 25)]) == 22.0


def test_p90_on_744_values_is_rank_670():
    # January has 744 hours: ceil(0.9 * 744) = 670
    assert p90([float(v) for v in range(1, 745)]) == 670.0


def test_p90_on_10_values_is_rank_9():
    assert p90([float(v) for v in range(1, 11)]) == 9.0


def test_p90_does_not_need_sorted_input():
    assert p90([5.0, 1.0, 4.0, 2.0, 3.0]) == 5.0


def test_p90_of_one_value_is_that_value():
    assert p90([-42.0]) == -42.0


def test_p90_does_not_change_the_input_list():
    errors = [3.0, 1.0, 2.0]
    p90(errors)
    assert errors == [3.0, 1.0, 2.0]


def test_summary_buffer_matches_p90():
    errors = [float(v) for v in range(-10, 14)]  # 24 values
    assert summarise(errors).p90_mw == p90(errors)


# --- empty input --------------------------------------------------------------


def test_empty_list_gives_zero_count_and_blanks():
    s = summarise([])
    assert s.n == 0
    for field in ("mae_mw", "bias_mw", "too_high", "share_too_high",
                  "p90_mw", "max_error_mw", "min_error_mw"):
        assert getattr(s, field) is None, field


# --- the Summary itself ---------------------------------------------------------


def test_summary_has_exactly_the_spec_fields():
    names = [f.name for f in dataclasses.fields(Summary)]
    assert names == ["n", "mae_mw", "bias_mw", "too_high", "share_too_high",
                     "p90_mw", "max_error_mw", "min_error_mw"]


def test_summary_cannot_be_changed_after_creation():
    s = summarise(EXAMPLE)
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.n = 99
