from pathlib import Path

import csv

from technical.prepare_nmc_modes import _c_rate, _folder_metadata, _summary_load_label, _write_chemistry_csvs


def test_metadata_parser_keeps_ambiguous_labels_explicit():
    assert _folder_metadata(Path("P462_NMC532_R2 design")) == ("P462", "NMC532", "R2")
    assert _summary_load_label("P462 (NMC532, high load)") == "high load"
    assert _c_rate("4.5C") == 4.5
    assert _c_rate("unknown") is None


def test_writer_splits_chemistries_without_mixing(tmp_path):
    rows = [
        {"chemistry": "NMC532", "cell_id": "a", "cycle": 1},
        {"chemistry": "NMC811", "cell_id": "b", "cycle": 1},
    ]

    paths = _write_chemistry_csvs(tmp_path, rows)

    assert set(paths) == {"NMC532", "NMC811"}
    for chemistry, path in paths.items():
        with path.open(newline="", encoding="utf-8") as handle:
            assert {row["chemistry"] for row in csv.DictReader(handle)} == {chemistry}
