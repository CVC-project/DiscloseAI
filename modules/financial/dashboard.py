"""EQSResult + FirmPanel → 단일 HTML 대시보드 생성.

생성된 파일은 docs/prototype/financial_dashboard.html에 저장되며 더블클릭으로
브라우저에서 바로 열린다. 모든 데이터는 inline embed (file:// 환경에서 CORS
없이 동작). Chart.js만 CDN 로드.

사용:
    from modules.financial.collector import fetch_panel
    from modules.financial.eqs import compute_eqs
    from modules.financial.translator import translate_all, extract_highlights
    from modules.financial.dashboard import build_dashboard

    panel = fetch_panel("00126380", range(2015, 2025), corp_name="삼성전자")
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
from .translator.highlights import Highlight

_DASHBOARD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "docs", "prototype"
)


def _firm_year_to_dict(y) -> dict:
    return {
        "year": y.year,
        "revenue": y.revenue,
        "operating_income": y.operating_income,
        "net_income": y.net_income,
        "operating_cashflow": y.operating_cashflow,
        "investing_cashflow": y.investing_cashflow,
        "financing_cashflow": y.financing_cashflow,
        "total_assets": y.total_assets,
        "total_liabilities": y.total_liabilities,
        "total_equity": y.total_equity,
    }


def _serialize(panel: FirmPanel, eqs: EQSResult, summary: List[str], highlights: Iterable[Highlight]) -> dict:
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
        "summary": summary,
        "highlights": [asdict(h) for h in highlights],
    }


_HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>DiscloseAI — {corp_name} 이익 해부</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f172a;
    --panel: #1e293b;
    --border: #334155;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --good: #22c55e;
    --warn: #eab308;
    --bad: #ef4444;
    --accent: #6366f1;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px;
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Malgun Gothic", sans-serif;
    line-height: 1.5;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  header {{
    display: flex; justify-content: space-between; align-items: flex-end;
    border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px;
  }}
  header h1 {{ margin: 0; font-size: 28px; }}
  header .meta {{ color: var(--muted); font-size: 14px; }}
  .grid {{ display: grid; gap: 16px; margin-bottom: 16px; }}
  .grid-2 {{ grid-template-columns: 1fr 1fr; }}
  .grid-3 {{ grid-template-columns: 1fr 1fr 1fr; }}
  .panel {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px;
  }}
  .panel h2 {{ margin: 0 0 12px; font-size: 16px; color: var(--muted); font-weight: 500; }}
  .score-big {{
    font-size: 72px; font-weight: 700; line-height: 1;
    background: linear-gradient(135deg, var(--accent), #8b5cf6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
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
      <div class="chart-wrap"><canvas id="radar"></canvas></div>
    </div>
  </div>

  <div class="panel">
    <h2>매출 · 영업현금흐름 · 순이익 시계열</h2>
    <div class="chart-wrap" style="height:320px;"><canvas id="ts"></canvas></div>
  </div>

  <div class="grid grid-3" style="margin-top:16px;">
    <div class="panel">
      <h2>📊 손익계산서</h2>
      <div class="summary-line" id="sumIncome"></div>
    </div>
    <div class="panel">
      <h2>🏛 재무상태표</h2>
      <div class="summary-line" id="sumBalance"></div>
    </div>
    <div class="panel">
      <h2>💵 현금흐름표</h2>
      <div class="summary-line" id="sumCash"></div>
    </div>
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

// 모듈 점수 리스트
const moduleColors = {{
  M1: '#06b6d4', M2: '#8b5cf6', M3: '#22c55e', M4: '#eab308', M5: '#ef4444'
}};
const moduleLabels = {{
  M1: 'M1 발생액 품질', M2: 'M2 분식 확률', M3: 'M3 현금흐름 괴리',
  M4: 'M4 이익 지속성', M5: 'M5 재무 건전성'
}};

const ml = document.getElementById('moduleList');
DATA.eqs.modules.forEach(m => {{
  const li = document.createElement('li');
  const score = m.score === null ? '—' : m.score.toFixed(1);
  li.innerHTML = `
    <div>
      <span class="module-score" style="color:${{moduleColors[m.name]}}">${{score}}</span>
      <span class="module-name" style="margin-left:12px;">${{moduleLabels[m.name]}}</span>
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
      backgroundColor: 'rgba(99, 102, 241, 0.25)',
      borderColor: '#6366f1',
      borderWidth: 2,
      pointBackgroundColor: '#8b5cf6',
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      r: {{
        min: 0, max: 100,
        grid: {{ color: 'rgba(148, 163, 184, 0.2)' }},
        angleLines: {{ color: 'rgba(148, 163, 184, 0.2)' }},
        pointLabels: {{ color: '#e2e8f0', font: {{ size: 12 }} }},
        ticks: {{ color: '#94a3b8', backdropColor: 'transparent', stepSize: 25 }}
      }}
    }}
  }}
}});

// 시계열
const yrs = DATA.years.map(y => y.year);
const toEok = v => v === null ? null : v / 1e8;  // 원 → 억원 (DART는 원 단위)
new Chart(document.getElementById('ts'), {{
  type: 'line',
  data: {{
    labels: yrs,
    datasets: [
      {{label: '매출', data: DATA.years.map(y => toEok(y.revenue)), borderColor: '#06b6d4', backgroundColor: 'transparent', tension: 0.3}},
      {{label: '영업현금흐름', data: DATA.years.map(y => toEok(y.operating_cashflow)), borderColor: '#22c55e', backgroundColor: 'transparent', tension: 0.3}},
      {{label: '순이익', data: DATA.years.map(y => toEok(y.net_income)), borderColor: '#eab308', backgroundColor: 'transparent', tension: 0.3}},
    ]
  }},
  options: {{
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
) -> str:
    """HTML 대시보드 생성. 저장 경로 반환."""
    out_dir = output_dir or _DASHBOARD_DIR
    os.makedirs(out_dir, exist_ok=True)
    payload = _serialize(panel, eqs, summary, highlights)
    years_in_panel = [y.year for y in panel.years]
    year_range = f"{min(years_in_panel)}~{max(years_in_panel)} ({len(years_in_panel)}년)" if years_in_panel else "—"
    html = _HTML_TEMPLATE.format(
        corp_name=payload["corp"]["name"],
        corp_code=payload["corp"]["code"],
        year_range=year_range,
        total=eqs.total if eqs.total is not None else "—",
        grade=eqs.grade or "F",
        data_json=json.dumps(payload, ensure_ascii=False),
    )
    out_path = os.path.join(out_dir, "financial_dashboard.html")
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(html)
    return out_path


# ---------------------------------------------------------------------------
# Ranking dashboard (다수 기업 비교)
# ---------------------------------------------------------------------------


def _record_row(r: FirmRecord) -> dict:
    """배치 1행 → 표 + 차트용 dict."""
    common = {
        "name": r.display_name,
        "code": r.corp.stock_code if r.corp else None,
        "industry_code": r.industry_code,
        "is_financial": r.industry_code is not None and r.industry_code.startswith(("064", "065", "066", "067")),
        "market_cap": r.market_cap,
        "year_count": len(r.panel.years) if r.panel else 0,
    }
    if r.eqs is None:
        return {**common, "total": None, "grade": None,
                "modules": {m: None for m in ("M1", "M2", "M3", "M4", "M5")},
                "error": r.error}
    mod_map = {m.name: m.score for m in r.eqs.modules}
    return {**common, "total": r.eqs.total, "grade": r.eqs.grade,
            "modules": {m: mod_map.get(m) for m in ("M1", "M2", "M3", "M4", "M5")},
            "error": None}


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
      <h2>랭킹 (컬럼 헤더 클릭 시 정렬)</h2>
      <div style="max-height:600px;overflow-y:auto;">
        <table id="ranking">
          <thead>
            <tr>
              <th data-key="rank">#</th>
              <th data-key="name">기업</th>
              <th class="num-cell" data-key="market_cap">시총</th>
              <th class="num-cell" data-key="total">총점</th>
              <th data-key="grade">등급</th>
              <th class="num-cell" data-key="m1">M1</th>
              <th class="num-cell" data-key="m2">M2</th>
              <th class="num-cell" data-key="m3">M3</th>
              <th class="num-cell" data-key="m4">M4</th>
              <th class="num-cell" data-key="m5">M5</th>
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
    <h2>총점 분포</h2>
    <div class="chart-wrap" style="height:200px;"><canvas id="histChart"></canvas></div>
  </div>

  <footer>
    <div class="disclaimer">
      ⚠️ 본 분석은 K-IFRS 재무제표 기반 과거 통계 정보입니다. 투자 조언이 아닙니다.
      금융지주사 등 일부 기업은 DART 과거 사업보고서 누락으로 단축 윈도우 기준입니다.
    </div>
    <div style="margin-top:12px;">
      Powered by DART OpenAPI · DiscloseAI Financial Module
    </div>
  </footer>
</div>

<script>
const DATA = {data_json};
const MODULE_COLORS = {{M1:'#06b6d4', M2:'#8b5cf6', M3:'#22c55e', M4:'#eab308', M5:'#ef4444'}};

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
      return `<td class="num-cell" style="color:${{MODULE_COLORS[m]}};">${{v === null ? '—' : v.toFixed(0)}}</td>`;
    }}).join('');
    const finBadge = r.is_financial ? ' <span style="color:var(--accent);font-size:10px;">[금융]</span>' : '';
    tr.innerHTML = `
      <td>${{i+1}}</td>
      <td><strong>${{r.name}}</strong>${{finBadge}} <span style="color:var(--muted);font-size:11px;">${{r.code || ''}}</span></td>
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
    labels: ['M1 발생액','M2 분식','M3 OCF/NI','M4 지속성','M5 Piotroski'],
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

// 총점 히스토그램 (10점 bin)
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
    payload = {"rows": rows, "summary": summary}
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
