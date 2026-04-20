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


def summary_html(text: str) -> str:
    """summary 텍스트를 섹션별로 색상 구분해 HTML로 변환."""
    if not text:
        return "<em>분석 없음</em>"
    lines = text.split("\n")
    html_lines = []
    for line in lines:
        line_e = escape(line)
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


def generate(days: int = 7) -> str:
    from modules.disclosure.db import get_local_session
    from modules.disclosure.models import DisclosureLocal

    session = get_local_session()
    cutoff = datetime.today().date() - timedelta(days=days)

    rows = (
        session.query(DisclosureLocal)
        .filter(DisclosureLocal.disclosure_date >= cutoff)
        .order_by(
            DisclosureLocal.high_impact.desc(),
            DisclosureLocal.disclosure_date.desc(),
        )
        .all()
    )
    session.close()

    total = len(rows)
    high_count = sum(1 for r in rows if r.high_impact)
    ai_count = sum(1 for r in rows if r.ai_analyzed)
    corps = len({r.corp_name for r in rows})

    cards = []
    for r in rows:
        color = TYPE_COLORS.get(r.disclosure_type or "기타", "#94a3b8")
        high_badge = (
            '<span class="badge high">⚠ HIGH IMPACT</span>' if r.high_impact else ""
        )
        ai_badge = (
            '<span class="badge ai">AI 분석</span>'
            if r.ai_analyzed
            else '<span class="badge tmpl">템플릿</span>'
        )
        dilution = (
            f'<span class="dilution">희석률 {fmt_ratio(r.dilution_ratio)}</span>'
            if r.dilution_ratio is not None
            else ""
        )
        summary = summary_html(r.summary or "")

        card = f"""
<div class="card {'high-impact' if r.high_impact else ''}">
  <div class="card-header">
    <span class="type-tag" style="background:{color}">{escape(r.disclosure_type or '기타')}</span>
    {high_badge}
    {ai_badge}
    {dilution}
    <span class="date">{fmt_date(r.disclosure_date)}</span>
  </div>
  <h3 class="corp">{escape(r.corp_name or '')}</h3>
  <h4 class="title">{escape(r.title or '')}</h4>
  <div class="summary">{summary}</div>
</div>"""
        cards.append(card)

    cards_html = (
        "\n".join(cards) if cards else "<p class='empty'>해당 기간 공시 없음</p>"
    )
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DiscloseAI — 공시 리포트</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}

  header {{ background: #1e293b; border-bottom: 1px solid #334155; padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; }}
  header h1 {{ font-size: 1.4rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.5px; }}
  header h1 span {{ color: #38bdf8; }}
  .meta {{ font-size: 0.78rem; color: #64748b; }}

  .stats {{ display: flex; gap: 16px; padding: 20px 32px; background: #1e293b; border-bottom: 1px solid #334155; }}
  .stat {{ background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 14px 20px; min-width: 130px; }}
  .stat-num {{ font-size: 1.6rem; font-weight: 700; color: #38bdf8; }}
  .stat-label {{ font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }}
  .stat.danger .stat-num {{ color: #ef4444; }}
  .stat.green .stat-num {{ color: #10b981; }}

  .filter-bar {{ padding: 16px 32px; display: flex; gap: 8px; flex-wrap: wrap; background: #0f172a; border-bottom: 1px solid #1e293b; }}
  .filter-btn {{ background: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 6px 14px; border-radius: 20px; cursor: pointer; font-size: 0.8rem; transition: all 0.15s; }}
  .filter-btn:hover, .filter-btn.active {{ background: #38bdf8; color: #0f172a; border-color: #38bdf8; font-weight: 600; }}

  .container {{ padding: 24px 32px; display: grid; grid-template-columns: repeat(auto-fill, minmax(520px, 1fr)); gap: 20px; }}

  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 20px; transition: transform 0.15s, box-shadow 0.15s; }}
  .card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }}
  .card.high-impact {{ border-color: #ef4444; border-width: 2px; background: #1e1a1a; }}

  .card-header {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }}
  .type-tag {{ color: #fff; font-size: 0.72rem; font-weight: 700; padding: 3px 10px; border-radius: 20px; }}
  .badge {{ font-size: 0.7rem; font-weight: 700; padding: 3px 9px; border-radius: 20px; }}
  .badge.high {{ background: #7f1d1d; color: #fca5a5; }}
  .badge.ai {{ background: #1e3a5f; color: #7dd3fc; }}
  .badge.tmpl {{ background: #1e293b; color: #64748b; border: 1px solid #334155; }}
  .dilution {{ font-size: 0.72rem; color: #fb923c; font-weight: 600; margin-left: auto; }}
  .date {{ font-size: 0.75rem; color: #64748b; margin-left: auto; }}

  .corp {{ font-size: 1rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }}
  .title {{ font-size: 0.85rem; color: #94a3b8; font-weight: 400; margin-bottom: 14px; line-height: 1.4; }}

  .summary {{ font-size: 0.82rem; line-height: 1.65; color: #cbd5e1; }}
  .summary p {{ margin-bottom: 4px; }}
  .summary .sec {{ font-weight: 600; margin-top: 10px; padding: 6px 10px; border-radius: 6px; }}
  .summary .cash {{ background: #0c4a1e; color: #86efac; }}
  .summary .risk {{ background: #450a0a; color: #fca5a5; }}
  .summary .hidden {{ background: #1e1b4b; color: #c4b5fd; }}
  .summary .verdict {{ background: #1c1917; color: #fde68a; border-left: 3px solid #fbbf24; }}
  .summary .concept {{ background: #0c3443; color: #7dd3fc; }}
  .summary .bullet {{ padding-left: 16px; color: #94a3b8; }}

  .empty {{ color: #64748b; text-align: center; padding: 60px; font-size: 1rem; }}
  footer {{ text-align: center; color: #334155; font-size: 0.75rem; padding: 24px; }}
</style>
</head>
<body>

<header>
  <h1>Disclose<span>AI</span> — 공시 리포트</h1>
  <span class="meta">최근 {days}일 · 생성: {generated_at}</span>
</header>

<div class="stats">
  <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">전체 공시</div></div>
  <div class="stat danger"><div class="stat-num">{high_count}</div><div class="stat-label">HIGH IMPACT</div></div>
  <div class="stat green"><div class="stat-num">{ai_count}</div><div class="stat-label">AI 분석 완료</div></div>
  <div class="stat"><div class="stat-num">{corps}</div><div class="stat-label">기업 수</div></div>
</div>

<div class="filter-bar">
  <button class="filter-btn active" onclick="filterCards('all', this)">전체</button>
  <button class="filter-btn" onclick="filterCards('high-impact', this)">⚠ HIGH IMPACT</button>
  <button class="filter-btn" onclick="filterCards('증자', this)">증자</button>
  <button class="filter-btn" onclick="filterCards('전환사채', this)">전환사채</button>
  <button class="filter-btn" onclick="filterCards('BW', this)">BW</button>
  <button class="filter-btn" onclick="filterCards('실적', this)">실적</button>
  <button class="filter-btn" onclick="filterCards('계약', this)">계약</button>
  <button class="filter-btn" onclick="filterCards('M&amp;A/분할', this)">M&A/분할</button>
  <button class="filter-btn" onclick="filterCards('CAPEX', this)">CAPEX</button>
  <button class="filter-btn" onclick="filterCards('임원변동', this)">임원변동</button>
</div>

<div class="container" id="card-container">
{cards_html}
</div>

<footer>DiscloseAI · 본 리포트는 참고용이며 투자 조언이 아닙니다.</footer>

<script>
function filterCards(type, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  document.querySelectorAll('.card').forEach(card => {{
    if (type === 'all') {{
      card.style.display = '';
    }} else if (type === 'high-impact') {{
      card.style.display = card.classList.contains('high-impact') ? '' : 'none';
    }} else {{
      const tag = card.querySelector('.type-tag');
      card.style.display = (tag && tag.textContent.trim() === type) ? '' : 'none';
    }}
  }});
}}
</script>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="최근 N일 (기본 7)")
    parser.add_argument("--out", type=str, default="", help="출력 파일 경로")
    args = parser.parse_args()

    print(f"[리포트 생성] 최근 {args.days}일 공시 조회 중...")
    html = generate(days=args.days)

    out_path = args.out or os.path.join(
        os.path.dirname(__file__), f"report_{datetime.today().strftime('%Y%m%d')}.html"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[완료] {out_path}")


if __name__ == "__main__":
    main()
