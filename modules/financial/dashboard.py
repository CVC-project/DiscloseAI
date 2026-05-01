"""EQSResult + FirmPanel → 단일 HTML 대시보드 생성.

생성된 파일은 docs/prototype/financial_dashboard.html에 저장되며 더블클릭으로
브라우저에서 바로 열린다. 모든 데이터는 inline embed (file:// 환경에서 CORS
없이 동작). Chart.js만 CDN 로드.

사용:
    from modules.financial.collector import fetch_panel
    from modules.financial.eqs import compute_eqs
    from modules.financial.translator import translate_all, extract_highlights
    from modules.financial.dashboard import build_dashboard

    panel = fetch_panel("00126380", range(2021, 2026), corp_name="삼성전자")
    eqs = compute_eqs(panel)
    out = build_dashboard(panel, eqs, translate_all(panel.latest()),
                         extract_highlights(panel))
    print(out)  # 저장 경로
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Iterable, List, Optional

from .batch import FirmRecord, summarize
from .eqs.types import EQSResult, FirmPanel
from .glossary import GLOSSARY
from .industry_groups import get_sector, load_sector_stats
from .translator.highlights import Highlight
from .translator.ratios import LABELS as RATIO_LABELS, compute_ratios

_DASHBOARD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs", "prototype"
)


def _firm_year_to_dict(y) -> dict:
    return {
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


def _industry_payload(corp_name: Optional[str]) -> Optional[dict]:
    """회사명으로 섹터 + 섹터 평균 비율 로드. 데이터 없으면 None."""
    if not corp_name:
        return None
    sector = get_sector(corp_name)
    if not sector:
        return None
    stats = load_sector_stats()
    if sector not in stats:
        return None
    s = stats[sector]
    return {
        "sector": sector,
        "n_companies": s.n_companies,
        "averages": {
            "gross_margin": s.avg_gross_margin,
            "operating_margin": s.avg_operating_margin,
            "net_margin": s.avg_net_margin,
            "roe": s.avg_roe,
            "roa": s.avg_roa,
        },
        "members": s.members,
    }


def _serialize(
    panel: FirmPanel,
    eqs: EQSResult,
    summary: List[str],
    highlights: Iterable[Highlight],
) -> dict:
    latest = panel.latest()
    ratios = (
        compute_ratios(latest).as_dict() if latest else {k: None for k in RATIO_LABELS}
    )
    return {
        "corp": {
            "name": panel.corp_name or "(이름 없음)",
            "code": panel.corp_code,
            "industry": panel.industry_code,
            "year_count": len(panel.years),
        },
        "years": [_firm_year_to_dict(y) for y in panel.years],
        "eqs": {
            "total": eqs.total,
            "grade": eqs.grade,
            "excluded": eqs.excluded,
            "modules": [
                {"name": m.name, "score": m.score, "raw": m.raw, "note": m.note}
                for m in eqs.modules
            ],
        },
        "ratios": {
            "year": latest.year if latest else None,
            "values": ratios,
            "labels": RATIO_LABELS,
        },
        "industry": _industry_payload(panel.corp_name),
        "summary": summary,
        "highlights": [asdict(h) for h in highlights],
        "glossary": {k: v.as_dict() for k, v in GLOSSARY.items()},
    }


_HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>DiscloseAI — {corp_name} 이익 해부</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #060814;
    --panel: rgba(15, 23, 42, 0.55);
    --panel-solid: #0f172a;
    --border: rgba(99, 102, 241, 0.22);
    --border-strong: rgba(99, 102, 241, 0.45);
    --text: #e2e8f0;
    --muted: #94a3b8;
    --good: #4ade80;
    --warn: #fbbf24;
    --bad: #f87171;
    --accent: #4da6ff;
    --accent2: #a78bfa;
    --nebula: #c084fc;
  }}
  * {{ box-sizing: border-box; }}
  /* 갤럭시 배경 — 깊은 공간 + 강한 nebula + 은하수 대각선 sweep */
  body {{
    margin: 0; padding: 24px;
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Malgun Gothic", sans-serif;
    line-height: 1.5;
    min-height: 100vh;
    background:
      /* 큰 nebula 구름 4개 — 인디고·마젠타·시안·골드 */
      radial-gradient(ellipse 55% 45% at 15% 18%, rgba(124, 108, 240, 0.42), transparent 60%),
      radial-gradient(ellipse 60% 50% at 88% 75%, rgba(244, 114, 182, 0.30), transparent 65%),
      radial-gradient(ellipse 45% 38% at 50% 100%, rgba(34, 211, 238, 0.22), transparent 65%),
      radial-gradient(ellipse 28% 22% at 95% 8%, rgba(251, 191, 36, 0.15), transparent 70%),
      /* 은하수 대각선 — 보라색 옅은 띠 */
      linear-gradient(135deg, transparent 28%, rgba(167, 139, 250, 0.08) 42%, rgba(196, 181, 253, 0.14) 50%, rgba(167, 139, 250, 0.08) 58%, transparent 72%),
      var(--bg);
    background-attachment: fixed;
    position: relative;
    overflow-x: hidden;
  }}
  /* 별빛 레이어 1 — 30개+ 점, 다양한 크기, 슬로우 트윙클 */
  body::before {{
    content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image:
      /* 큰 별 (밝은) */
      radial-gradient(2.2px 2.2px at 7% 11%, #fff, transparent 55%),
      radial-gradient(2px 2px at 28% 83%, #fff, transparent 55%),
      radial-gradient(2.4px 2.4px at 52% 31%, #c4b5fd, transparent 55%),
      radial-gradient(2px 2px at 73% 60%, #fff, transparent 55%),
      radial-gradient(2.2px 2.2px at 91% 17%, #fbcfe8, transparent 55%),
      radial-gradient(2px 2px at 11% 71%, #93c5fd, transparent 55%),
      /* 중간 별 */
      radial-gradient(1.4px 1.4px at 18% 28%, #ffffffcc, transparent 60%),
      radial-gradient(1.4px 1.4px at 33% 12%, #ffffffaa, transparent 60%),
      radial-gradient(1.5px 1.5px at 41% 56%, #c4b5fdcc, transparent 60%),
      radial-gradient(1.4px 1.4px at 47% 89%, #ffffffaa, transparent 60%),
      radial-gradient(1.5px 1.5px at 62% 8%, #93c5fdcc, transparent 60%),
      radial-gradient(1.4px 1.4px at 68% 38%, #ffffffaa, transparent 60%),
      radial-gradient(1.5px 1.5px at 79% 75%, #fbcfe8cc, transparent 60%),
      radial-gradient(1.4px 1.4px at 85% 48%, #ffffffaa, transparent 60%),
      radial-gradient(1.4px 1.4px at 96% 64%, #ffffffaa, transparent 60%),
      /* 작은 별 다수 */
      radial-gradient(1px 1px at 4% 35%, #ffffff88, transparent 65%),
      radial-gradient(1px 1px at 14% 91%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 21% 47%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 26% 22%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 36% 75%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 43% 18%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 49% 50%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 55% 73%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 58% 24%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 65% 92%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 71% 16%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 75% 45%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 81% 24%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 88% 81%, #ffffff77, transparent 65%),
      radial-gradient(1px 1px at 94% 39%, #ffffff77, transparent 65%);
    animation: starsTwinkle 7s ease-in-out infinite alternate;
  }}
  @keyframes starsTwinkle {{
    0%   {{ opacity: 0.65; }}
    50%  {{ opacity: 1.0; }}
    100% {{ opacity: 0.5; }}
  }}
  /* 패널의 cosmic 글로우 가로 라인 (헤더 위 장식) */
  .container::before {{
    content: ''; display: block; height: 1px; margin: 0 auto 18px;
    background: linear-gradient(90deg, transparent, var(--accent2), var(--accent), transparent);
    opacity: 0.6;
  }}
  /* === 코스믹 장식: 떠다니는 행성 + 슈팅 스타 === */
  .cosmic-decor {{ position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }}
  .planet {{ position: absolute; opacity: 0.85; filter: drop-shadow(0 0 18px rgba(167,139,250,0.30)); }}
  .planet-1 {{ top: 5%; right: 4%; width: 140px; height: 120px; animation: floatA 22s ease-in-out infinite; }}
  .planet-2 {{ bottom: 7%; left: 3%; width: 100px; height: 100px; animation: floatB 28s ease-in-out infinite; }}
  .planet-3 {{ top: 52%; right: 7%; width: 60px; height: 60px; animation: floatA 25s ease-in-out infinite; opacity: 0.7; }}
  @keyframes floatA {{
    0%, 100% {{ transform: translateY(0) rotate(0); }}
    50%      {{ transform: translateY(-14px) rotate(2deg); }}
  }}
  @keyframes floatB {{
    0%, 100% {{ transform: translateY(0) rotate(0); }}
    50%      {{ transform: translateY(12px) rotate(-2deg); }}
  }}
  /* 슈팅 스타 — 사선 streak. 18초 주기로 한 번 가로지름 */
  .shooting-star {{
    position: absolute; top: 14%; left: -10%;
    width: 140px; height: 1.5px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.95) 60%, rgba(196,181,253,0.9) 90%, transparent);
    filter: drop-shadow(0 0 8px rgba(255,255,255,0.85));
    border-radius: 1px;
    transform: rotate(22deg);
    animation: shoot 14s linear infinite;
    opacity: 0;
  }}
  .shooting-star.delay {{ animation-delay: 7s; top: 38%; }}
  @keyframes shoot {{
    0%  {{ opacity: 0; transform: translate(0, 0) rotate(22deg); }}
    2%  {{ opacity: 1; }}
    9%  {{ opacity: 1; transform: translate(110vw, 45vh) rotate(22deg); }}
    10% {{ opacity: 0; transform: translate(110vw, 45vh) rotate(22deg); }}
    100%{{ opacity: 0; transform: translate(110vw, 45vh) rotate(22deg); }}
  }}
  /* 헤일로가 있는 밝은 별 — 코어 + 부드러운 후광 */
  body::after {{
    content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image:
      radial-gradient(4px 4px at 13% 24%, #fff 0%, rgba(255,255,255,0.4) 25%, transparent 70%),
      radial-gradient(4.5px 4.5px at 76% 13%, #c4b5fd 0%, rgba(196,181,253,0.4) 25%, transparent 70%),
      radial-gradient(5px 5px at 39% 86%, #93c5fd 0%, rgba(147,197,253,0.35) 25%, transparent 70%),
      radial-gradient(4px 4px at 89% 67%, #fbcfe8 0%, rgba(251,207,232,0.35) 25%, transparent 70%),
      radial-gradient(4px 4px at 6% 64%, #fde68a 0%, rgba(253,230,138,0.3) 25%, transparent 70%);
    animation: starsTwinkle 9s ease-in-out infinite alternate-reverse;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; position: relative; z-index: 1; }}
  /* 헤더 — 코스믹 그라데이션 라인 + 회사명 글로우 */
  header {{
    display: flex; justify-content: space-between; align-items: flex-end;
    padding-bottom: 16px; margin-bottom: 24px;
    border-bottom: 1px solid transparent;
    border-image: linear-gradient(90deg, transparent, var(--accent2), var(--accent), transparent) 1;
  }}
  header h1 {{
    margin: 0; font-size: 30px; letter-spacing: -0.02em;
    background: linear-gradient(135deg, #cbd5e1, var(--accent), var(--nebula));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 36px rgba(77,166,255,0.18);
  }}
  header .meta {{ color: var(--muted); font-size: 14px; }}
  .grid {{ display: grid; gap: 16px; margin-bottom: 16px; }}
  .grid-2 {{ grid-template-columns: 1fr 1fr; }}
  .grid-3 {{ grid-template-columns: 1fr 1fr 1fr; }}
  /* 패널 — 글래스(반투명+블러) + 인디고 글로우 보더 + 미세 코스믹 그라디언트 */
  .panel {{
    background:
      linear-gradient(135deg, rgba(167,139,250,0.04), rgba(77,166,255,0.04) 60%, rgba(244,114,182,0.03)),
      var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px; padding: 20px;
    backdrop-filter: blur(12px) saturate(1.3);
    -webkit-backdrop-filter: blur(12px) saturate(1.3);
    box-shadow:
      0 1px 0 rgba(255,255,255,0.06) inset,
      0 0 0 1px rgba(167,139,250,0.08) inset,
      0 18px 40px rgba(0,0,0,0.4),
      0 0 24px rgba(77,166,255,0.06);
    transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
    position: relative;
  }}
  .panel:hover {{
    border-color: var(--border-strong);
    box-shadow:
      0 1px 0 rgba(255,255,255,0.08) inset,
      0 0 0 1px rgba(167,139,250,0.15) inset,
      0 22px 50px rgba(77,166,255,0.18),
      0 0 32px rgba(167,139,250,0.18);
  }}
  .panel h2 {{
    margin: 0 0 12px; font-size: 16px;
    color: var(--text); font-weight: 600; letter-spacing: 0.01em;
  }}
  .score-big {{
    font-size: 76px; font-weight: 800; line-height: 1;
    background: linear-gradient(135deg, var(--accent), var(--accent2), var(--nebula));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 40px rgba(167,139,250,0.25);
    letter-spacing: -0.03em;
  }}
  .grade {{
    display: inline-block; padding: 4px 16px; border-radius: 999px;
    font-weight: 700; font-size: 18px; margin-left: 12px;
  }}
  .grade-A {{ background: #16a34a; color: white; }}
  .grade-B {{ background: #65a30d; color: white; }}
  .grade-C {{ background: #ca8a04; color: white; }}
  .grade-D {{ background: #ea580c; color: white; }}
  .grade-F {{ background: #dc2626; color: white; }}
  .module-list {{ list-style: none; padding: 0; margin: 16px 0 0; }}
  .module-list li {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px solid var(--border);
  }}
  .module-list li:last-child {{ border-bottom: none; }}
  .module-name {{ color: var(--muted); font-size: 13px; }}
  .module-score {{ font-weight: 700; font-size: 18px; }}
  .summary-line {{
    background: rgba(99, 102, 241, 0.1); border-left: 3px solid var(--accent);
    padding: 12px 16px; border-radius: 4px; margin-bottom: 8px;
  }}
  .highlight-card {{
    border-left: 4px solid var(--border);
    padding: 12px 16px; margin-bottom: 8px;
    background: rgba(0,0,0,0.2); border-radius: 4px;
  }}
  .highlight-card.sev-high {{ border-left-color: var(--bad); }}
  .highlight-card.sev-mid {{ border-left-color: var(--warn); }}
  .highlight-card.sev-low {{ border-left-color: var(--good); }}
  .highlight-card .title {{ font-weight: 700; margin-bottom: 4px; }}
  .highlight-card .meta {{ font-size: 12px; color: var(--muted); margin-left: 8px; }}
  .chart-wrap {{ position: relative; height: 280px; }}
  .chart-wrap.radar {{ height: 380px; }}
  .chart-wrap canvas {{ display: block !important; width: 100% !important; height: 100% !important; }}
  .ratios-list {{ margin: 0; padding: 0; }}
  .ratio-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid var(--border);
  }}
  .ratio-row:last-child {{ border-bottom: none; }}
  .ratio-name {{ flex: 0 0 130px; color: var(--muted); font-size: 13px; }}
  .ratio-bar-wrap {{
    flex: 1; height: 8px; background: rgba(148,163,184,0.15);
    border-radius: 4px; overflow: hidden; position: relative;
  }}
  .ratio-bar-fill {{ height: 100%; transition: width 0.3s; border-radius: 4px; }}
  .ratio-bar-fill.positive {{ background: linear-gradient(90deg, var(--accent), #8b5cf6); }}
  .ratio-bar-fill.negative {{ background: var(--bad); }}
  .ratio-value {{
    flex: 0 0 90px; text-align: right; font-weight: 600; font-size: 16px;
  }}
  .ratio-value.na {{ color: var(--muted); font-weight: 400; font-size: 13px; }}
  .stmt-table {{
    width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px;
  }}
  .stmt-table th, .stmt-table td {{
    padding: 10px 8px; border-bottom: 1px solid var(--border); text-align: right;
  }}
  .stmt-table th:first-child, .stmt-table td:first-child {{
    text-align: left; color: var(--muted); font-weight: 500;
  }}
  .stmt-table thead th {{
    color: var(--muted); font-weight: 500; font-size: 12px;
    border-bottom: 2px solid var(--border);
  }}
  .stmt-table td {{ font-variant-numeric: tabular-nums; }}
  .stmt-table tr.highlight-row td {{
    font-weight: 700; background: rgba(99,102,241,0.08);
  }}
  .stmt-table td.negative {{ color: var(--bad); }}
  .industry-row {{
    display: grid; grid-template-columns: 130px 1fr 90px 90px 90px;
    gap: 12px; align-items: center;
    padding: 10px 0; border-bottom: 1px solid var(--border);
    font-size: 14px;
  }}
  .industry-row:last-child {{ border-bottom: none; }}
  .industry-row .ind-label {{ color: var(--muted); }}
  .industry-row .ind-bar-wrap {{
    position: relative; height: 24px; background: rgba(148,163,184,0.08);
    border-radius: 4px; overflow: hidden;
  }}
  .industry-row .ind-bar-mine {{
    position: absolute; left: 0; top: 0; height: 100%;
    background: linear-gradient(90deg, var(--accent), #8b5cf6); opacity: 0.85;
  }}
  .industry-row .ind-bar-avg {{
    position: absolute; top: 0; height: 100%; width: 2px;
    background: var(--warn);
  }}
  .industry-row .ind-val {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .industry-row .ind-val.mine {{ font-weight: 600; }}
  .industry-row .ind-val.avg {{ color: var(--muted); }}
  .industry-row .ind-diff {{ text-align: right; font-weight: 600; }}
  .industry-row .ind-diff.up {{ color: var(--good); }}
  .industry-row .ind-diff.down {{ color: var(--bad); }}
  .industry-row .ind-diff.na {{ color: var(--muted); font-weight: 400; }}
  .industry-head {{
    display: grid; grid-template-columns: 130px 1fr 90px 90px 90px;
    gap: 12px; padding: 8px 0; border-bottom: 2px solid var(--border);
    color: var(--muted); font-size: 12px;
  }}
  .industry-head div:nth-child(3), .industry-head div:nth-child(4), .industry-head div:nth-child(5) {{
    text-align: right;
  }}
  .help {{
    display: inline-block; margin-left: 4px; cursor: help;
    color: var(--muted); font-size: 10px;
    position: relative; vertical-align: middle;
    width: 14px; height: 14px; line-height: 14px;
    text-align: center; border-radius: 50%;
    background: rgba(148,163,184,0.15);
    font-weight: 400; font-style: normal;
  }}
  .help:hover {{ background: var(--accent); color: white; }}
  .help .help-text {{
    display: none; position: absolute;
    left: 0; bottom: calc(100% + 10px);
    width: 340px; padding: 0;
    background: #0b1220; color: var(--text);
    border: 1px solid var(--accent); border-radius: 8px;
    font-size: 12px; line-height: 1.55;
    z-index: 100; text-align: left;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    font-weight: 400; white-space: normal;
    overflow: hidden;
  }}
  .help:hover .help-text {{ display: block; }}
  .help-title {{
    font-size: 13px; font-weight: 700; color: var(--text);
    background: linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.15));
    padding: 10px 14px;
    border-bottom: 1px solid rgba(99,102,241,0.3);
  }}
  .help-section {{
    padding: 8px 14px;
    border-bottom: 1px solid rgba(51, 65, 85, 0.4);
  }}
  .help-section:last-child {{ border-bottom: none; }}
  .help-section-label {{
    font-size: 10px; font-weight: 700;
    color: var(--warn); letter-spacing: 0.5px;
    margin-bottom: 4px; text-transform: uppercase;
  }}
  .help-section-body {{
    font-size: 12px; line-height: 1.55; color: var(--text);
  }}
  /* 왼쪽 끝 근처의 툴팁은 왼쪽이 아닌 오른쪽 정렬 */
  .industry-row .help .help-text,
  .ratio-row .help .help-text,
  .stmt-table .help .help-text {{
    left: auto; right: auto;
  }}
  footer {{
    margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border);
    color: var(--muted); font-size: 12px;
  }}
  .disclaimer {{
    background: rgba(234, 179, 8, 0.08); border: 1px solid rgba(234, 179, 8, 0.3);
    padding: 12px 16px; border-radius: 8px; margin-top: 16px; font-size: 13px;
  }}
</style>
</head>
<body>
<!-- 갤럭시 장식: 떠다니는 행성 + 슈팅 스타 (배경 레이어, 콘텐츠와 무관) -->
<div class="cosmic-decor" aria-hidden="true">
  <!-- Planet 1: 시안/인디고 가스자이언트 with ring (top-right) -->
  <svg class="planet planet-1" viewBox="0 0 140 120" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <radialGradient id="pg1" cx="38%" cy="38%">
        <stop offset="0%" stop-color="#bae6fd"/>
        <stop offset="55%" stop-color="#3b82f6"/>
        <stop offset="100%" stop-color="#0c1b3a"/>
      </radialGradient>
      <linearGradient id="pg1ring" x1="0%" y1="50%" x2="100%" y2="50%">
        <stop offset="0%" stop-color="#a78bfa" stop-opacity="0.05"/>
        <stop offset="50%" stop-color="#a78bfa" stop-opacity="0.55"/>
        <stop offset="100%" stop-color="#a78bfa" stop-opacity="0.05"/>
      </linearGradient>
    </defs>
    <ellipse cx="70" cy="60" rx="62" ry="9" fill="none" stroke="url(#pg1ring)" stroke-width="2.5" transform="rotate(-18 70 60)"/>
    <ellipse cx="70" cy="60" rx="62" ry="9" fill="none" stroke="#c4b5fd" stroke-opacity="0.15" stroke-width="6" transform="rotate(-18 70 60)"/>
    <circle cx="70" cy="60" r="28" fill="url(#pg1)"/>
    <circle cx="60" cy="52" r="5" fill="#bae6fd" opacity="0.35"/>
  </svg>
  <!-- Planet 2: 마젠타/보라 작은 행성 (bottom-left) -->
  <svg class="planet planet-2" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <radialGradient id="pg2" cx="36%" cy="36%">
        <stop offset="0%" stop-color="#fbcfe8"/>
        <stop offset="55%" stop-color="#c026d3"/>
        <stop offset="100%" stop-color="#3b0764"/>
      </radialGradient>
    </defs>
    <circle cx="50" cy="50" r="32" fill="url(#pg2)" filter="drop-shadow(0 0 18px rgba(192,38,211,0.45))"/>
    <ellipse cx="44" cy="42" rx="6" ry="4" fill="#fbcfe8" opacity="0.4"/>
  </svg>
  <!-- Planet 3: 골드/오렌지 작은 행성 with ring (mid-right) -->
  <svg class="planet planet-3" viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <radialGradient id="pg3" cx="35%" cy="35%">
        <stop offset="0%" stop-color="#fef3c7"/>
        <stop offset="55%" stop-color="#f59e0b"/>
        <stop offset="100%" stop-color="#451a03"/>
      </radialGradient>
    </defs>
    <ellipse cx="40" cy="40" rx="36" ry="6" fill="none" stroke="#fcd34d" stroke-opacity="0.45" stroke-width="1.6" transform="rotate(15 40 40)"/>
    <circle cx="40" cy="40" r="16" fill="url(#pg3)"/>
  </svg>
  <span class="shooting-star"></span>
  <span class="shooting-star delay"></span>
</div>
<div class="container">
  <header>
    <div>
      <h1>{corp_name} <span style="color:var(--muted);font-size:18px;">({corp_code})</span></h1>
      <div class="meta">DiscloseAI · 이익 해부 (Earnings Quality Score)</div>
    </div>
    <div style="text-align:right;">
      <div class="meta">분석 기간</div>
      <div style="font-size:18px;font-weight:600;">{year_range}</div>
    </div>
  </header>

  <div class="grid grid-2">
    <div class="panel">
      <h2>EQS 종합 점수</h2>
      <div>
        <span class="score-big">{total}</span>
        <span class="grade grade-{grade}">{grade}</span>
      </div>
      <ul class="module-list" id="moduleList"></ul>
    </div>

    <div class="panel">
      <h2>5개 모듈 프로파일</h2>
      <div class="chart-wrap radar"><canvas id="radar"></canvas></div>
    </div>
  </div>

  <div class="panel" style="margin-top:0;">
    <h2>💰 수익성 지표 <span style="color:var(--muted);font-weight:400;font-size:13px;" id="ratiosYear"></span></h2>
    <div class="ratios-list" id="ratiosList"></div>
  </div>

  <div class="panel" id="industryPanel" style="margin-top:16px; display:none;">
    <h2>🏭 업계 대비 <span style="color:var(--muted);font-weight:400;font-size:13px;" id="industryMeta"></span></h2>
    <div class="industry-head">
      <div>지표</div>
      <div>내 회사 vs 업계 평균</div>
      <div>내 회사</div>
      <div>업계 평균</div>
      <div>차이</div>
    </div>
    <div id="industryRows"></div>
  </div>

  <div class="panel" style="margin-top:16px;">
    <h2>매출 · 영업현금흐름 · 순이익 시계열</h2>
    <div class="chart-wrap" style="height:320px;"><canvas id="ts"></canvas></div>
  </div>

  <div class="panel" style="margin-top:16px;">
    <h2>📊 손익계산서 (최근 5년)</h2>
    <div class="summary-line" id="sumIncome"></div>
    <table class="stmt-table" id="incomeTable"></table>
  </div>

  <div class="panel" style="margin-top:16px;">
    <h2>🏛 재무상태표 (최근 5년)</h2>
    <div class="summary-line" id="sumBalance"></div>
    <table class="stmt-table" id="balanceTable"></table>
  </div>

  <div class="panel" style="margin-top:16px;">
    <h2>💵 현금흐름표 (최근 5년)</h2>
    <div class="summary-line" id="sumCash"></div>
    <table class="stmt-table" id="cashflowTable"></table>
  </div>

  <div class="panel" style="margin-top:16px;">
    <h2>⚡ 주목 포인트</h2>
    <div id="highlights"></div>
  </div>

  <footer>
    <div class="disclaimer">
      ⚠️ 본 분석은 과거 통계 기반 참고 정보입니다. 투자 조언이 아닙니다.
      EQS 점수는 K-IFRS 재무제표 자동 분석 결과로, 단일 지표만으로 투자 판단을 내리지 마세요.
    </div>
    <div style="margin-top:12px;">
      Powered by DART OpenAPI · DiscloseAI Financial Module · 분석 시점 데이터 기준
    </div>
  </footer>
</div>

<script>
const DATA = {data_json};

// 용어 설명 툴팁 헬퍼 — glossary에 있는 key만 ⓘ 출력 (섹션형 카드)
function helpIcon(key) {{
  const g = DATA.glossary && DATA.glossary[key];
  if (!g) return '';
  const sections = [];
  if (g.description) sections.push(['📖 개념', g.description]);
  if (g.how)         sections.push(['🧮 산출 방식', g.how]);
  if (g.benchmark)   sections.push(['📏 기준선', g.benchmark]);
  if (g.intuition)   sections.push(['💡 쉽게 말하면', g.intuition]);
  const body = sections.map(([lbl, txt]) =>
    `<div class="help-section"><div class="help-section-label">${{lbl}}</div><div class="help-section-body">${{txt}}</div></div>`
  ).join('');
  return `<span class="help">ⓘ<span class="help-text">
    <div class="help-title">${{g.label}}</div>${{body}}
  </span></span>`;
}}

// 모듈 점수 리스트
const moduleColors = {{
  M1: '#06b6d4', M2: '#8b5cf6', M3: '#22c55e', M4: '#eab308', M5: '#ef4444'
}};
const moduleLabels = {{
  M1: '현금이익률', M2: '매출 회수 건전성', M3: '부채 건전성',
  M4: '본업 안정성', M5: '자본 성장성'
}};

const ml = document.getElementById('moduleList');
DATA.eqs.modules.forEach(m => {{
  const li = document.createElement('li');
  const score = m.score === null ? '—' : m.score.toFixed(1);
  li.innerHTML = `
    <div>
      <span class="module-score" style="color:${{moduleColors[m.name]}}">${{score}}</span>
      <span class="module-name" style="margin-left:12px;">${{moduleLabels[m.name]}}${{helpIcon(m.name)}}</span>
    </div>
    <span class="module-name" style="font-size:11px;text-align:right;max-width:200px;">${{m.note}}</span>
  `;
  ml.appendChild(li);
}});

// 레이더 차트
new Chart(document.getElementById('radar'), {{
  type: 'radar',
  data: {{
    labels: DATA.eqs.modules.map(m => moduleLabels[m.name]),
    datasets: [{{
      label: 'EQS',
      data: DATA.eqs.modules.map(m => m.score || 0),
      backgroundColor: 'rgba(77, 166, 255, 0.22)',
      borderColor: '#4da6ff',
      borderWidth: 2,
      pointBackgroundColor: '#a78bfa',
      pointBorderColor: '#fff',
      pointHoverRadius: 6,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    layout: {{ padding: {{ top: 4, bottom: 4, left: 4, right: 4 }} }},
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      r: {{
        min: 0, max: 100,
        grid: {{ color: 'rgba(167, 139, 250, 0.18)' }},
        angleLines: {{ color: 'rgba(167, 139, 250, 0.22)' }},
        pointLabels: {{ color: '#e2e8f0', font: {{ size: 13 }} }},
        ticks: {{ color: '#94a3b8', backdropColor: 'transparent', stepSize: 25 }}
      }}
    }}
  }}
}});

// 수익성 지표 렌더링
// 막대바는 30%를 풀 게이지 기준 — 대부분 비율 지표가 30%면 우수 수준
const ratioRef = 30;
const rList = document.getElementById('ratiosList');
if (DATA.ratios.year !== null) {{
  document.getElementById('ratiosYear').textContent = `(${{DATA.ratios.year}}년 결산 기준)`;
}}
Object.entries(DATA.ratios.labels).forEach(([key, label]) => {{
  const v = DATA.ratios.values[key];
  const row = document.createElement('div');
  row.className = 'ratio-row';
  let valueHtml, barHtml;
  if (v === null || v === undefined) {{
    valueHtml = `<div class="ratio-value na">N/A</div>`;
    barHtml = `<div class="ratio-bar-wrap"></div>`;
  }} else {{
    const pct = Math.min(Math.abs(v) / ratioRef * 100, 100);
    const cls = v >= 0 ? 'positive' : 'negative';
    valueHtml = `<div class="ratio-value">${{v.toFixed(1)}}%</div>`;
    barHtml = `<div class="ratio-bar-wrap"><div class="ratio-bar-fill ${{cls}}" style="width:${{pct}}%"></div></div>`;
  }}
  row.innerHTML = `<div class="ratio-name">${{label}}${{helpIcon(key)}}</div>${{barHtml}}${{valueHtml}}`;
  rList.appendChild(row);
}});

// 업계 대비 렌더링
if (DATA.industry) {{
  document.getElementById('industryPanel').style.display = '';
  document.getElementById('industryMeta').textContent =
    `· ${{DATA.industry.sector}} (${{DATA.industry.n_companies}}개사 평균)`;
  const rowsDiv = document.getElementById('industryRows');
  // 막대 시각화 기준: 양쪽 값의 최대치 * 1.2
  Object.entries(DATA.ratios.labels).forEach(([key, label]) => {{
    const mine = DATA.ratios.values[key];
    const avg = DATA.industry.averages[key];
    const row = document.createElement('div');
    row.className = 'industry-row';
    let barHtml = '<div class="ind-bar-wrap"></div>';
    let diffHtml = '<div class="ind-diff na">—</div>';
    let mineHtml = '<div class="ind-val mine">—</div>';
    let avgHtml = '<div class="ind-val avg">—</div>';
    if (mine !== null && mine !== undefined) {{
      mineHtml = `<div class="ind-val mine">${{mine.toFixed(1)}}%</div>`;
    }}
    if (avg !== null && avg !== undefined) {{
      avgHtml = `<div class="ind-val avg">${{avg.toFixed(1)}}%</div>`;
    }}
    if (mine !== null && avg !== null && mine !== undefined && avg !== undefined) {{
      const maxRef = Math.max(Math.abs(mine), Math.abs(avg)) * 1.2 || 1;
      const mineW = Math.max(0, Math.min(100, mine / maxRef * 100));
      const avgW = avg / maxRef * 100;
      barHtml = `<div class="ind-bar-wrap">
        <div class="ind-bar-mine" style="width:${{mineW}}%"></div>
        <div class="ind-bar-avg" style="left:${{avgW}}%"></div>
      </div>`;
      const diff = mine - avg;
      const diffCls = diff >= 0 ? 'up' : 'down';
      const sign = diff >= 0 ? '+' : '';
      diffHtml = `<div class="ind-diff ${{diffCls}}">${{sign}}${{diff.toFixed(1)}}%p</div>`;
    }}
    row.innerHTML = `<div class="ind-label">${{label}}${{helpIcon(key)}}</div>${{barHtml}}${{mineHtml}}${{avgHtml}}${{diffHtml}}`;
    rowsDiv.appendChild(row);
  }});
}}

// 시계열
const yrs = DATA.years.map(y => y.year);
const toEok = v => v === null ? null : v / 1e8;  // 원 → 억원 (DART는 원 단위)
new Chart(document.getElementById('ts'), {{
  type: 'line',
  data: {{
    labels: yrs,
    datasets: [
      {{label: '매출', data: DATA.years.map(y => toEok(y.revenue)), borderColor: '#4da6ff', backgroundColor: 'rgba(77,166,255,0.08)', tension: 0.35, borderWidth: 2.2, pointBackgroundColor: '#4da6ff', pointRadius: 3, fill: true}},
      {{label: '영업현금흐름', data: DATA.years.map(y => toEok(y.operating_cashflow)), borderColor: '#34d399', backgroundColor: 'rgba(52,211,153,0.06)', tension: 0.35, borderWidth: 2.2, pointBackgroundColor: '#34d399', pointRadius: 3, fill: true}},
      {{label: '순이익', data: DATA.years.map(y => toEok(y.net_income)), borderColor: '#fbbf24', backgroundColor: 'rgba(251,191,36,0.06)', tension: 0.35, borderWidth: 2.2, pointBackgroundColor: '#fbbf24', pointRadius: 3, fill: true}},
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    layout: {{ padding: {{ top: 4, bottom: 4, left: 4, right: 8 }} }},
    plugins: {{ legend: {{ labels: {{ color: '#e2e8f0' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }},
      y: {{ ticks: {{ color: '#94a3b8', callback: v => (v/10000).toFixed(0) + '조' }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }}
    }}
  }}
}});

// 번역 3개
document.getElementById('sumIncome').textContent  = DATA.summary[0] || '';
document.getElementById('sumBalance').textContent = DATA.summary[1] || '';
document.getElementById('sumCash').textContent    = DATA.summary[2] || '';

// 재무제표 3종 표 렌더링
function formatMoney(v) {{
  if (v === null || v === undefined) return '—';
  const eok = v / 1e8;  // 원 → 억원
  if (Math.abs(eok) >= 10000) {{
    return (eok / 10000).toFixed(1) + '조';
  }}
  return Math.round(eok).toLocaleString('ko-KR') + '억';
}}

function renderStatementTable(tableId, rows, years) {{
  const table = document.getElementById(tableId);
  const yearHead = years.map(y => `<th>${{y}}</th>`).join('');
  let html = `<thead><tr><th>항목</th>${{yearHead}}</tr></thead><tbody>`;
  rows.forEach(row => {{
    const cells = row.values.map(v => {{
      const cls = (v !== null && v !== undefined && v < 0) ? 'negative' : '';
      return `<td class="${{cls}}">${{formatMoney(v)}}</td>`;
    }}).join('');
    const hClass = row.highlight ? 'highlight-row' : '';
    const info = row.key ? helpIcon(row.key) : '';
    html += `<tr class="${{hClass}}"><td>${{row.label}}${{info}}</td>${{cells}}</tr>`;
  }});
  html += '</tbody>';
  table.innerHTML = html;
}}

const stmtYears = DATA.years.map(y => y.year);

// 손익계산서
renderStatementTable('incomeTable', [
  {{label: '매출액', values: DATA.years.map(y => y.revenue)}},
  {{label: '매출원가', values: DATA.years.map(y => y.cogs)}},
  {{label: '매출총이익', values: DATA.years.map(y =>
    (y.revenue !== null && y.cogs !== null) ? y.revenue - y.cogs : null)}},
  {{label: '영업이익', values: DATA.years.map(y => y.operating_income), highlight: true}},
  {{label: '당기순이익', values: DATA.years.map(y => y.net_income), highlight: true}},
], stmtYears);

// 재무상태표
renderStatementTable('balanceTable', [
  {{label: '자산총계', key: 'total_assets', values: DATA.years.map(y => y.total_assets), highlight: true}},
  {{label: '　유동자산', key: 'current_assets', values: DATA.years.map(y => y.current_assets)}},
  {{label: '부채총계', key: 'total_liabilities', values: DATA.years.map(y => y.total_liabilities), highlight: true}},
  {{label: '　유동부채', key: 'current_liabilities', values: DATA.years.map(y => y.current_liabilities)}},
  {{label: '　비유동부채', values: DATA.years.map(y => y.long_term_debt)}},
  {{label: '자본총계', key: 'total_equity', values: DATA.years.map(y => y.total_equity), highlight: true}},
], stmtYears);

// 현금흐름표
renderStatementTable('cashflowTable', [
  {{label: '영업활동 CF', key: 'operating_cashflow', values: DATA.years.map(y => y.operating_cashflow), highlight: true}},
  {{label: '투자활동 CF', key: 'investing_cashflow', values: DATA.years.map(y => y.investing_cashflow)}},
  {{label: '재무활동 CF', key: 'financing_cashflow', values: DATA.years.map(y => y.financing_cashflow)}},
], stmtYears);

// Highlights
const hc = document.getElementById('highlights');
if (DATA.highlights.length === 0) {{
  hc.innerHTML = '<div class="meta">감지된 주목 포인트 없음 (정상 신호)</div>';
}}
DATA.highlights.forEach(h => {{
  const sev = h.severity >= 7 ? 'high' : h.severity >= 5 ? 'mid' : 'low';
  const div = document.createElement('div');
  div.className = `highlight-card sev-${{sev}}`;
  div.innerHTML = `<div class="title">${{h.title}} <span class="meta">severity ${{h.severity}}/10</span></div><div>${{h.message}}</div>`;
  hc.appendChild(div);
}});
</script>
</body>
</html>
"""


def build_dashboard(
    panel: FirmPanel,
    eqs: EQSResult,
    summary: List[str],
    highlights: List[Highlight],
    output_dir: Optional[str] = None,
    *,
    output_name: str = "financial_dashboard.html",
) -> str:
    """HTML 대시보드 생성. 저장 경로 반환.

    ``output_name``: 기본 ``financial_dashboard.html``. 통합 대시보드의
    기업분석 오버레이용으로 ticker별 ``firm_<ticker>.html`` 형태로 다수 생성
    가능 (자체완결형 — file:// 환경에서도 그대로 동작).
    """
    out_dir = output_dir or _DASHBOARD_DIR
    os.makedirs(out_dir, exist_ok=True)
    payload = _serialize(panel, eqs, summary, highlights)
    years_in_panel = [y.year for y in panel.years]
    year_range = (
        f"{min(years_in_panel)}~{max(years_in_panel)} ({len(years_in_panel)}년)"
        if years_in_panel
        else "—"
    )
    html = _HTML_TEMPLATE.format(
        corp_name=payload["corp"]["name"],
        corp_code=payload["corp"]["code"],
        year_range=year_range,
        total=eqs.total if eqs.total is not None else "—",
        grade=eqs.grade or "F",
        data_json=json.dumps(payload, ensure_ascii=False),
    )
    out_path = os.path.join(out_dir, output_name)
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(html)
    return out_path


# ---------------------------------------------------------------------------
# Ranking dashboard (다수 기업 비교)
# ---------------------------------------------------------------------------


def _record_row(r: FirmRecord) -> dict:
    """배치 1행 → 표 + 차트용 dict.

    ``module_notes``: 각 모듈의 산출 사유·해석 노트. UI 툴팁 노출용.
    - 정상 산출: ``'M=-1.5 (정상)'`` 등 원시 지표 + 해석
    - 결측 None: 왜 계산 못 했는지 사유 (예: ``'매출원가 없음(서비스형)'``)
    - 업종 제외: ``'금융업 제외'`` — eqs.modules에는 없지만 excluded에 기록됨
    """
    all_mods = ("M1", "M2", "M3", "M4", "M5")
    common = {
        "name": r.display_name,
        "code": r.corp.stock_code if r.corp else None,
        "industry_code": r.industry_code,
        "is_financial": r.industry_code is not None
        and r.industry_code.startswith(("064", "065", "066", "067")),
        "market_cap": r.market_cap,
        "year_count": len(r.panel.years) if r.panel else 0,
        "dart_url": r.dart_url,
    }
    if r.eqs is None:
        err = r.error or "분석 실패"
        return {
            **common,
            "total": None,
            "grade": None,
            "modules": {m: None for m in all_mods},
            "module_notes": {m: err for m in all_mods},
            "error": r.error,
        }
    mod_map = {m.name: (m.score, m.note) for m in r.eqs.modules}
    excluded = set(r.eqs.excluded or [])
    # 업종별로 제외 사유 메시지 분기 (금융·지주 혼동 방지)
    ind = r.industry_code or ""
    if ind.startswith(("064", "065", "066", "067")):
        excluded_note = "금융업 제외 — 해당 모듈 부적합"
    elif ind.startswith("100"):
        excluded_note = "지주·투자회사 제외 — 단일기업 fallback 부적합"
    else:
        excluded_note = "제외 — 해당 모듈 부적합"
    modules: dict = {}
    notes: dict = {}
    for m in all_mods:
        if m in mod_map:
            score, note = mod_map[m]
            modules[m] = score
            notes[m] = note or ""
        elif m in excluded:
            modules[m] = None
            notes[m] = excluded_note
        else:
            modules[m] = None
            notes[m] = ""
    return {
        **common,
        "total": r.eqs.total,
        "grade": r.eqs.grade,
        "modules": modules,
        "module_notes": notes,
        "error": None,
    }


_RANKING_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>DiscloseAI — KOSPI 50 EQS 비교</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f172a; --panel: #1e293b; --border: #334155;
    --text: #e2e8f0; --muted: #94a3b8;
    --accent: #6366f1;
    --A: #16a34a; --B: #65a30d; --C: #ca8a04; --D: #ea580c; --F: #dc2626;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 24px; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Malgun Gothic", sans-serif; }}
  .container {{ max-width: 1400px; margin: 0 auto; }}
  header {{ display: flex; justify-content: space-between; align-items: flex-end;
    border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }}
  header h1 {{ margin: 0; font-size: 28px; }}
  header .meta {{ color: var(--muted); font-size: 14px; }}
  .stat-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }}
  .stat {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; }}
  .stat .num {{ font-size: 28px; font-weight: 700; }}
  .stat .lbl {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
  .grid {{ display: grid; gap: 16px; margin-bottom: 16px; }}
  .grid-2 {{ grid-template-columns: 2fr 1fr; }}
  .panel {{ background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px; }}
  .panel h2 {{ margin: 0 0 12px; font-size: 16px; color: var(--muted); font-weight: 500; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 6px; color: var(--muted); font-weight: 500;
    border-bottom: 1px solid var(--border); cursor: pointer; user-select: none; }}
  th:hover {{ color: var(--text); }}
  th.sort-asc::after {{ content: " ▲"; color: var(--accent); }}
  th.sort-desc::after {{ content: " ▼"; color: var(--accent); }}
  th {{ position: relative; }}
  th .th-tip {{
    display: none; position: absolute;
    left: 50%; top: calc(100% + 10px);
    transform: translateX(-50%);
    width: 300px; padding: 0;
    background: #0b1220; color: var(--text);
    border: 1px solid var(--accent); border-radius: 8px;
    font-size: 12px; line-height: 1.55;
    z-index: 200; text-align: left;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    font-weight: 400; white-space: normal;
    overflow: hidden; cursor: default;
  }}
  th:hover .th-tip {{ display: block; }}
  #ranking th:first-child .th-tip {{ left: 0; transform: none; }}
  #ranking th:last-child  .th-tip {{ left: auto; right: 0; transform: none; }}
  .th-tip-title {{
    font-size: 13px; font-weight: 700; color: var(--text);
    background: linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.15));
    padding: 10px 14px;
    border-bottom: 1px solid rgba(99,102,241,0.3);
  }}
  .th-tip-section {{
    padding: 8px 14px;
    border-bottom: 1px solid rgba(51, 65, 85, 0.4);
  }}
  .th-tip-section:last-child {{ border-bottom: none; }}
  .th-tip-label {{
    font-size: 10px; font-weight: 700;
    color: var(--warn); letter-spacing: 0.5px;
    margin-bottom: 4px; text-transform: uppercase;
  }}
  .th-tip-body {{
    font-size: 12px; line-height: 1.55; color: var(--text);
  }}
  td {{ padding: 6px; border-bottom: 1px solid rgba(51, 65, 85, 0.4); }}
  tr:hover td {{ background: rgba(99, 102, 241, 0.06); }}
  .grade-pill {{ display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 11px; font-weight: 700; color: white; min-width: 20px; text-align: center; }}
  .grade-A {{ background: var(--A); }} .grade-B {{ background: var(--B); }}
  .grade-C {{ background: var(--C); }} .grade-D {{ background: var(--D); }}
  .grade-F {{ background: var(--F); }}
  .num-cell {{ font-variant-numeric: tabular-nums; text-align: right; }}
  .total-cell {{ font-weight: 700; }}
  .err-row td {{ color: var(--muted); font-style: italic; }}
  .module-bar {{ display: inline-block; height: 6px; background: var(--accent);
    border-radius: 2px; vertical-align: middle; margin-right: 4px; }}
  .chart-wrap {{ position: relative; height: 240px; }}
  footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border);
    color: var(--muted); font-size: 12px; }}
  .disclaimer {{ background: rgba(234, 179, 8, 0.08);
    border: 1px solid rgba(234, 179, 8, 0.3); padding: 12px 16px; border-radius: 8px;
    margin-top: 16px; font-size: 13px; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1>KOSPI 50 — EQS 비교 분석</h1>
      <div class="meta">DiscloseAI · {analyzed_at} 분석</div>
    </div>
    <div style="text-align:right;">
      <div class="meta">분석 윈도우</div>
      <div style="font-size:18px;font-weight:600;">{year_range}</div>
    </div>
  </header>

  <div class="stat-row">
    <div class="stat"><div class="num">{success_count}<span style="color:var(--muted);font-size:18px;"> / {total_count}</span></div><div class="lbl">분석 성공</div></div>
    <div class="stat"><div class="num">{avg_total}</div><div class="lbl">평균 EQS</div></div>
    <div class="stat"><div class="num" style="color:var(--A);">{a_count}</div><div class="lbl">A등급</div></div>
    <div class="stat"><div class="num" style="color:var(--F);">{f_count}</div><div class="lbl">F등급</div></div>
  </div>

  <div class="grid grid-2">
    <div class="panel">
      <h2>랭킹 (컬럼 헤더에 마우스를 올리면 설명, 클릭하면 정렬)</h2>
      <div style="overflow:visible;">
        <table id="ranking">
          <thead>
            <tr>
              <th data-key="rank">#</th>
              <th data-key="name">기업</th>
              <th class="num-cell" data-key="market_cap">시총</th>
              <th class="num-cell" data-key="total">평균점수</th>
              <th data-key="grade">등급</th>
              <th class="num-cell" data-key="m1">현금이익률</th>
              <th class="num-cell" data-key="m2">매출 회수</th>
              <th class="num-cell" data-key="m3">부채 건전성</th>
              <th class="num-cell" data-key="m4">본업 안정성</th>
              <th class="num-cell" data-key="m5">자본 성장성</th>
              <th class="num-cell" data-key="years">년수</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <div>
      <div class="panel">
        <h2>등급 분포</h2>
        <div class="chart-wrap"><canvas id="gradeChart"></canvas></div>
      </div>
      <div class="panel" style="margin-top:16px;">
        <h2>모듈별 평균 점수</h2>
        <div class="chart-wrap"><canvas id="moduleChart"></canvas></div>
      </div>
    </div>
  </div>

  <div class="panel">
    <h2>평균점수 분포</h2>
    <div class="chart-wrap" style="height:200px;"><canvas id="histChart"></canvas></div>
  </div>

  <footer>
    <div class="disclaimer">
      ⚠️ 본 분석은 K-IFRS 재무제표 기반 과거 통계 정보입니다. 투자 조언이 아닙니다.
      금융지주사 등 일부 기업은 DART 과거 사업보고서 누락으로 단축 윈도우 기준입니다.
    </div>
    <div style="margin-top:8px; font-size:12px; color:var(--muted);">
      * 표시 = 대체 모델(fallback) 적용. 금융업·지주사·서비스업 등 표준 모델이 부적합한 종목에 업종 특성에 맞는 별도 산식을 사용했습니다. 마우스를 올리면 상세 사유를 확인할 수 있습니다.
    </div>
    <div style="margin-top:12px;">
      Powered by DART OpenAPI · DiscloseAI Financial Module
    </div>
  </footer>
</div>

<script>
const DATA = {data_json};
const MODULE_COLORS = {{M1:'#06b6d4', M2:'#8b5cf6', M3:'#22c55e', M4:'#eab308', M5:'#ef4444'}};

// 컬럼 헤더 툴팁 — 주린이 친화 설명. M1~M5는 glossary에서, 나머지는 EXTRA_TOOLTIPS에서.
const EXTRA_TOOLTIPS = {{
  rank: {{
    label: '#',
    description: '현재 정렬 기준에 따른 순위. 기본 정렬은 시총 내림차순.',
    intuition: '컬럼 헤더(시총·평균점수 등)를 클릭하면 해당 기준으로 다시 정렬됩니다.',
  }},
  name: {{
    label: '기업명',
    description: '회사 이름. 행을 클릭하면 해당 회사의 상세 사업보고서(DART)가 새 창에서 열립니다.',
    intuition: '"우"가 붙은 우선주, ETF는 분석에서 제외했습니다.',
  }},
  market_cap: {{
    label: '시가총액 (시총)',
    description: '시가총액 = 현재 주가 × 발행 주식 수. 시장이 회사 전체에 매긴 값.',
    benchmark: '10조+ 초대형 / 1조~10조 대형 / 1천억~1조 중형 / 1천억↓ 소형',
    intuition: '"회사를 통째로 사려면 얼마인가?" 매출이나 자산과 다른, 시장의 평가입니다. 매일 변합니다.',
  }},
  total: {{
    label: '평균점수 (EQS Total)',
    description: 'M1~M5 다섯 지표의 단순 평균(0~100점). 금융업은 M2 제외 4개 평균.',
    how: '5개 지표 점수를 더해 5로 나눔. 산출 불가한 지표는 평균에서 자동 제외.',
    benchmark: '80↑ A 우수 / 65↑ B 양호 / 50↑ C 보통 / 35↑ D 주의 / 35↓ F 취약',
    intuition: '학교 성적표 평균과 비슷합니다. 5과목 평균을 내서 등급을 매기는 셈.',
  }},
  grade: {{
    label: '등급 (Grade)',
    description: '평균점수에 따라 부여한 5단계 등급.',
    benchmark: 'A: 80↑, B: 65~79, C: 50~64, D: 35~49, F: 35↓',
    intuition: 'A는 "재무가 매우 튼튼해 보임", F는 "재무 신호에 빨간불". 다만 등급은 과거 재무만 본 값이고, 주가가 싼지·비싼지는 별개입니다.',
  }},
  years: {{
    label: '분석 연도 수',
    description: '점수 산출에 사용한 회계연도 수. 정상은 5년.',
    intuition: '상장한 지 얼마 안 된 회사(예: LG에너지솔루션)나 사업보고서가 일부 누락된 회사는 3~4년만 사용. 데이터가 짧으면 노이즈가 커질 수 있습니다.',
  }},
}};

function buildThTooltip(key, upper) {{
  const g = (DATA.glossary && DATA.glossary[upper]) || EXTRA_TOOLTIPS[key];
  if (!g) return '';
  const sections = [];
  if (g.description) sections.push(['📖 개념', g.description]);
  if (g.how)         sections.push(['🧮 산출 방식', g.how]);
  if (g.benchmark)   sections.push(['📏 기준선', g.benchmark]);
  if (g.intuition)   sections.push(['💡 쉽게 말하면', g.intuition]);
  const body = sections.map(([lbl, txt]) =>
    `<div class="th-tip-section"><div class="th-tip-label">${{lbl}}</div><div class="th-tip-body">${{txt}}</div></div>`
  ).join('');
  return `<span class="th-tip"><div class="th-tip-title">${{g.label}}</div>${{body}}</span>`;
}}

// 페이지 로드 시 모든 헤더에 툴팁 삽입 (M1~M5는 glossary, 나머지는 EXTRA_TOOLTIPS)
const TH_LABELS = {{m1:'현금이익률', m2:'매출 회수 건전성', m3:'부채 건전성', m4:'본업 안정성', m5:'자본 성장성'}};
document.querySelectorAll('#ranking th').forEach(th => {{
  const key = th.dataset.key || '';
  const upper = key.toUpperCase();
  const isModule = ['M1','M2','M3','M4','M5'].includes(upper);
  const tip = buildThTooltip(key, upper);
  if (!tip) return;
  // 표 헤더에 보일 짧은 라벨 — M모듈은 한글 라벨, 기존 텍스트가 있으면 그대로 유지
  const visibleLabel = isModule ? (TH_LABELS[key] || key) : (th.textContent.trim());
  th.innerHTML = visibleLabel + tip;
}});

// 랭킹 표 렌더
const tbody = document.querySelector('#ranking tbody');
let sortKey = 'market_cap';
let sortDir = -1;  // -1: 내림차순

const GRADE_RANK = {{A: 5, B: 4, C: 3, D: 2, F: 1}};

function fmtCap(v) {{
  if (v === null || v === undefined) return '—';
  if (v >= 1e12) return (v / 1e12).toFixed(1) + '조';
  if (v >= 1e8)  return (v / 1e8).toFixed(0) + '억';
  return v.toLocaleString();
}}

function render() {{
  const rows = [...DATA.rows];
  rows.sort((a, b) => {{
    const va = pick(a, sortKey), vb = pick(b, sortKey);
    if (va === null && vb === null) return 0;
    if (va === null) return 1;
    if (vb === null) return -1;
    if (typeof va === 'string') return va.localeCompare(vb, 'ko') * sortDir;
    return (va - vb) * sortDir;
  }});
  tbody.innerHTML = '';
  rows.forEach((r, i) => {{
    const tr = document.createElement('tr');
    if (r.total === null) tr.className = 'err-row';
    const moduleCells = ['M1','M2','M3','M4','M5'].map(m => {{
      const v = r.modules[m];
      const note = (r.module_notes && r.module_notes[m]) ? r.module_notes[m] : '';
      const safeNote = note.replace(/"/g, '&quot;');
      const isFallback = note.includes('fallback');
      const fbMark = isFallback ? '*' : '';
      const display = v === null ? '—' : v.toFixed(0) + fbMark;
      const titleAttr = safeNote ? `title="${{safeNote}}"` : '';
      const cursor = note ? 'cursor:help;' : '';
      return `<td class="num-cell" ${{titleAttr}} style="color:${{MODULE_COLORS[m]}};${{cursor}}">${{display}}</td>`;
    }}).join('');
    const finBadge = r.is_financial ? ' <span style="color:var(--accent);font-size:10px;">[금융]</span>' : '';
    const nameHtml = r.dart_url
      ? `<a href="${{r.dart_url}}" target="_blank" rel="noopener" style="color:var(--text);text-decoration:none;border-bottom:1px dashed var(--muted);" title="DART 사업보고서 보기">${{r.name}}</a>`
      : r.name;
    tr.innerHTML = `
      <td>${{i+1}}</td>
      <td><strong>${{nameHtml}}</strong>${{finBadge}} <span style="color:var(--muted);font-size:11px;">${{r.code || ''}}</span></td>
      <td class="num-cell" style="color:var(--muted);">${{fmtCap(r.market_cap)}}</td>
      <td class="num-cell total-cell">${{r.total === null ? '—' : r.total.toFixed(1)}}</td>
      <td>${{r.grade ? `<span class="grade-pill grade-${{r.grade}}">${{r.grade}}</span>` : ''}}</td>
      ${{moduleCells}}
      <td class="num-cell" style="color:var(--muted);">${{r.year_count}}</td>
    `;
    tbody.appendChild(tr);
  }});
  // 헤더 정렬 표시 갱신
  document.querySelectorAll('#ranking th').forEach(th => {{
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.key === sortKey) th.classList.add(sortDir > 0 ? 'sort-asc' : 'sort-desc');
  }});
}}

function pick(r, key) {{
  if (key === 'rank') return null;
  if (key === 'name') return r.name;
  if (key === 'market_cap') return r.market_cap;
  if (key === 'total') return r.total;
  if (key === 'grade') return r.grade ? GRADE_RANK[r.grade] : null;
  if (key === 'years') return r.year_count;
  if (key.startsWith('m')) return r.modules[key.toUpperCase()];
  return null;
}}

document.querySelectorAll('#ranking th').forEach(th => {{
  th.addEventListener('click', () => {{
    const k = th.dataset.key;
    if (!k || k === 'rank') return;
    if (sortKey === k) sortDir = -sortDir;
    else {{ sortKey = k; sortDir = -1; }}
    render();
  }});
}});

render();

// 등급 분포 도넛
new Chart(document.getElementById('gradeChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['A','B','C','D','F'],
    datasets: [{{
      data: ['A','B','C','D','F'].map(g => DATA.summary.grade_distribution[g] || 0),
      backgroundColor: ['#16a34a','#65a30d','#ca8a04','#ea580c','#dc2626'],
      borderColor: 'var(--panel)', borderWidth: 2,
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ position: 'right', labels: {{ color: '#e2e8f0', font: {{ size: 12 }} }} }} }}
  }}
}});

// 모듈별 평균
new Chart(document.getElementById('moduleChart'), {{
  type: 'bar',
  data: {{
    labels: ['현금이익률','매출 회수','부채 건전성','본업 안정성','자본 성장성'],
    datasets: [{{
      data: ['M1','M2','M3','M4','M5'].map(m => DATA.summary.module_means[m] || 0),
      backgroundColor: ['#06b6d4','#8b5cf6','#22c55e','#eab308','#ef4444'],
    }}]
  }},
  options: {{
    indexAxis: 'y',
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ min: 0, max: 100, ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }},
      y: {{ ticks: {{ color: '#e2e8f0' }}, grid: {{ display: false }} }}
    }}
  }}
}});

// 평균점수 히스토그램 (10점 bin)
const bins = Array.from({{length: 10}}, (_, i) => 0);  // 0-9, 10-19, ..., 90-100
DATA.rows.forEach(r => {{
  if (r.total === null) return;
  const idx = Math.min(9, Math.floor(r.total / 10));
  bins[idx]++;
}});
new Chart(document.getElementById('histChart'), {{
  type: 'bar',
  data: {{
    labels: ['0-9','10-19','20-29','30-39','40-49','50-59','60-69','70-79','80-89','90-100'],
    datasets: [{{
      data: bins,
      backgroundColor: ['#dc2626','#dc2626','#dc2626','#ea580c','#ea580c','#ca8a04','#ca8a04','#65a30d','#65a30d','#16a34a'],
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ display: false }} }},
      y: {{ ticks: {{ color: '#94a3b8', stepSize: 1 }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }}
    }}
  }}
}});
</script>
</body>
</html>
"""


def build_ranking_dashboard(
    records: List[FirmRecord],
    year_range: str,
    output_dir: Optional[str] = None,
    *,
    output_name: str = "kospi50_ranking.html",
) -> str:
    """다수 기업 비교 대시보드 생성. 저장 경로 반환."""
    from datetime import datetime

    out_dir = output_dir or _DASHBOARD_DIR
    os.makedirs(out_dir, exist_ok=True)
    rows = [_record_row(r) for r in records]
    summary = summarize(records)
    glossary = {k: v.as_dict() for k, v in GLOSSARY.items() if k.startswith("M")}
    payload = {"rows": rows, "summary": summary, "glossary": glossary}
    html = _RANKING_TEMPLATE.format(
        analyzed_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        year_range=year_range,
        success_count=summary["success_count"],
        total_count=summary["total_count"],
        avg_total=summary["avg_total"] if summary["avg_total"] is not None else "—",
        a_count=summary["grade_distribution"].get("A", 0),
        f_count=summary["grade_distribution"].get("F", 0),
        data_json=json.dumps(payload, ensure_ascii=False),
    )
    out_path = os.path.join(out_dir, output_name)
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(html)
    return out_path
