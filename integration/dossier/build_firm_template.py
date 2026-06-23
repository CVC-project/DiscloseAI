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


_GLOSS_FALLBACK_SNIPPET = r"""
<style>
.gloss-sel-btn {
  position: absolute; z-index: 100001;
  background: linear-gradient(135deg, rgba(94,234,212,0.18), rgba(167,139,250,0.18));
  border: 1px solid rgba(94,234,212,0.55); color: #5eead4;
  padding: 6px 11px; border-radius: 14px;
  font: 600 11.5px/1.2 inherit; cursor: pointer;
  box-shadow: 0 6px 18px rgba(0,0,0,0.5), 0 0 12px rgba(94,234,212,0.2);
  white-space: nowrap; user-select: none;
}
.gloss-sel-btn:hover { background: linear-gradient(135deg, rgba(94,234,212,0.28), rgba(167,139,250,0.28)); }
.gloss-sel-btn:disabled { opacity: 0.6; cursor: wait; }
.gloss-tip {
  position: absolute; z-index: 100000;
  background: rgba(8,12,28,0.97); color: #e2e8f0;
  border: 1px solid rgba(94,234,212,0.4); border-radius: 10px;
  padding: 12px 14px; font-size: 11.5px; line-height: 1.65;
  box-shadow: 0 10px 28px rgba(0,0,0,0.55); max-height: 60vh; overflow-y: auto;
}
.gloss-tip-label { font-size: 13px; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
.gloss-tip-cat {
  display: inline-block; font-size: 9px; color: #fbbf24;
  border: 1px solid rgba(251,191,36,0.3); padding: 1px 6px; border-radius: 8px;
  letter-spacing: .08em; text-transform: uppercase; margin-bottom: 8px;
}
.gloss-tip-desc { color: #cbd5e1; white-space: pre-wrap; }
</style>
<script>
/* Glossary Bedrock 폴백 — iframe(firm 도시에) 안에서 텍스트 드래그 시 AI 풀이.
   integration/dossier/build_firm_template.py 가 빌드 시 주입. 의존성 없음(vanilla JS).
   글로스 사전(integration/data/glossary.json)에 이미 있는 단어는 스킵. */
(function() {
  var CHAT_URL = 'http://localhost:8001/integration/chat';
  var GLOSS_ALIASES = new Set();
  var CACHE = new Map();
  var btnEl = null, tipEl = null;

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function hideBtn() { if (btnEl) { btnEl.remove(); btnEl = null; } }
  function hideTip() { if (tipEl) { tipEl.remove(); tipEl = null; } }

  function showBtn(rect, term) {
    hideBtn();
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'gloss-sel-btn';
    var disp = term.length > 14 ? term.slice(0, 14) + '…' : term;
    btn.textContent = '✨ "' + disp + '" 풀이 받기';
    var left = rect.left + window.scrollX;
    left = Math.max(8, Math.min(window.innerWidth - 240, left));
    var top = rect.bottom + window.scrollY + 6;
    btn.style.left = left + 'px';
    btn.style.top = top + 'px';
    btn.addEventListener('mousedown', function(e) { e.stopPropagation(); });
    btn.addEventListener('click', function() { fetchFallback(term, btn); });
    document.body.appendChild(btn);
    btnEl = btn;
  }

  function showTip(anchorEl, entry) {
    hideTip();
    var tip = document.createElement('div');
    tip.className = 'gloss-tip';
    var html = '<div class="gloss-tip-label">' + esc(entry.label) + '</div>';
    if (entry.category) html += '<div class="gloss-tip-cat">' + esc(entry.category) + '</div>';
    if (entry.description) html += '<div class="gloss-tip-desc">' + esc(entry.description) + '</div>';
    tip.innerHTML = html;
    document.body.appendChild(tip);
    var r = anchorEl.getBoundingClientRect();
    var w = Math.min(340, window.innerWidth - 16);
    tip.style.width = w + 'px';
    var left = r.left + window.scrollX;
    left = Math.max(8, Math.min(window.innerWidth - w - 8, left));
    var top = r.bottom + window.scrollY + 6;
    if (top + tip.offsetHeight > window.scrollY + window.innerHeight - 8) {
      top = r.top + window.scrollY - tip.offsetHeight - 4;
    }
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
    tipEl = tip;
  }

  function fetchFallback(term, btn) {
    var t = String(term || '').trim();
    if (!t) return;
    if (CACHE.has(t)) { showTip(btn, CACHE.get(t)); return; }
    btn.disabled = true;
    btn.textContent = '🔄 풀이 받는 중…';
    var sysp = '당신은 주식 투자 초보(주린이)를 위한 친절한 용어 풀이 도우미입니다. ' +
      '주어진 용어를 1~3문장(80~150자)으로 쉽게 풀어 설명하세요. ' +
      '어려운 회계·법률 용어는 한 줄로 더 풀어주고, 가능하면 짧은 비유도 곁들이세요. ' +
      '"사세요/파세요/매수 추천" 같은 투자 권유는 절대 하지 마세요.';
    fetch(CHAT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: '"' + t + '"의 뜻을 풀어주세요.',
        system_prompt: sysp, history: [], context: {}
      })
    }).then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function(data) {
      var text = (data.text || '').trim();
      if (!text) throw new Error('빈 응답');
      var entry = { label: t, category: 'AI 풀이', description: text };
      CACHE.set(t, entry);
      showTip(btn, entry);
    }).catch(function(e) {
      btn.disabled = false;
      btn.textContent = '⚠ 실패: ' + (e.message || e);
      setTimeout(hideBtn, 2400);
    });
  }

  // 글로스 사전 별칭 로드 (있으면 중복 wrap 스킵)
  fetch('../data/glossary.json')
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(j) {
      if (!j || !j.entries) return;
      Object.keys(j.entries).forEach(function(k) {
        var label = String((j.entries[k] || {}).label || '');
        var m = label.match(/\(([^)]+)\)/);
        var main = label.replace(/\s*\([^)]+\)\s*/g, '').trim();
        if (main && main.length >= 2 && main.indexOf('·') < 0) GLOSS_ALIASES.add(main);
        if (m && m[1] && m[1].length >= 2 && m[1].indexOf('·') < 0) GLOSS_ALIASES.add(m[1].trim());
      });
    })
    .catch(function() {});

  document.addEventListener('mouseup', function() {
    setTimeout(function() {
      var sel = window.getSelection && window.getSelection();
      if (!sel || sel.isCollapsed) return;
      var term = sel.toString().trim();
      if (term.length < 2 || term.length > 50) return;
      if (GLOSS_ALIASES.has(term)) return;
      var node = sel.anchorNode;
      if (node && node.nodeType === 3) node = node.parentElement;
      if (node && node.closest && (node.closest('.gloss-sel-btn') || node.closest('.gloss-tip'))) return;
      var range = sel.getRangeAt(0);
      var rect = range.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) return;
      showBtn(rect, term);
    }, 10);
  });

  document.addEventListener('mousedown', function(e) {
    if (btnEl && (btnEl === e.target || btnEl.contains(e.target))) return;
    if (tipEl && (tipEl === e.target || tipEl.contains(e.target))) return;
    hideBtn();
    hideTip();
  });
})();
</script>
"""


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

    # 3) 글로스 폴백 스니펫 주입 (모듈 ① 확장 — firm 도시에 안에서도 텍스트 드래그 → AI 풀이)
    #    Codex의 financial 템플릿엔 없는 기능이라 integration이 후처리로 덧붙임.
    #    iframe 내부에서도 자체 mouseup·fetch 동작. 의존성 없음(순수 vanilla JS).
    html = html.replace("</body>", _GLOSS_FALLBACK_SNIPPET + "\n</body>", 1)

    with open(_OUT, "w", encoding="utf-8") as fp:
        fp.write(html)
    print(f"[done] 템플릿 생성 → {_OUT} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
