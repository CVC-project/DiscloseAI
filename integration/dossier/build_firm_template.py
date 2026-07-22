"""firm.html 템플릿 빌드 — financial 의 _HTML_TEMPLATE 에서 '데이터 주도' 단일 템플릿 생성.

배경 (docs/ARCHITECTURE.md 알려진 문제 #2):
  기존엔 기업마다 데이터가 인라인된 firm_<ticker>.html(완성본)을 iframe으로 임베드했다.
  이를 "데이터(JSON) + 단일 템플릿(firm.html)"로 분리한다. 템플릿은 financial 의
  _HTML_TEMPLATE 와 **CSS·렌더 로직이 바이트 동일**해야 한다(픽셀 불변 보장).

방식 (integration-only, financial 코드 무수정):
  1. modules.financial.dashboard._HTML_TEMPLATE 를 read-only import (서빙 계층 예외 — integration/CLAUDE.md).
  2. 6개 헤더 placeholder + data_json 을 마커로 렌더(.format).
  3. 딱 두 가지만 변경:
     (a) 헤더 6개 지점 → id hook (JS가 DATA._hdr 로 채움)
     (b) `const DATA = {...}` → `let DATA=null` + 렌더 코드를 __renderFirm()로 감싸 fetch 완료 후 실행
  4. CSS·body 구조·차트 옵션·렌더 함수는 전부 그대로 → 출력 동일.

각 치환은 발생 횟수를 assert 한다(원본 구조가 바뀌면 빌드가 시끄럽게 실패).

실행 (repo 루트에서):
  python integration/dossier/build_firm_template.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_OUT = os.path.join(_HERE, "firm.html")

sys.path.insert(0, _ROOT)
from modules.financial.dashboard import (
    _HTML_TEMPLATE,
)  # noqa: E402  (서빙 계층 read-only import)


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(
            f"[build 실패] '{label}': 예상 1회, 실제 {n}회 매칭.\n"
            f"  → _HTML_TEMPLATE 구조가 바뀌었을 수 있음. 패턴 확인 필요:\n  {old[:120]!r}"
        )
    return text.replace(old, new)


# JS: 부트스트랩(fetch + 헤더 주입 + 렌더 호출). __renderFirm 본문은 원본 렌더 코드.
# 주의: 따옴표 없는 폰트만 사용 — 작은따옴표 JS 문자열 안에 들어가므로 인용부호 금지.
_MSG_STYLE = (
    "color:#94a3b8;font-family:sans-serif;"
    "padding:48px;text-align:center;font-size:15px;line-height:1.6"
)
_DATA_OPEN = (
    "let DATA = null;\n"
    "function __setText(id, t){ var e = document.getElementById(id); if (e) e.textContent = t; }\n"
    "function __renderFirm() {"
)
_BOOTSTRAP_CLOSE = (
    "}\n"
    "async function __bootstrapFirm() {\n"
    "  var p = new URLSearchParams(location.search);\n"
    "  var ticker = p.get('ticker');\n"
    "  var ver = p.get('v') || '';\n"
    f"  if (!ticker) {{ document.body.innerHTML = '<div style=\"{_MSG_STYLE}\">기업 코드(ticker)가 지정되지 않았습니다.</div>'; return; }}\n"
    "  try {\n"
    "    var res = await fetch('./data/firm_' + ticker + '.json' + (ver ? '?v=' + ver : ''));\n"
    "    if (!res.ok) throw new Error('HTTP ' + res.status);\n"
    "    DATA = await res.json();\n"
    "  } catch (e) {\n"
    f"    document.body.innerHTML = '<div style=\"{_MSG_STYLE}\">기업 데이터를 찾을 수 없습니다 (' + ticker + ').</div>';\n"
    "    return;\n"
    "  }\n"
    "  var h = DATA._hdr || {};\n"
    "  document.title = 'DiscloseAI — ' + (h.corp_name || '') + ' 이익 해부';\n"
    "  __setText('fCorpName', h.corp_name || '');\n"
    "  __setText('fCorpCode', h.corp_code || '');\n"
    "  __setText('fYearRange', h.year_range || '');\n"
    "  __setText('fTotal', (h.total != null) ? h.total : '');\n"
    "  var g = document.getElementById('fGrade');\n"
    "  if (g) { g.className = 'grade grade-' + (h.grade || 'F'); g.textContent = h.grade || ''; }\n"
    "  __renderFirm();\n"
    "}\n"
    "__bootstrapFirm();\n"
    "</script>"
)


def main() -> int:
    # 1) 마커로 렌더 (literal {{ }} 는 .format 이 { } 로 환원)
    html = _HTML_TEMPLATE.format(
        corp_name="%%CN%%",
        corp_code="%%CC%%",
        year_range="%%YR%%",
        total="%%TOT%%",
        grade="%%GR%%",
        data_json="%%DATA%%",
    )

    # 2a) 헤더 6개 지점 → id hook
    html = _replace_once(
        html,
        "<title>DiscloseAI — %%CN%% 이익 해부</title>",
        "<title>DiscloseAI — 기업 이익 해부</title>",
        "title",
    )
    html = _replace_once(
        html,
        '<h1>%%CN%% <span style="color:var(--muted);font-size:18px;">(%%CC%%)</span></h1>',
        '<h1><span id="fCorpName"></span> <span style="color:var(--muted);font-size:18px;">(<span id="fCorpCode"></span>)</span></h1>',
        "h1 corp name/code",
    )
    html = _replace_once(
        html,
        '<div style="font-size:18px;font-weight:600;">%%YR%%</div>',
        '<div style="font-size:18px;font-weight:600;" id="fYearRange"></div>',
        "year_range",
    )
    html = _replace_once(
        html,
        '<span class="score-big">%%TOT%%</span>',
        '<span class="score-big" id="fTotal"></span>',
        "total score",
    )
    html = _replace_once(
        html,
        '<span class="grade grade-%%GR%%">%%GR%%</span>',
        '<span class="grade" id="fGrade"></span>',
        "grade badge",
    )

    # 잔여 마커 없는지 확인
    for marker in ("%%CN%%", "%%CC%%", "%%YR%%", "%%TOT%%", "%%GR%%"):
        if marker in html:
            raise SystemExit(f"[build 실패] 잔여 마커 발견: {marker}")

    # 2b) const DATA = {...}; → let DATA=null + __renderFirm() 래퍼 시작
    html = _replace_once(html, "const DATA = %%DATA%%;", _DATA_OPEN, "const DATA line")

    # 2b-cont) 데이터 스크립트 블록의 닫는 </script> 앞에 래퍼 종료 + 부트스트랩 삽입
    #   (head 의 Chart.js <script src>…</script> 가 아닌 '마지막' </script> 를 타깃)
    idx = html.rfind("</script>")
    if idx == -1:
        raise SystemExit("[build 실패] 닫는 </script> 를 찾지 못함")
    html = html[:idx] + _BOOTSTRAP_CLOSE + html[idx + len("</script>") :]

    with open(_OUT, "w", encoding="utf-8") as fp:
        fp.write(html)
    print(f"[done] 템플릿 생성 → {_OUT} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
