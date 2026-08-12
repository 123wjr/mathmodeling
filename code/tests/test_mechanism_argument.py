from pathlib import Path

from technical.mechanism_argument import build_argument


def test_mechanism_audit_is_monotone_and_condition_held_out():
    result = build_argument(Path("study_output"))
    for response in result["mechanism_monotonicity"].values():
        assert all(item["increasing"] for item in response.values())
    lco = result["leave_condition_out"]
    assert lco["ridge"]["n_conditions"] == 27
    assert lco["ridge"]["wins_vs_persistence"] == 27
