"""
modules/disclosure/generate_report.py
DB에서 공시 데이터를 읽어 정적 HTML 리포트를 생성한다.

실행:
    python -m modules.disclosure.generate_report
    python -m modules.disclosure.generate_report --days 30
"""

import os
import sys
import argparse
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def fmt_date(d) -> str:
    if d is None:
        return "-"
    if isinstance(d, (datetime, date)):
        return d.strftime("%Y-%m-%d")
    return str(d)


def fmt_ratio(v) -> str:
    if v is None:
        return "-"
    return f"{v:.2f}%"


def escape(s: str) -> str:
    if not s:
        return ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


import re as _re


def _mark_uncertain(text: str) -> str:
    """[추정] 태그 이후 텍스트를 회색 이탤릭으로 변환."""
    return _re.sub(
        r"\[추정\](.*)",
        r'<span class="uncertain">[추정]</span><span class="uncertain-text">\1</span>',
        text,
    )


def summary_html(text: str) -> str:
    """summary 텍스트를 섹션별로 색상 구분해 HTML로 변환."""
    if not text:
        return "<em>분석 없음</em>"
    lines = text.split("\n")
    html_lines = []
    for line in lines:
        line_e = escape(line)
        line_e = _mark_uncertain(line_e)
        if line_e.startswith("[Cash]"):
            html_lines.append(f'<p class="sec cash">{line_e}</p>')
        elif line_e.startswith("[Risk]"):
            html_lines.append(f'<p class="sec risk">{line_e}</p>')
        elif line_e.startswith("[Hidden Agenda]"):
            html_lines.append(f'<p class="sec hidden">{line_e}</p>')
        elif line_e.startswith("[Verdict]"):
            html_lines.append(f'<p class="sec verdict">{line_e}</p>')
        elif line_e.startswith("[오늘의 개념]"):
            html_lines.append(f'<p class="sec concept">{line_e}</p>')
        elif line_e.startswith("- "):
            html_lines.append(f'<p class="bullet">{line_e}</p>')
        elif line_e.strip() == "":
            html_lines.append("<br>")
        else:
            html_lines.append(f"<p>{line_e}</p>")
    return "\n".join(html_lines)


TYPE_COLORS = {
    "정기보고서": "#0ea5e9",
    "증자": "#ef4444",
    "전환사채": "#ef4444",
    "BW": "#ef4444",
    "M&A/분할": "#f97316",
    "실적": "#3b82f6",
    "계약": "#10b981",
    "CAPEX": "#10b981",
    "임원변동": "#8b5cf6",
    "자기주식": "#6366f1",
    "채권발행": "#f59e0b",
    "내부자거래": "#94a3b8",
    "최대주주변동": "#ec4899",
    "영업양도": "#f97316",
    "기타": "#94a3b8",
}


def _disc_row(r) -> str:
    """모달 안 공시 한 줄 (클릭 시 분석 펼침)."""
    color = TYPE_COLORS.get(r.disclosure_type or "기타", "#94a3b8")
    high_badge = '<span class="badge high">⚠ HIGH</span>' if r.high_impact else ""
    ai_badge = (
        '<span class="badge ai">AI</span>'
        if r.ai_analyzed
        else '<span class="badge tmpl">템플릿</span>'
    )
    dilution = (
        f'<span class="dilution">희석률 {fmt_ratio(r.dilution_ratio)}</span>'
        if (r.dilution_ratio is not None and r.dilution_ratio > 0)
        else ""
    )
    dart_link = ""
    if r.disclosure_id:
        dart_link = f'<a class="dart-link" href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo={r.disclosure_id}" target="_blank" onclick="event.stopPropagation()">원문↗</a>'
    analysis = summary_html(r.summary or "")
    title_esc = escape(r.title or "")
    summary_esc = escape(r.summary or "").replace("\n", "\\n")
    corp_esc = escape(r.corp_name or "")
    disc_type_esc = escape(r.disclosure_type or "기타")
    disc_date_esc = fmt_date(r.disclosure_date)
    chat_btn = f'<button class="chat-btn" onclick="openChat(this)" data-corp="{corp_esc}" data-title="{title_esc}" data-type="{disc_type_esc}" data-date="{disc_date_esc}" data-summary="{summary_esc}">💬 질문하기</button>'
    return f"""<div class="disc-row" data-type="{disc_type_esc}" data-high="{'1' if r.high_impact else '0'}">
  <div class="disc-row-header" onclick="toggleDisc(this)">
    <div class="disc-row-left">
      <span class="type-tag" style="background:{color}">{disc_type_esc}</span>
      {high_badge}
      <span class="disc-title">{title_esc}</span>
    </div>
    <div class="disc-row-right">
      {dilution}{ai_badge}{dart_link}
      <span class="disc-date">{disc_date_esc}</span>
      <span class="disc-chevron">▼</span>
    </div>
  </div>
  <div class="disc-analysis">
    <div class="disc-analysis-inner">
      {analysis}
      <div class="chat-row">{chat_btn}</div>
    </div>
  </div>
</div>"""


def generate(days: int = 7, all_disclosures: bool = False) -> str:
    from modules.disclosure.db import get_local_session
    from modules.disclosure.models import DisclosureLocal
    from collections import defaultdict
    import json

    gemini_api_key = os.getenv("GEMINI_API_KEY", "")

    session = get_local_session()
    cutoff = datetime.today().date() - timedelta(days=days)

    q = session.query(DisclosureLocal).filter(DisclosureLocal.disclosure_date >= cutoff)
    if not all_disclosures:
        q = q.filter(DisclosureLocal.display_worthy == True)  # noqa: E712
    rows = q.order_by(
        DisclosureLocal.high_impact.desc(),
        DisclosureLocal.disclosure_date.desc(),
    ).all()
    session.close()

    total = len(rows)
    high_count = sum(1 for r in rows if r.high_impact)
    ai_count = sum(1 for r in rows if r.ai_analyzed)

    company_map: dict[str, list] = defaultdict(list)
    for r in rows:
        company_map[r.corp_name or "기타"].append(r)

    sorted_companies = sorted(
        company_map.items(),
        key=lambda x: (sum(1 for r in x[1] if r.high_impact), len(x[1])),
        reverse=True,
    )

    # 검색용 JS 데이터 (기업명 + 공시 제목 목록)
    search_data = {
        name: [r.title or "" for r in corp_rows] for name, corp_rows in sorted_companies
    }

    # 기업 카드 그리드
    corp_cards_html = ""
    for corp_name, corp_rows in sorted_companies:
        high_in_corp = sum(1 for r in corp_rows if r.high_impact)
        types_in_corp = list(
            {r.disclosure_type for r in corp_rows if r.disclosure_type}
        )
        type_dots = "".join(
            f'<span class="tdot" style="background:{TYPE_COLORS.get(t,"#94a3b8")}" title="{escape(t)}"></span>'
            for t in types_in_corp[:5]
        )
        high_cls = "corp-high" if high_in_corp else ""
        high_mark = (
            f'<span class="corp-high-mark">⚠ {high_in_corp}</span>'
            if high_in_corp
            else ""
        )
        name_esc = escape(corp_name)
        corp_cards_html += f"""<div class="corp-card {high_cls}" data-corp="{name_esc}" data-titles="{escape('|'.join(r.title or '' for r in corp_rows))}" onclick="openModal('{name_esc}')">
  <div class="corp-card-top">
    <span class="corp-card-name">{name_esc}</span>
    {high_mark}
  </div>
  <div class="corp-card-bottom">
    <span class="corp-card-count">{len(corp_rows)}건</span>
    <div class="type-dots">{type_dots}</div>
  </div>
</div>"""

    # 모달 콘텐츠 (기업별 사전 생성, 숨김)
    modal_data_html = ""
    for corp_name, corp_rows in sorted_companies:
        rows_html = "\n".join(_disc_row(r) for r in corp_rows)
        modal_data_html += f'<div class="modal-corp-data" data-corp="{escape(corp_name)}">{rows_html}</div>\n'

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    search_json = json.dumps(search_data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DiscloseAI — 공시 리포트</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Pretendard','Apple SD Gothic Neo',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}

  /* ── 헤더 ── */
  header{{background:#1e293b;border-bottom:1px solid #334155;padding:16px 28px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}}
  header h1{{font-size:1.3rem;font-weight:700;color:#f8fafc;letter-spacing:-.5px;white-space:nowrap}}
  header h1 span{{color:#38bdf8}}
  .meta{{font-size:.75rem;color:#64748b}}

  /* ── 통계 ── */
  .stats{{display:flex;gap:12px;padding:16px 28px;background:#1e293b;border-bottom:1px solid #334155;flex-wrap:wrap}}
  .stat{{background:#0f172a;border:1px solid #334155;border-radius:10px;padding:12px 18px;min-width:110px}}
  .stat-num{{font-size:1.5rem;font-weight:700;color:#38bdf8}}
  .stat-label{{font-size:.72rem;color:#94a3b8;margin-top:2px}}
  .stat.danger .stat-num{{color:#ef4444}}
  .stat.green .stat-num{{color:#10b981}}

  /* ── 검색 + 필터 ── */
  .toolbar{{padding:14px 28px;background:#0f172a;border-bottom:1px solid #1e293b;display:flex;flex-direction:column;gap:10px}}
  .search-wrap{{position:relative}}
  .search-input{{width:100%;background:#1e293b;border:1px solid #334155;border-radius:10px;padding:9px 16px 9px 38px;color:#e2e8f0;font-size:.85rem;outline:none;transition:border .15s}}
  .search-input:focus{{border-color:#38bdf8}}
  .search-icon{{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:#64748b;font-size:.9rem}}
  .filter-bar{{display:flex;gap:6px;flex-wrap:wrap}}
  .filter-btn{{background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:4px 12px;border-radius:20px;cursor:pointer;font-size:.75rem;transition:all .15s}}
  .filter-btn:hover,.filter-btn.active{{background:#38bdf8;color:#0f172a;border-color:#38bdf8;font-weight:600}}

  /* ── 기업 카드 그리드 ── */
  .corp-grid{{padding:20px 28px;display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}}
  .corp-card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:14px 16px;cursor:pointer;transition:transform .15s,box-shadow .15s,border-color .15s}}
  .corp-card:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.4);border-color:#38bdf8}}
  .corp-card.corp-high{{border-color:#ef4444;background:#1c1717}}
  .corp-card-top{{display:flex;align-items:flex-start;justify-content:space-between;gap:6px;margin-bottom:10px}}
  .corp-card-name{{font-size:.92rem;font-weight:700;color:#f1f5f9;line-height:1.3}}
  .corp-high-mark{{font-size:.65rem;font-weight:700;color:#fca5a5;background:#7f1d1d;padding:2px 6px;border-radius:8px;white-space:nowrap}}
  .corp-card-bottom{{display:flex;align-items:center;justify-content:space-between}}
  .corp-card-count{{font-size:.72rem;color:#64748b}}
  .type-dots{{display:flex;gap:4px}}
  .tdot{{width:8px;height:8px;border-radius:50%}}
  .no-result{{color:#64748b;text-align:center;padding:48px;font-size:.95rem;display:none}}

  /* ── 모달 ── */
  .modal-overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;align-items:flex-start;justify-content:center;padding:40px 16px;overflow-y:auto}}
  .modal-overlay.open{{display:flex}}
  .modal-box{{background:#1e293b;border:1px solid #334155;border-radius:16px;width:100%;max-width:800px;max-height:85vh;display:flex;flex-direction:column;position:relative}}
  .modal-header{{padding:18px 22px;border-bottom:1px solid #334155;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}}
  .modal-corp-name{{font-size:1.1rem;font-weight:700;color:#f8fafc}}
  .modal-close{{background:none;border:none;color:#64748b;cursor:pointer;font-size:1.2rem;padding:4px 8px;border-radius:6px;transition:color .15s}}
  .modal-close:hover{{color:#f1f5f9}}
  .modal-filter{{padding:10px 22px;border-bottom:1px solid #334155;display:flex;gap:6px;flex-wrap:wrap;flex-shrink:0}}
  .modal-body{{overflow-y:auto;flex:1;padding:10px 0}}

  /* ── 공시 행 ── */
  .disc-row{{border-bottom:1px solid #1e293b}}
  .disc-row:last-child{{border-bottom:none}}
  .disc-row-header{{display:flex;align-items:center;justify-content:space-between;padding:12px 22px;cursor:pointer;gap:12px;transition:background .12s}}
  .disc-row-header:hover{{background:#253148}}
  .disc-row.open .disc-row-header{{background:#253148}}
  .disc-row-left{{display:flex;align-items:center;gap:8px;flex:1;min-width:0;flex-wrap:wrap}}
  .disc-row-right{{display:flex;align-items:center;gap:8px;flex-shrink:0}}
  .disc-title{{font-size:.83rem;color:#cbd5e1;line-height:1.4}}
  .disc-date{{font-size:.72rem;color:#64748b;white-space:nowrap}}
  .disc-chevron{{color:#64748b;font-size:.75rem;transition:transform .2s}}
  .disc-row.open .disc-chevron{{transform:rotate(180deg)}}

  /* ── 분석 내용 ── */
  .disc-analysis{{max-height:0;overflow:hidden;transition:max-height .3s ease}}
  .disc-row.open .disc-analysis{{max-height:2000px}}
  .disc-analysis-inner{{padding:16px 22px;border-top:1px solid #1e293b;font-size:.81rem;line-height:1.65;color:#cbd5e1}}
  .disc-analysis-inner p{{margin-bottom:4px}}
  .disc-analysis-inner .sec{{font-weight:600;margin-top:10px;padding:6px 10px;border-radius:6px}}
  .disc-analysis-inner .cash{{background:#0c4a1e;color:#86efac}}
  .disc-analysis-inner .risk{{background:#450a0a;color:#fca5a5}}
  .disc-analysis-inner .hidden{{background:#1e1b4b;color:#c4b5fd}}
  .disc-analysis-inner .verdict{{background:#1c1917;color:#fde68a;border-left:3px solid #fbbf24}}
  .disc-analysis-inner .concept{{background:#0c3443;color:#7dd3fc}}
  .disc-analysis-inner .bullet{{padding-left:16px;color:#94a3b8}}
  .disc-analysis-inner .uncertain{{color:#f59e0b;font-size:.7rem;font-weight:700;margin-right:4px}}
  .disc-analysis-inner .uncertain-text{{color:#78716c;font-style:italic}}

  .type-tag{{color:#fff;font-size:.68rem;font-weight:700;padding:2px 8px;border-radius:20px;white-space:nowrap}}
  .badge{{font-size:.65rem;font-weight:700;padding:2px 7px;border-radius:20px;white-space:nowrap}}
  .badge.high{{background:#7f1d1d;color:#fca5a5}}
  .badge.ai{{background:#1e3a5f;color:#7dd3fc}}
  .badge.tmpl{{background:#1e293b;color:#64748b;border:1px solid #334155}}
  .dilution{{font-size:.68rem;color:#fb923c;font-weight:600}}
  .dart-link{{font-size:.68rem;color:#38bdf8;text-decoration:none;padding:2px 7px;border:1px solid #38bdf8;border-radius:20px;white-space:nowrap;transition:background .12s}}
  .dart-link:hover{{background:#38bdf8;color:#0f172a}}

  /* ── 채팅 버튼 ── */
  .chat-row{{margin-top:14px;padding-top:12px;border-top:1px solid #334155}}
  .chat-btn{{background:linear-gradient(135deg,#6366f1,#8b5cf6);border:none;color:#fff;padding:6px 16px;border-radius:20px;cursor:pointer;font-size:.78rem;font-weight:600;transition:opacity .15s}}
  .chat-btn:hover{{opacity:.85}}

  /* ── 채팅 패널 (슬라이드인) ── */
  .chat-panel{{position:fixed;right:0;top:0;bottom:0;width:380px;background:#1e293b;border-left:1px solid #334155;display:flex;flex-direction:column;z-index:200;transform:translateX(100%);transition:transform .25s ease}}
  .chat-panel.open{{transform:translateX(0)}}
  .chat-panel-header{{padding:14px 18px;border-bottom:1px solid #334155;display:flex;align-items:flex-start;justify-content:space-between;gap:8px;flex-shrink:0}}
  .chat-panel-title{{font-size:.82rem;font-weight:700;color:#f1f5f9;line-height:1.4}}
  .chat-panel-sub{{font-size:.7rem;color:#64748b;margin-top:2px}}
  .chat-panel-close{{background:none;border:none;color:#64748b;cursor:pointer;font-size:1.1rem;flex-shrink:0;padding:2px 6px;border-radius:6px}}
  .chat-panel-close:hover{{color:#f1f5f9}}
  .chat-messages{{flex:1;overflow-y:auto;padding:14px 18px;display:flex;flex-direction:column;gap:12px}}
  .chat-msg{{max-width:95%;padding:10px 14px;border-radius:12px;font-size:.8rem;line-height:1.6;white-space:pre-wrap;word-break:break-word}}
  .chat-msg.user{{background:#1e3a5f;color:#e2e8f0;align-self:flex-end;border-bottom-right-radius:4px}}
  .chat-msg.assistant{{background:#0f172a;color:#cbd5e1;align-self:flex-start;border-bottom-left-radius:4px;border:1px solid #334155}}
  .chat-msg.typing{{color:#64748b;font-style:italic}}
  .chat-input-row{{padding:12px 18px;border-top:1px solid #334155;display:flex;gap:8px;flex-shrink:0}}
  .chat-input{{flex:1;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:8px 12px;color:#e2e8f0;font-size:.8rem;outline:none;resize:none;max-height:100px;transition:border .15s}}
  .chat-input:focus{{border-color:#6366f1}}
  .chat-send{{background:#6366f1;border:none;color:#fff;padding:8px 14px;border-radius:10px;cursor:pointer;font-size:.8rem;font-weight:600;align-self:flex-end;transition:opacity .15s}}
  .chat-send:hover{{opacity:.85}}
  .chat-send:disabled{{opacity:.4;cursor:not-allowed}}
  .chat-disclaimer{{font-size:.65rem;color:#475569;text-align:center;padding:4px 18px 10px;flex-shrink:0}}

  footer{{text-align:center;color:#334155;font-size:.72rem;padding:20px}}
</style>
</head>
<body>

<header>
  <h1>Disclose<span>AI</span></h1>
  <span class="meta">최근 {days}일 · {generated_at}</span>
</header>

<div class="stats">
  <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">전체 공시</div></div>
  <div class="stat danger"><div class="stat-num">{high_count}</div><div class="stat-label">HIGH IMPACT</div></div>
  <div class="stat green"><div class="stat-num">{ai_count}</div><div class="stat-label">AI 분석</div></div>
  <div class="stat"><div class="stat-num">{len(sorted_companies)}</div><div class="stat-label">기업 수</div></div>
</div>

<div class="toolbar">
  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input class="search-input" id="search-input" type="text" placeholder="기업명 또는 공시 제목 검색..." oninput="onSearch(this.value)">
  </div>
  <div class="filter-bar">
    <button class="filter-btn active" onclick="setFilter('all',this)">전체</button>
    <button class="filter-btn" onclick="setFilter('high-impact',this)">⚠ HIGH IMPACT</button>
    <button class="filter-btn" onclick="setFilter('정기보고서',this)">정기보고서</button>
    <button class="filter-btn" onclick="setFilter('증자',this)">증자</button>
    <button class="filter-btn" onclick="setFilter('전환사채',this)">전환사채</button>
    <button class="filter-btn" onclick="setFilter('BW',this)">BW</button>
    <button class="filter-btn" onclick="setFilter('실적',this)">실적</button>
    <button class="filter-btn" onclick="setFilter('계약',this)">계약</button>
    <button class="filter-btn" onclick="setFilter('M&amp;A/분할',this)">M&amp;A/분할</button>
    <button class="filter-btn" onclick="setFilter('CAPEX',this)">CAPEX</button>
    <button class="filter-btn" onclick="setFilter('자기주식',this)">자기주식</button>
  </div>
</div>

<div class="corp-grid" id="corp-grid">
{corp_cards_html}
</div>
<p class="no-result" id="no-result">검색 결과가 없습니다.</p>

<footer>DiscloseAI · 본 리포트는 참고용이며 투자 조언이 아닙니다.</footer>

<!-- 채팅 패널 -->
<div class="chat-panel" id="chat-panel">
  <div class="chat-panel-header">
    <div>
      <div class="chat-panel-title" id="chat-panel-title">공시 질문하기</div>
      <div class="chat-panel-sub" id="chat-panel-sub"></div>
    </div>
    <button class="chat-panel-close" onclick="closeChat()">✕</button>
  </div>
  <div class="chat-messages" id="chat-messages"></div>
  <div class="chat-disclaimer">참고용 정보입니다 · 투자 조언 아님</div>
  <div class="chat-input-row">
    <textarea class="chat-input" id="chat-input" rows="1" placeholder="이 공시에 대해 궁금한 점을 입력하세요..." onkeydown="onChatKey(event)"></textarea>
    <button class="chat-send" id="chat-send" onclick="sendChat()">전송</button>
  </div>
</div>

<!-- 기업별 모달 데이터 (숨김) -->
<div id="modal-store" style="display:none">
{modal_data_html}
</div>

<!-- 모달 -->
<div class="modal-overlay" id="modal-overlay" onclick="onOverlayClick(event)">
  <div class="modal-box" id="modal-box">
    <div class="modal-header">
      <span class="modal-corp-name" id="modal-title"></span>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-filter" id="modal-filter">
      <button class="filter-btn active" onclick="filterModal('all',this)">전체</button>
      <button class="filter-btn" onclick="filterModal('high-impact',this)">⚠ HIGH IMPACT</button>
      <button class="filter-btn" onclick="filterModal('정기보고서',this)">정기보고서</button>
      <button class="filter-btn" onclick="filterModal('증자',this)">증자</button>
      <button class="filter-btn" onclick="filterModal('전환사채',this)">전환사채</button>
      <button class="filter-btn" onclick="filterModal('실적',this)">실적</button>
      <button class="filter-btn" onclick="filterModal('계약',this)">계약</button>
      <button class="filter-btn" onclick="filterModal('자기주식',this)">자기주식</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<script>
const searchData = {search_json};
const GEMINI_API_KEY = '{gemini_api_key}';
const GEMINI_MODEL = 'gemini-2.5-flash-preview-04-17';
let currentFilter = 'all';

function setFilter(type, btn) {{
  currentFilter = type;
  document.querySelectorAll('.filter-bar .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters(document.getElementById('search-input').value);
}}

function onSearch(q) {{
  applyFilters(q);
}}

function applyFilters(q) {{
  q = q.trim().toLowerCase();
  const cards = document.querySelectorAll('.corp-card');
  let anyVisible = false;
  cards.forEach(card => {{
    const corp = card.dataset.corp;
    const titles = (card.dataset.titles || '').toLowerCase();
    const matchSearch = !q || corp.toLowerCase().includes(q) || titles.includes(q);
    // 타입 필터
    let matchType = true;
    if (currentFilter === 'high-impact') {{
      matchType = card.classList.contains('corp-high');
    }} else if (currentFilter !== 'all') {{
      // 해당 타입 공시가 있는 기업만
      const data = searchData[corp];
      const discEl = document.querySelectorAll(`#modal-store [data-corp="${{corp}}"] .disc-row`);
      matchType = Array.from(discEl).some(r => r.dataset.type === currentFilter);
    }}
    const show = matchSearch && matchType;
    card.style.display = show ? '' : 'none';
    if (show) anyVisible = true;
  }});
  document.getElementById('no-result').style.display = anyVisible ? 'none' : 'block';
}}

function openModal(corp) {{
  const src = document.querySelector(`#modal-store [data-corp="${{corp}}"]`);
  if (!src) return;
  document.getElementById('modal-title').textContent = corp;
  const body = document.getElementById('modal-body');
  body.innerHTML = src.innerHTML;
  // 모달 내 필터 초기화
  document.querySelectorAll('#modal-filter .filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('#modal-filter .filter-btn').classList.add('active');
  document.getElementById('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}}

function closeModal() {{
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
}}

function onOverlayClick(e) {{
  if (e.target === document.getElementById('modal-overlay')) closeModal();
}}

function toggleDisc(header) {{
  const row = header.parentElement;
  const isOpen = row.classList.contains('open');
  // 같은 모달 내 다른 열린 공시 모두 닫기
  document.querySelectorAll('#modal-body .disc-row.open').forEach(r => r.classList.remove('open'));
  if (!isOpen) row.classList.add('open');
}}

function filterModal(type, btn) {{
  document.querySelectorAll('#modal-filter .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#modal-body .disc-row').forEach(row => {{
    let show = false;
    if (type === 'all') show = true;
    else if (type === 'high-impact') show = row.dataset.high === '1';
    else show = row.dataset.type === type;
    row.style.display = show ? '' : 'none';
  }});
}}

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') {{ closeModal(); closeChat(); }} }});

// ── 채팅 ──────────────────────────────────────────────
let chatContext = {{}};
let chatHistory = [];
let chatStreaming = false;

function _buildSystemPrompt(ctx) {{
  const summaryBlock = ctx.summary
    ? `\\n아래는 이 공시의 AI 사전 분석입니다.\\n---\\n${{ctx.summary}}\\n---\\n`
    : '';
  return `당신은 한국 주식시장 공시 전문 AI 어시스턴트입니다.
사용자가 특정 공시에 대해 궁금한 점을 질문하면 쉽고 명확하게 한국어로 답변하세요.

【현재 공시 정보】
- 기업명: ${{ctx.corp_name}}
- 공시 제목: ${{ctx.disc_title}}
- 공시 유형: ${{ctx.disc_type}}
- 공시 일자: ${{ctx.disc_date}}
${{summaryBlock}}
【답변 원칙】
- 원문이나 분석에 명시된 내용은 근거를 들어 답변하세요.
- 확인되지 않은 추론은 "추정컨대" 또는 "~일 가능성이 있습니다"로 시작하세요.
- 전문 용어는 쉬운 말로 풀어 설명하세요.
- 투자 조언이 아닌 정보 제공 목적임을 명심하세요.
- 답변은 핵심만 3~5문장 이내로 작성하세요.`;
}}

function openChat(btn) {{
  event.stopPropagation();
  chatContext = {{
    corp_name: btn.dataset.corp,
    disc_title: btn.dataset.title,
    disc_type: btn.dataset.type,
    disc_date: btn.dataset.date,
    summary: (btn.dataset.summary || '').replace(/\\n/g, '\\n'),
  }};
  chatHistory = [];
  document.getElementById('chat-panel-title').textContent = btn.dataset.corp + ' · ' + btn.dataset.type;
  document.getElementById('chat-panel-sub').textContent = btn.dataset.title;
  document.getElementById('chat-messages').innerHTML = '';
  document.getElementById('chat-input').value = '';
  document.getElementById('chat-panel').classList.add('open');
}}

function closeChat() {{
  document.getElementById('chat-panel').classList.remove('open');
}}

function onChatKey(e) {{
  if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendChat(); }}
}}

async function sendChat() {{
  if (chatStreaming) return;
  if (!GEMINI_API_KEY) {{
    alert('.env 파일에 GEMINI_API_KEY를 추가하고 리포트를 다시 생성하세요.');
    return;
  }}
  const input = document.getElementById('chat-input');
  const q = input.value.trim();
  if (!q) return;

  appendMsg('user', q);
  input.value = '';

  const assistantEl = appendMsg('assistant', '', true);
  chatStreaming = true;
  document.getElementById('chat-send').disabled = true;

  // Gemini API 직접 호출 (스트리밍)
  const systemPrompt = _buildSystemPrompt(chatContext);
  const contents = [
    ...chatHistory,
    {{ role: 'user', parts: [{{ text: q }}] }}
  ];

  try {{
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${{GEMINI_MODEL}}:streamGenerateContent?key=${{GEMINI_API_KEY}}&alt=sse`;
    const res = await fetch(url, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        system_instruction: {{ parts: [{{ text: systemPrompt }}] }},
        contents,
        generationConfig: {{ temperature: 0.3 }},
      }}),
    }});

    if (!res.ok) {{
      const errText = await res.text();
      assistantEl.textContent = 'Gemini 오류: ' + res.status + ' — ' + errText.slice(0, 200);
      assistantEl.classList.remove('typing');
      return;
    }}

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    assistantEl.classList.remove('typing');

    while (true) {{
      const {{done, value}} = await reader.read();
      if (done) break;
      const lines = decoder.decode(value).split('\\n');
      for (const line of lines) {{
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (!raw || raw === '[DONE]') continue;
        try {{
          const obj = JSON.parse(raw);
          const text = obj?.candidates?.[0]?.content?.parts?.[0]?.text;
          if (text) {{ fullText += text; assistantEl.textContent = fullText; scrollChat(); }}
        }} catch {{}}
      }}
    }}

    if (fullText) {{
      chatHistory.push({{ role: 'user', parts: [{{ text: q }}] }});
      chatHistory.push({{ role: 'model', parts: [{{ text: fullText }}] }});
    }}

  }} catch (err) {{
    assistantEl.textContent = '오류: ' + err.message;
    assistantEl.classList.remove('typing');
  }} finally {{
    chatStreaming = false;
    document.getElementById('chat-send').disabled = false;
    input.focus();
  }}
}}

function appendMsg(role, text, typing=false) {{
  const el = document.createElement('div');
  el.className = 'chat-msg ' + role + (typing ? ' typing' : '');
  el.textContent = typing ? '답변 생성 중...' : text;
  document.getElementById('chat-messages').appendChild(el);
  scrollChat();
  return el;
}}

function scrollChat() {{
  const m = document.getElementById('chat-messages');
  m.scrollTop = m.scrollHeight;
}}
</script>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="최근 N일 (기본 7)")
    parser.add_argument("--out", type=str, default="", help="출력 파일 경로")
    parser.add_argument("--all", action="store_true", help="저가치 공시 포함 전체 출력")
    args = parser.parse_args()

    print(
        f"[리포트 생성] 최근 {args.days}일 공시 조회 중{'(전체)' if args.all else ''}..."
    )
    html = generate(days=args.days, all_disclosures=args.all)

    out_path = args.out or os.path.join(
        os.path.dirname(__file__), f"report_{datetime.today().strftime('%Y%m%d')}.html"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[완료] {out_path}")


if __name__ == "__main__":
    main()
