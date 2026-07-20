import json
import sys

from scripts.export_eqs_v3_subset import main


def test_export_replaces_only_eqs_fields_and_writes_comparison(tmp_path, monkeypatch):
    source = tmp_path / "source.json"
    scores = tmp_path / "scores.json"
    output = tmp_path / "output.json"
    comparison = tmp_path / "comparison.json"
    source.write_text(
        json.dumps(
            [
                {
                    "name": "Example",
                    "corp_code": "00000001",
                    "market_cap": 123,
                    "total": 40.0,
                    "modules": {"M1": {"score": 40.0, "note": "old"}},
                }
            ]
        ),
        encoding="utf-8",
    )
    scores.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "corp_code": "00000001",
                        "total": 70.0,
                        "grade": "B",
                        "industry_code": "261",
                        "excluded": [],
                        "modules": [
                            {"name": "M1", "score": 70.0, "note": "new"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "export_eqs_v3_subset.py",
            "--input",
            str(source),
            "--scores",
            str(scores),
            "--output",
            str(output),
            "--comparison-output",
            str(comparison),
        ],
    )

    assert main() == 0
    record = json.loads(output.read_text(encoding="utf-8"))[0]
    assert record["market_cap"] == 123
    assert record["total"] == 70.0
    assert record["modules"]["M1"]["note"] == "new"
    assert record["eqs_method"] == "v3_all_krx_percentile_financial_short_history_2021_2025"
    assert json.loads(comparison.read_text(encoding="utf-8"))[0]["delta"] == 30.0
