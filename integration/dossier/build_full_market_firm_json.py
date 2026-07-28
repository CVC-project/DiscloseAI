"""전체 상장사 firm_<ticker>.json 생성 — integration-only (financial 코드 무수정, read-only import).

기존 48개사용 firm_<ticker>.json(EQS 탭)과 동일한 스키마를 전체 상장사(2,683개 EQS 산출
가능 기업)로 확장한다. EQS/F-EQS 점수 자체는 GPU에서 이미 계산된 결과를 그대로 쓰고
(재계산하지 않음), ratios/summary/highlights/glossary는 financial 모듈의 순수 규칙기반
코드(translator/*, glossary.py)를 read-only import해 재사용한다(LLM 미사용).

입력(모두 modules/financial/data/universe/, financial 소유 원재료):
  eqs_v3_panels_2021_2025.json       5개년 원본 재무 패널 2,683개 (raw)
  eqs_v3_scores_2021_2025.json       일반기업 EQS(M1~M5) 2,683개
  financial_feqs_scores_2021_2025.json  금융업 F-EQS(F1~F5) 118개
출력: integration/dossier/data/firm_<ticker>.json (전체 상장사, 기존 48개 포함 덮어씀)

알려진 단순화(이번 1단계 범위):
  - industry.sector 라벨은 KSIC 코드 그대로("KSIC 264") — 한글 업종명 매핑 테이블 미확보.
  - industry.averages/members는 KSIC 앞 3자리로 그룹핑한 "표시용" 참고치다.
    실제 EQS 점수 산출에 쓰인 정식 동료집단 위계(3자리→2자리→전체, 표본<20 시 확장)와는
    다를 수 있다 — 점수 자체는 GPU 산출 원본을 그대로 쓰므로 정확하지만, 이 industry 블록은
    "비교용 참고 화면"일 뿐 점수 계산에 관여하지 않는다.

실행 (repo 루트에서)::
    python integration/dossier/build_full_market_firm_json.py
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from collections import defaultdict
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _ROOT)

from modules.financial.eqs.types import FirmPanel, FirmYear  # noqa: E402
from modules.financial.translator.ratios import compute_ratios, LABELS as RATIO_LABELS  # noqa: E402
from modules.financial.translator.highlights import extract_highlights  # noqa: E402
from modules.financial.translator.translate import translate_all  # noqa: E402
from modules.financial.glossary import GLOSSARY  # noqa: E402

_UNIVERSE_DIR = os.path.join(_ROOT, "modules", "financial", "data", "universe")
_PANELS_PATH = os.path.join(_UNIVERSE_DIR, "eqs_v3_panels_2021_2025.json")
_EQS_SCORES_PATH = os.path.join(_UNIVERSE_DIR, "eqs_v3_scores_2021_2025.json")
_FEQS_SCORES_PATH = os.path.join(_UNIVERSE_DIR, "financial_feqs_scores_2021_2025.json")
_MASTER_PATH = os.path.join(_HERE, "data", "company_master.json")
_OUT_DIR = os.path.join(_HERE, "data")

_RATIO_KEYS = ("gross_margin", "operating_margin", "net_margin", "roe", "roa")


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def _panel_from_raw(row: dict) -> FirmPanel:
    years = [
        FirmYear(**{k: v for k, v in y.items() if k in FirmYear.__dataclass_fields__})
        for y in row.get("years", [])
    ]
    return FirmPanel(
        corp_code=row["corp_code"],
        corp_name=row.get("corp_name"),
        industry_code=row.get("industry_code"),
        years=years,
    )


def _ksic_group(industry_code: str | None) -> str | None:
    if not industry_code:
        return None
    return industry_code[:3]


def build() -> dict[str, dict]:
    panels_raw = _load_json(_PANELS_PATH)["panels"]
    eqs_scores = {r["corp_code"]: r for r in _load_json(_EQS_SCORES_PATH)["results"]}
    feqs_scores = {r["corp_code"]: r for r in _load_json(_FEQS_SCORES_PATH)["results"]}
    master = _load_json(_MASTER_PATH)
    ticker_by_corp = {c["corp_code"]: c["ticker"] for c in master["companies"]}

    panels: dict[str, FirmPanel] = {}
    for row in panels_raw:
        panels[row["corp_code"]] = _panel_from_raw(row)

    # 1차 통과: 회사별 최신연도 ratios 계산 (peer 평균 산출에 필요)
    latest_ratios: dict[str, dict] = {}
    for corp_code, panel in panels.items():
        latest = panel.latest()
        if latest is None:
            continue
        latest_ratios[corp_code] = compute_ratios(latest).as_dict()

    # KSIC 앞 3자리 그룹핑 → 표시용 동료 평균 (점수 계산엔 미사용, 화면 참고치)
    group_members: dict[str, list[str]] = defaultdict(list)
    for corp_code, panel in panels.items():
        group = _ksic_group(panel.industry_code)
        if group and panel.corp_name:
            group_members[group].append(panel.corp_name)

    group_averages: dict[str, dict] = {}
    for corp_code, panel in panels.items():
        group = _ksic_group(panel.industry_code)
        if not group or group in group_averages:
            continue
        members_codes = [
            c for c, p in panels.items() if _ksic_group(p.industry_code) == group
        ]
        # 단순 평균은 극단치(예: 매출 대비 이상치 비율) 하나에도 크게 흔들린다.
        # 화면 참고치 목적이므로 중앙값(median)을 사용해 이상치 영향을 줄인다.
        samples: dict[str, list[float]] = {k: [] for k in _RATIO_KEYS}
        for mc in members_codes:
            r = latest_ratios.get(mc)
            if not r:
                continue
            for k in _RATIO_KEYS:
                if r.get(k) is not None:
                    samples[k].append(r[k])
        group_averages[group] = {
            k: (statistics.median(v) if v else None) for k, v in samples.items()
        }

    results: dict[str, dict] = {}
    skipped_no_ticker = 0
    for corp_code, panel in panels.items():
        ticker = ticker_by_corp.get(corp_code)
        if not ticker:
            skipped_no_ticker += 1
            continue

        is_financial = corp_code in feqs_scores
        score_row = feqs_scores.get(corp_code) if is_financial else eqs_scores.get(corp_code)
        if score_row is None:
            continue

        latest = panel.latest()
        ratios_values = latest_ratios.get(corp_code) or {k: None for k in _RATIO_KEYS}
        group = _ksic_group(panel.industry_code)

        years_payload = [
            {
                "year": y.year,
                "revenue": y.revenue,
                "cogs": y.cogs,
                "operating_income": y.operating_income,
                "net_income": y.net_income,
                "operating_cashflow": y.operating_cashflow,
                "investing_cashflow": y.investing_cashflow,
                "financing_cashflow": y.financing_cashflow,
                "total_assets": y.total_assets,
                "total_liabilities": y.total_liabilities,
                "total_equity": y.total_equity,
                "current_assets": y.current_assets,
                "current_liabilities": y.current_liabilities,
                "long_term_debt": y.long_term_debt,
            }
            for y in panel.years
        ]

        summary = translate_all(latest) if latest else []
        highlights = [
            {"severity": h.severity, "title": h.title, "message": h.message}
            for h in (extract_highlights(panel) if latest else [])
        ]

        glossary_keys = list(_RATIO_KEYS) + [
            "operating_cashflow",
            "investing_cashflow",
            "financing_cashflow",
            "total_assets",
            "total_liabilities",
            "total_equity",
            "current_assets",
            "current_liabilities",
        ]
        glossary_keys += [m["name"] for m in score_row.get("modules", [])]
        glossary = {
            k: GLOSSARY[k].as_dict() for k in dict.fromkeys(glossary_keys) if k in GLOSSARY
        }

        years_list = [y.year for y in panel.years]
        year_range = (
            f"{min(years_list)}~{max(years_list)} ({len(years_list)}년)"
            if years_list
            else "—"
        )
        total_val = score_row.get("total")

        payload = {
            "corp": {
                "name": panel.corp_name,
                "code": corp_code,
                "industry": panel.industry_code,
                "year_count": len(years_list),
            },
            "years": years_payload,
            "eqs": {
                "total": total_val,
                "grade": score_row.get("grade"),
                "excluded": score_row.get("excluded", []),
                "modules": score_row.get("modules", []),
                "method": score_row.get(
                    "method",
                    "feqs_v1_financial_peer_percentile_2021_2025"
                    if is_financial
                    else "eqs_v3_industry_percentile",
                ),
            },
            "ratios": {
                "year": latest.year if latest else None,
                "values": ratios_values,
                "labels": RATIO_LABELS,
            },
            "industry": {
                "sector": f"KSIC {group}" if group else None,
                "n_companies": len(group_members.get(group, [])) if group else 0,
                "averages": group_averages.get(group) if group else None,
                "members": group_members.get(group, [])[:50] if group else [],
            },
            "summary": summary,
            "highlights": highlights,
            "glossary": glossary,
            "_hdr": {
                "corp_name": panel.corp_name or "(이름 없음)",
                "corp_code": corp_code,
                "year_range": year_range,
                "total": str(total_val) if total_val is not None else "—",
                "grade": score_row.get("grade") or "F",
            },
        }
        results[ticker] = payload

    print(f"[info] corp_code에 매칭되는 ticker 없어 스킵: {skipped_no_ticker}")
    return results


def main() -> int:
    results = build()
    os.makedirs(_OUT_DIR, exist_ok=True)
    written = 0
    for ticker, payload in results.items():
        out_path = os.path.join(_OUT_DIR, f"firm_{ticker}.json")
        with open(out_path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, separators=(",", ":"))
        written += 1
    print(f"[done] firm_<ticker>.json {written}개 생성 -> {_OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
