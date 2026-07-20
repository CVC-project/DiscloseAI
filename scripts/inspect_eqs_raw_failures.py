"""Inspect why selected DART reports cannot be retrieved as document XML ZIPs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.financial.collector import _get, fetch_corp_codes
from recover_eqs_raw_panels import _select_report


TARGET_CODES = (
    "00978075",  # 머니무브
    "00929228",  # 엔에스컴퍼니
    "00414540",  # 대주이엔티
    "01466832",  # 라피치
    "01229240",  # 가이아코퍼레이션
    "01035942",  # 메디안디노스틱
)


def main() -> int:
    corp_index = {corp.corp_code: corp for corp in fetch_corp_codes()}
    results = []
    for corp_code in TARGET_CODES:
        corp = corp_index.get(corp_code)
        reports = _get(
            "https://opendart.fss.or.kr/api/list.json",
            {"corp_code": corp_code, "bgn_de": "20210101", "page_count": 100},
        ).json().get("list", [])
        selected = []
        for year in range(2021, 2026):
            report = _select_report(reports, year)
            if not report:
                selected.append({"year": year, "selected": None})
                continue
            response = _get(
                "https://opendart.fss.or.kr/api/document.xml", {"rcept_no": report["rcept_no"]}
            )
            body = response.content
            selected.append(
                {
                    "year": year,
                    "rcept_no": report["rcept_no"],
                    "report_nm": report.get("report_nm"),
                    "rcept_dt": report.get("rcept_dt"),
                    "http_status": response.status_code,
                    "is_zip": body[:2] == b"PK",
                    "response_preview": body[:300].decode("utf-8", errors="replace"),
                }
            )
        results.append(
            {
                "corp_code": corp_code,
                "corp_name": corp.corp_name if corp else None,
                "report_count": len(reports),
                "selected_reports": selected,
            }
        )
    print(json.dumps({"companies": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
