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


_REFERENCE_PANEL_SNIPPET = r"""
<style>
.rp-overlay {
  position: fixed; inset: 0; z-index: 99400;
  background: rgba(2,6,23,0.92); backdrop-filter: blur(6px);
  display: none; align-items: center; justify-content: center; padding: 24px;
}
.rp-overlay.open { display: flex; }
.rp-modal {
  background: #0b1224; border: 1px solid rgba(167,139,250,0.3);
  border-radius: 12px; width: 100%; max-width: 1080px;
  max-height: 94vh; display: flex; flex-direction: column;
  box-shadow: 0 24px 60px rgba(0,0,0,0.6); color: #e2e8f0;
}
.rp-header {
  padding: 16px 22px 14px;
  border-bottom: 1px solid rgba(167,139,250,0.18);
  display: flex; align-items: center; gap: 12px; flex-shrink: 0;
}
.rp-title { font-size: 16px; font-weight: 700; color: #f1f5f9; }
.rp-meta { font-size: 12px; color: #94a3b8; flex: 1; }
.rp-close {
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
  color: #e2e8f0; width: 30px; height: 30px; border-radius: 50%;
  cursor: pointer; font-size: 14px; flex-shrink: 0;
}
.rp-close:hover { background: rgba(248,113,113,0.18); border-color: rgba(248,113,113,0.5); color: #f87171; }
.rp-body {
  overflow-y: auto; padding: 22px 28px; font-size: 13.5px;
  line-height: 1.7; color: #cbd5e1; min-height: 0;
}
.rp-section { margin: 0 0 24px; }
.rp-section h3 {
  margin: 0 0 12px; font-size: 14px; color: #a78bfa;
  font-weight: 600; letter-spacing: 0.3px;
  text-transform: uppercase;
}
.rp-notes {
  background: rgba(167,139,250,0.06);
  border: 1px solid rgba(167,139,250,0.15);
  border-radius: 10px; padding: 16px 18px;
  font-size: 14px; line-height: 1.85; color: #e2e8f0;
}
.rp-fin-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}
.rp-fin-card {
  background: rgba(8,12,28,0.55);
  border: 1px solid rgba(94,234,212,0.15);
  border-radius: 10px; padding: 13px 15px;
}
.rp-fin-item {
  color: #94a3b8; font-size: 12px; font-weight: 600;
  letter-spacing: 0.2px; margin-bottom: 4px;
}
.rp-fin-value {
  color: #f1f5f9; font-size: 19px; font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.rp-fin-yoy { color: #5eead4; font-size: 12.5px; font-weight: 600; margin-left: 6px; }
.rp-fin-yoy.neg { color: #f87171; }
.rp-fin-explain { color: #cbd5e1; font-size: 12px; margin-top: 6px; line-height: 1.5; }
.rp-seg-list {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
}
.rp-seg {
  background: rgba(8,12,28,0.45);
  border: 1px solid rgba(94,234,212,0.12);
  border-radius: 8px; padding: 10px 13px;
}
.rp-seg-name {
  font-weight: 700; color: #5eead4; font-size: 13.5px;
  display: flex; align-items: baseline; gap: 8px;
}
.rp-seg-share {
  color: #94a3b8; font-size: 11.5px; font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.rp-seg-desc { color: #cbd5e1; font-size: 12px; margin-top: 4px; line-height: 1.5; }
.rp-chips {
  display: flex; flex-wrap: wrap; gap: 6px;
}
.rp-chip {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 999px; padding: 4px 11px;
  font-size: 12px; color: #cbd5e1;
}
.rp-empty {
  color: #64748b; font-size: 12.5px; font-style: italic;
  padding: 10px 0;
}
.rp-disclaimer {
  margin-top: 18px; padding: 11px 14px;
  background: rgba(248,113,113,0.05);
  border: 1px solid rgba(248,113,113,0.15);
  border-radius: 8px;
  color: #94a3b8; font-size: 11.5px; line-height: 1.6;
}
.rp-error { color: #f87171; padding: 24px; font-size: 13px; line-height: 1.7; }
.rp-error code {
  background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 3px;
  color: #fbbf24; font-family: 'Courier New', monospace; font-size: 11.5px;
}
.rp-hint { padding: 24px; color: #94a3b8; font-size: 13px; text-align: center; }
</style>
<div class="rp-overlay" id="rpOverlay">
  <div class="rp-modal">
    <div class="rp-header">
      <div class="rp-title">📚 회사 참고서</div>
      <div class="rp-meta" id="rpMeta">로딩…</div>
      <button class="rp-close" type="button" id="rpClose">✕</button>
    </div>
    <div class="rp-body" id="rpBody"></div>
  </div>
</div>
<script>
/* 회사 참고서 패널 (모듈 ③ 2c).
   - DATA._hdr.corp_code → fetch index.json → rcept_no
   - fetch summary.json → 재무 카드·사업부문·요약 단락 렌더
   - kam·emphasis는 감사보고서 수집 후속에서 채움 (현재 비어있어 placeholder) */
(function() {
  var overlayEl, bodyEl, metaEl;

  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function show() { overlayEl.classList.add('open'); }
  function hide() { overlayEl.classList.remove('open'); }

  function renderNotes(notes) {
    if (!notes) return '';
    return '<div class="rp-section">' +
           '<h3>한눈에 보기</h3>' +
           '<div class="rp-notes">' + escHtml(notes) + '</div>' +
           '</div>';
  }
  function renderFinancials(list) {
    if (!list || !list.length) {
      return '<div class="rp-section"><h3>재무 핵심</h3>' +
             '<div class="rp-empty">재무 정보가 아직 추출되지 않았어요.</div></div>';
    }
    var cards = list.map(function(f) {
      var yoyCls = (f.yoy && /^[-]/.test(String(f.yoy))) ? 'rp-fin-yoy neg' : 'rp-fin-yoy';
      var yoyHtml = f.yoy ? ' <span class="' + yoyCls + '">' + escHtml(f.yoy) + '</span>' : '';
      return '<div class="rp-fin-card">' +
             '<div class="rp-fin-item">' + escHtml(f.item) + '</div>' +
             '<div class="rp-fin-value">' + escHtml(f.value) + yoyHtml + '</div>' +
             (f.explain ? '<div class="rp-fin-explain">' + escHtml(f.explain) + '</div>' : '') +
             '</div>';
    }).join('');
    return '<div class="rp-section"><h3>재무 핵심</h3>' +
           '<div class="rp-fin-grid">' + cards + '</div></div>';
  }
  function renderSegments(list) {
    if (!list || !list.length) return '';
    var cards = list.map(function(s) {
      var shareTxt = (s.revenue_share != null) ?
        '· 매출비중 ' + Math.round(s.revenue_share * 100) + '%' : '';
      return '<div class="rp-seg">' +
             '<div class="rp-seg-name">' + escHtml(s.name || '') +
             '<span class="rp-seg-share">' + shareTxt + '</span></div>' +
             (s.desc ? '<div class="rp-seg-desc">' + escHtml(s.desc) + '</div>' : '') +
             '</div>';
    }).join('');
    return '<div class="rp-section"><h3>사업 부문</h3>' +
           '<div class="rp-seg-list">' + cards + '</div></div>';
  }
  function renderProducts(list) {
    if (!list || !list.length) return '';
    var chips = list.map(function(p) {
      return '<span class="rp-chip">' + escHtml(p) + '</span>';
    }).join('');
    return '<div class="rp-section"><h3>주요 제품·서비스</h3>' +
           '<div class="rp-chips">' + chips + '</div></div>';
  }
  function renderAudit(kam, emphasis) {
    var hasContent = (kam && kam.length) || (emphasis && emphasis.length);
    if (hasContent) {
      // 향후 감사보고서 수집 PR에서 카드 렌더로 교체. 지금은 placeholder 유지.
      return '<div class="rp-section"><h3>감사보고서 풀이</h3>' +
             '<div class="rp-empty">감사보고서 데이터 표시 — TODO</div></div>';
    }
    return '<div class="rp-section"><h3>감사보고서 풀이</h3>' +
           '<div class="rp-empty">감사보고서(KAM·강조사항) 수집은 다음 단계에 추가됩니다.</div></div>';
  }
  function renderGlossary(list) {
    if (!list || !list.length) return '';
    var chips = list.map(function(t) {
      return '<span class="rp-chip">' + escHtml(t) + '</span>';
    }).join('');
    return '<div class="rp-section"><h3>이 보고서에 등장한 공시 용어</h3>' +
           '<div class="rp-chips">' + chips + '</div></div>';
  }
  function renderDisclaimer(meta) {
    var src = '';
    if (meta && meta.rcept_dt) {
      src = '출처: ' + escHtml(meta.rcept_dt.slice(0, 4)) + '년 사업보고서';
      if (meta.model_used) src += ' · 생성 모델: ' + escHtml(meta.model_used);
    }
    return '<div class="rp-disclaimer">' +
           '⚠ 본 페이지는 과거 공시·재무정보를 AI가 정리한 <b>참고 정보</b>입니다. ' +
           '투자 조언이 아니며, 수치·해석에 오차가 있을 수 있어요.' +
           (src ? '<br>' + src : '') +
           '</div>';
  }

  function loadData() {
    var corpCodeEl = document.getElementById('fCorpCode');
    var corpCode = (corpCodeEl && corpCodeEl.textContent.trim()) || '';
    if (!corpCode) {
      bodyEl.innerHTML =
        '<div class="rp-error">corp_code를 찾을 수 없습니다.</div>';
      return;
    }
    bodyEl.innerHTML = '<div class="rp-hint">참고서를 불러오는 중…</div>';
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
          throw new Error('이 회사의 참고서는 아직 만들어지지 않았어요.\n(corp_code: ' + corpCode + ')');
        }
        return fetch('../../modules/disclosure/data/fulltext/' + corpCode + '/' + entry.rcept_no + '/summary.json');
      })
      .then(function(r) {
        if (!r.ok) throw new Error('summary.json fetch 실패 (status ' + r.status + ')');
        return r.json();
      })
      .then(function(data) {
        metaEl.textContent =
          (data.corp_name || entry.corp_name) + ' · ' + entry.report_nm;
        bodyEl.innerHTML =
          renderNotes(data.investor_notes) +
          renderFinancials(data.financial_highlights) +
          renderAudit(data.kam, data.emphasis) +
          renderSegments(data.segments) +
          renderProducts(data.products) +
          renderGlossary(data.glossary_terms) +
          renderDisclaimer(data);
      })
      .catch(function(e) {
        metaEl.textContent = '';
        bodyEl.innerHTML =
          '<div class="rp-error">⚠ ' + escHtml(e.message) +
          '<br><br>로컬에서 수집·파싱·요약을 먼저 실행해주세요:' +
          '<br><code>python -m modules.disclosure.fulltext_collector</code>' +
          '<br><code>python -m modules.disclosure.fulltext_parser</code>' +
          '<br><code>python -m modules.disclosure.summary_extractor</code></div>';
      });
  }

  function init() {
    overlayEl = document.getElementById('rpOverlay');
    bodyEl = document.getElementById('rpBody');
    metaEl = document.getElementById('rpMeta');
    var closeBtn = document.getElementById('rpClose');
    var openBtn = document.getElementById('rpBtn');
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

    # 4) 회사 참고서 패널 (모듈 ③ 2c) — ftBtn 옆에 진입 버튼 + 요약 모달
    _rp_button = (
        '<button class="ghost-btn" type="button" id="rpBtn" '
        'style="border-color:rgba(167,139,250,0.5);color:#a78bfa">'
        "📚 회사 참고서</button>\n        "
    )
    html = _replace_once(
        html,
        '<button class="ghost-btn" type="button" id="ftBtn"',
        _rp_button + '<button class="ghost-btn" type="button" id="ftBtn"',
        "reference button in action-row",
    )
    html = html.replace("</body>", _REFERENCE_PANEL_SNIPPET + "\n</body>", 1)

    with open(_OUT, "w", encoding="utf-8") as fp:
        fp.write(html)
    print(f"[done] 템플릿 생성 → {_OUT} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
