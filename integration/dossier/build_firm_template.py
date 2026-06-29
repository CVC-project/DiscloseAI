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


_FULLTEXT_VIEWER_SNIPPET = r"""
<style>
.ft-overlay {
  position: fixed; inset: 0; z-index: 99500;
  background: rgba(2,6,23,0.92); backdrop-filter: blur(6px);
  display: none; align-items: center; justify-content: center; padding: 24px;
}
.ft-overlay.open { display: flex; }
.ft-modal {
  background: #0b1224; border: 1px solid rgba(94,234,212,0.25);
  border-radius: 12px; width: 100%; max-width: 1180px;
  max-height: 94vh; display: flex; flex-direction: column;
  box-shadow: 0 24px 60px rgba(0,0,0,0.6); color: #e2e8f0;
}
.ft-header {
  padding: 16px 22px 14px;
  border-bottom: 1px solid rgba(94,234,212,0.12);
  display: flex; align-items: center; gap: 12px; flex-shrink: 0;
}
.ft-title { font-size: 16px; font-weight: 700; color: #f1f5f9; }
.ft-meta { font-size: 12px; color: #94a3b8; flex: 1; }
.ft-close {
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
  color: #e2e8f0; width: 30px; height: 30px; border-radius: 50%;
  cursor: pointer; font-size: 14px; flex-shrink: 0;
}
.ft-close:hover { background: rgba(248,113,113,0.18); border-color: rgba(248,113,113,0.5); color: #f87171; }
.ft-body {
  display: grid; grid-template-columns: 260px 1fr; gap: 0;
  flex: 1; min-height: 0; overflow: hidden;
}
.ft-tree {
  border-right: 1px solid rgba(94,234,212,0.1);
  overflow-y: auto; padding: 10px 0; background: rgba(8,12,28,0.5);
}
.ft-tree-item {
  padding: 7px 14px; cursor: pointer; font-size: 12.5px;
  color: #cbd5e1; line-height: 1.4; border-left: 2px solid transparent;
}
.ft-tree-item:hover { background: rgba(94,234,212,0.06); color: #e2e8f0; }
.ft-tree-item.active {
  background: rgba(94,234,212,0.12); color: #5eead4;
  border-left-color: #5eead4; font-weight: 600;
}
.ft-tree-item.sub { padding-left: 28px; font-size: 11.5px; color: #94a3b8; }
.ft-tree-item.sub.active { color: #5eead4; }
.ft-content {
  overflow-y: auto; padding: 20px 28px; font-size: 13.5px;
  line-height: 1.75; color: #cbd5e1;
}
.ft-section-title {
  font-size: 18px; font-weight: 700; color: #f1f5f9;
  margin: 0 0 14px; padding-bottom: 8px;
  border-bottom: 1px solid rgba(94,234,212,0.15);
}
.ft-paragraph { margin: 10px 0; white-space: pre-wrap; }
.ft-table-wrap { margin: 14px 0; overflow-x: auto; }
.ft-table {
  border-collapse: collapse; font-size: 12px; min-width: 100%;
  background: rgba(8,12,28,0.5);
}
.ft-table th, .ft-table td {
  border: 1px solid rgba(94,234,212,0.12);
  padding: 6px 9px; vertical-align: top; text-align: left;
}
.ft-table th {
  background: rgba(94,234,212,0.08); color: #5eead4;
  font-weight: 600; font-size: 11.5px;
}
.ft-table tbody tr:nth-child(even) { background: rgba(255,255,255,0.02); }
.ft-error {
  color: #f87171; padding: 24px; font-size: 13px; line-height: 1.7;
}
.ft-error code {
  background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 3px;
  color: #fbbf24; font-family: 'Courier New', monospace; font-size: 11.5px;
}
.ft-hint {
  padding: 24px; color: #94a3b8; font-size: 13px; text-align: center;
}
</style>
<div class="ft-overlay" id="ftOverlay">
  <div class="ft-modal">
    <div class="ft-header">
      <div class="ft-title">📄 사업보고서 본문</div>
      <div class="ft-meta" id="ftMeta">로딩…</div>
      <button class="ft-close" type="button" id="ftClose">✕</button>
    </div>
    <div class="ft-body">
      <div class="ft-tree" id="ftTree"></div>
      <div class="ft-content" id="ftContent"></div>
    </div>
  </div>
</div>
<script>
/* 사업보고서 본문 뷰어 (모듈 ③ 1c).
   - DATA._hdr.corp_code → fetch index.json → 해당 회사 rcept_no
   - fetch parsed.json → 좌측 트리 + 우측 본문 렌더
   - 본문 안에서 텍스트 드래그 → 기존 셀렉션 폴백 자동 작동 (gloss-sel-btn) */
(function() {
  var parsed = null;
  var overlayEl, treeEl, contentEl, metaEl;

  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function show() { overlayEl.classList.add('open'); }
  function hide() { overlayEl.classList.remove('open'); }

  function findNode(id) {
    var parts = id.split('/').map(function(x) { return parseInt(x, 10); });
    var node = parsed.chapters[parts[0]];
    for (var i = 1; i < parts.length; i++) {
      if (!node || !node.children) return null;
      node = node.children[parts[i]];
    }
    return node || null;
  }

  function renderTree() {
    treeEl.innerHTML = '';
    parsed.chapters.forEach(function(ch, i) {
      var item = document.createElement('div');
      item.className = 'ft-tree-item';
      item.dataset.id = String(i);
      item.textContent = ch.title || ('챕터 ' + (i + 1));
      item.addEventListener('click', function() { selectNode(String(i)); });
      treeEl.appendChild(item);
      (ch.children || []).forEach(function(sub, j) {
        var s = document.createElement('div');
        s.className = 'ft-tree-item sub';
        s.dataset.id = i + '/' + j;
        s.textContent = sub.title || ('절 ' + (j + 1));
        s.addEventListener('click', function() { selectNode(i + '/' + j); });
        treeEl.appendChild(s);
      });
    });
  }

  function selectNode(id) {
    var items = treeEl.querySelectorAll('.ft-tree-item');
    items.forEach(function(it) {
      it.classList.toggle('active', it.dataset.id === id);
    });
    var node = findNode(id);
    if (!node) {
      contentEl.innerHTML = '<div class="ft-error">노드를 찾을 수 없습니다.</div>';
      return;
    }
    var html = '<h3 class="ft-section-title">' + escHtml(node.title || '') + '</h3>';
    if (!(node.paragraphs || []).length && !(node.tables || []).length) {
      html += '<div class="ft-hint">이 섹션엔 본문 텍스트·표가 없어요. 좌측에서 하위 절을 골라보세요.</div>';
    }
    (node.paragraphs || []).forEach(function(p) {
      html += '<p class="ft-paragraph">' + escHtml(p) + '</p>';
    });
    (node.tables || []).forEach(function(t) {
      html += '<div class="ft-table-wrap"><table class="ft-table">';
      if (t.headers && t.headers.length) {
        html += '<thead>';
        t.headers.forEach(function(hr) {
          html += '<tr>';
          hr.forEach(function(c) { html += '<th>' + escHtml(c) + '</th>'; });
          html += '</tr>';
        });
        html += '</thead>';
      }
      if (t.rows && t.rows.length) {
        html += '<tbody>';
        t.rows.forEach(function(r) {
          html += '<tr>';
          r.forEach(function(c) { html += '<td>' + escHtml(c) + '</td>'; });
          html += '</tr>';
        });
        html += '</tbody>';
      }
      html += '</table></div>';
    });
    contentEl.innerHTML = html;
    contentEl.scrollTop = 0;
  }

  function loadData() {
    // 부트스트랩이 DATA를 let 선언이라 window.DATA로 못 보지만, #fCorpCode 텍스트엔 들어가 있음.
    var corpCodeEl = document.getElementById('fCorpCode');
    var corpNameEl = document.getElementById('fCorpName');
    var corpCode = (corpCodeEl && corpCodeEl.textContent.trim()) || '';
    var corpName = (corpNameEl && corpNameEl.textContent.trim()) || '';
    if (!corpCode) {
      contentEl.innerHTML =
        '<div class="ft-error">corp_code를 찾을 수 없습니다.<br>' +
        '<span style="color:#94a3b8">기업 데이터 로딩이 끝난 뒤 다시 눌러주세요.</span></div>';
      return;
    }
    contentEl.innerHTML = '<div class="ft-hint">사업보고서 본문을 불러오는 중…</div>';
    treeEl.innerHTML = '';
    metaEl.textContent = '로딩…';

    var indexUrl = '../../modules/disclosure/data/fulltext/index.json';
    var entry = null;
    fetch(indexUrl)
      .then(function(r) {
        if (!r.ok) throw new Error('index 없음 (status ' + r.status + ')');
        return r.json();
      })
      .then(function(idx) {
        entry = idx[corpCode];
        if (!entry) {
          throw new Error('이 회사의 사업보고서 본문은 아직 수집되지 않았습니다.\n(corp_code: ' + corpCode + ')');
        }
        metaEl.textContent =
          entry.corp_name + ' · ' + entry.report_nm + ' (' + entry.rcept_dt + ')';
        return fetch('../../modules/disclosure/data/fulltext/' + corpCode + '/' + entry.rcept_no + '/parsed.json');
      })
      .then(function(r) {
        if (!r.ok) throw new Error('parsed.json fetch 실패 (status ' + r.status + ')');
        return r.json();
      })
      .then(function(data) {
        parsed = data;
        renderTree();
        if (parsed.chapters && parsed.chapters.length) selectNode('0');
        else contentEl.innerHTML = '<div class="ft-hint">챕터가 비어있어요.</div>';
      })
      .catch(function(e) {
        metaEl.textContent = '';
        contentEl.innerHTML =
          '<div class="ft-error">⚠ ' + escHtml(e.message) +
          '<br><br>로컬에서 수집·파싱을 먼저 실행해주세요:' +
          '<br><code>python -m modules.disclosure.fulltext_collector</code>' +
          '<br><code>python -m modules.disclosure.fulltext_parser</code></div>';
      });
  }

  function init() {
    overlayEl = document.getElementById('ftOverlay');
    treeEl = document.getElementById('ftTree');
    contentEl = document.getElementById('ftContent');
    metaEl = document.getElementById('ftMeta');
    var closeBtn = document.getElementById('ftClose');
    var openBtn = document.getElementById('ftBtn');
    if (!overlayEl || !openBtn) return;
    closeBtn.addEventListener('click', hide);
    overlayEl.addEventListener('click', function(e) { if (e.target === overlayEl) hide(); });
    openBtn.addEventListener('click', function() { show(); loadData(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
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

    # 3) 사업보고서 본문 뷰어 (모듈 ③ 1c) — EQS action-row에 진입 버튼 + 본문 모달
    _ft_button = (
        '<button class="ghost-btn" type="button" id="ftBtn" '
        'style="border-color:rgba(94,234,212,0.45);color:#5eead4">'
        "📄 사업보고서 본문</button>\n        "
    )
    html = _replace_once(
        html,
        '<a class="ghost-btn" id="dartReportBtn"',
        _ft_button + '<a class="ghost-btn" id="dartReportBtn"',
        "fulltext button in action-row",
    )
    html = html.replace("</body>", _FULLTEXT_VIEWER_SNIPPET + "\n</body>", 1)

    with open(_OUT, "w", encoding="utf-8") as fp:
        fp.write(html)
    print(f"[done] 템플릿 생성 → {_OUT} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
