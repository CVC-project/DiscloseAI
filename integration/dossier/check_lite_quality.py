"""check_lite_quality.py — galaxy lite 산출물 회귀 게이트 (결정 원장의 코드 승격판).

## 왜 있나
lite는 22사+로 같은 파이프라인을 반복한다. 한 번 지적받은 실수(비유·미공시·표준 단정·
적자 오독…)를 다음 기업에서 되풀이하면 원장에 적는 의미가 없다.
**원장 조문 1건 = 이 파일의 규칙 1개**로 승격해, 매 세션 말미에 전 기업을 재검사한다.

## 규칙 대장 (규칙을 추가할 때 원장 번호를 반드시 적을 것)
| ID | 근거 | 무엇을 막나 |
|----|------|-------------|
| R1  | FN-021          | '미공시' 단어 — 수집 갭을 공시 부재로 단정 |
| R2  | UX-041          | 은유(골짜기·강줄기·저수지·항로·존) — lite는 직관 서술 |
| R3  | PLAN §1         | EQS 탭 중복(점수·등급·백분위·업계평균·ROE·ROA) |
| R4  | STYLE_GUIDE A7  | 격식체(~다./~음./~임.) |
| R5  | FN-022          | 표준 재무활동 방향 단정이 실제 표준값과 어긋남 |
| R6  | FN-022          | '…도'(동조) 표현인데 표준과 국면이 다름 |
| R7  | FN-022          | 적자인데 '남아요'로 서술 |
| R8  | BATCH §4        | std_focus가 표준 골든 dives에 실존하지 않음 |
| R9  | UX-042          | 스토리 스레드 파손(order 불연속·첫 카드 bridge 존재) |
| R10 | FN-022          | 골든 매니페스트에 lite 산출물 혼입 / 골든·lite 교집합 |
| R11 | PLAN §6         | 델타 카드 3문장 규격 위반 |
| R12 | BATCH §4        | 브래킷 안에 숫자가 아닌 텍스트 |
| R13 | 금칙어          | 투자 조언성 표현(매수·매도·추천·보장·확실) |
| R14 | FN-023          | 정규화 값이 물리적으로 불가능 — 원천(firm JSON) 결함 |
| R15 | FN-023          | 매출이 급락 후 급반등 — 연결·별도 기준 혼재 의심 |

Usage:
    python integration/dossier/check_lite_quality.py            # 전 기업
    python integration/dossier/check_lite_quality.py 042700     # 한 기업
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):  # cp949 콘솔 크래시 방지 (FN-001)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

BANNED_METAPHOR = ["골짜기", "강줄기", "저수지", "항로", "영업 존", "매듭", "물길"]
BANNED_EQS = [
    "백분위",
    "업계 평균",
    "업계평균",
    "동종업계",
    "ROE",
    "ROA",
    "종합점수",
    "등급은",
]
BANNED_ADVICE = ["매수", "매도", "추천", "보장", "확실", "장부이익"]

# 브래킷 안에 허용되는 것: 숫자(+단위) · FY 라벨 · 8상 부호코드
CHIP_OK = re.compile(r"^(-?[\d,]+(\.\d+)?\s*(조|억|원|%p|%)?|FY\d{2}|[+-]{3})$")


def prose_of(doc: dict[str, Any]) -> list[tuple[str, str]]:
    """(위치, 문장) — 화면에 글자로 나가는 것만 모은다 (앵커·키 필드는 제외)."""
    out: list[tuple[str, str]] = []
    for k, v in (doc.get("strings") or {}).items():
        for s in v if isinstance(v, list) else [v]:
            out.append((f"strings.{k}", s))
    for c in doc.get("cards", []):
        out.append((f"{c['id']}.title", c.get("title", "")))
        for i, ln in enumerate(c.get("lines", [])):
            out.append((f"{c['id']}.lines[{i}]", ln))
        if c.get("bridge"):
            out.append((f"{c['id']}.bridge", c["bridge"]))
    for n in doc.get("notes", []):
        out.append((f"{n['id']}.title", n.get("title", "")))
        for i, ln in enumerate(n.get("what", []) + n.get("why", [])):
            out.append((f"{n['id']}.prose[{i}]", ln))
        if n.get("bridge"):
            out.append((f"{n['id']}.bridge", n["bridge"]))
    return out


def check_doc(t: str, doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    lines = prose_of(doc)

    for where, s in lines:
        if "미공시" in s:
            errs.append(
                f"R1 {where}: '미공시' — 수집 갭은 '데이터 준비 중'으로 (FN-021)"
            )
        for w in BANNED_METAPHOR:
            if w in s:
                errs.append(f"R2 {where}: 은유 '{w}' (UX-041)")
        for w in BANNED_EQS:
            if w in s:
                errs.append(f"R3 {where}: EQS 중복 '{w}' (PLAN §1)")
        for w in BANNED_ADVICE:
            if w in s:
                errs.append(f"R13 {where}: 금칙어 '{w}'")
        st = s.rstrip()
        if re.search(r"(다|음|임)\.$", st) and not re.search(r"(요|죠)\.$", st):
            errs.append(f"R4 {where}: 격식체 — …{st[-20:]}")
        for chip in re.findall(r"\[([^\]]+)\]", s):
            if not CHIP_OK.match(chip.strip()):
                errs.append(f"R12 {where}: 브래킷 안이 숫자가 아님 — [{chip}]")

    # R5·R6·R7 — 표준을 '읽어서' 말했는지 (고정 문구 단정 금지)
    S, SD = doc.get("series", {}), doc.get("std_series", {})
    fin = (S.get("fin") or [None])[-1]
    std_fin = (SD.get("fin") or [None])[-1]
    d3 = next((c for c in doc.get("cards", []) if c["id"] == "d3"), None)
    if d3 and fin is not None and std_fin is not None:
        body = " ".join(d3.get("lines", []))
        opposite_claim = ("반대로" in body) or ("반대예요" in body)
        same_claim = ("표준도" in body) or ("같은 방향" in body)
        actually_same = (fin >= 0) == (std_fin >= 0)
        if opposite_claim and actually_same:
            errs.append(
                "R5 d3: '표준과 반대'라고 했는데 표준 재무활동 부호가 같음 (FN-022)"
            )
        if same_claim and not actually_same:
            errs.append(
                "R5 d3: '표준과 같은 방향'이라고 했는데 표준 재무활동 부호가 반대 (FN-022)"
            )
    if d3:
        name = (doc.get("corp") or {}).get("name", "")
        line2 = (d3.get("lines") or ["", "", ""])[1]
        if line2.startswith(f"{name}도"):
            my = (doc.get("pattern") or {}).get("code")
            std_code = (
                "".join(
                    "+" if (SD.get(k) or [0])[-1] >= 0 else "-"
                    for k in ("ocf", "icf", "fin")
                )
                if all(SD.get(k) for k in ("ocf", "icf", "fin"))
                else None
            )
            if std_code and my != std_code:
                errs.append(
                    f"R6 d3: '{name}도'인데 국면이 표준과 다름({my} vs {std_code}) (FN-022)"
                )
    op = (S.get("op") or [None])[-1]
    if op is not None and op < 0:
        for where, s in lines:
            if "남아요" in s or "남는 돈이 많" in s:
                errs.append(f"R7 {where}: 적자인데 '남아요' 서술 (FN-022)")

    # R8 — std_focus가 표준 골든에 실존하는가
    std_t = (doc.get("std_ref") or {}).get("ticker")
    gp = DATA / f"galaxy_{std_t}.json"
    dives = {}
    if gp.exists():
        dives = json.loads(gp.read_text(encoding="utf-8")).get("dives") or {}
    for c in doc.get("cards", []):
        f = (c.get("anchor") or {}).get("std_focus")
        if f and f.startswith("dive:") and dives and f[5:] not in dives:
            errs.append(f"R8 {c['id']}: std_focus '{f}' 가 {std_t} dives에 없음")
    for n in doc.get("notes", []):
        f = n.get("std_focus")
        if f and f.startswith("dive:") and dives and f[5:] not in dives:
            errs.append(f"R8 {n['id']}: std_focus '{f}' 가 {std_t} dives에 없음")

    # R9 — 스토리 스레드 (델타·노트 각각 1..N 연속, 첫 카드만 bridge 없음)
    for label, items in (
        ("cards", doc.get("cards", [])),
        ("notes", doc.get("notes", [])),
    ):
        if not items:
            continue
        orders = [i.get("order") for i in items]
        if sorted(orders) != list(range(1, len(items) + 1)):
            errs.append(f"R9 {label}: order가 1..{len(items)} 연속이 아님 — {orders}")
        for i in items:
            has_bridge = bool(i.get("bridge"))
            if i.get("order") == 1 and has_bridge:
                errs.append(f"R9 {label}.{i['id']}: 첫 카드인데 bridge가 있음")
            if i.get("order") != 1 and not has_bridge:
                errs.append(f"R9 {label}.{i['id']}: bridge 없음 — 스레드가 끊김")

    # R11 — 델타 카드 3문장
    for c in doc.get("cards", []):
        if len(c.get("lines", [])) != 3:
            errs.append(f"R11 {c['id']}: 3문장 규격 위반 ({len(c.get('lines', []))}줄)")

    # R14·R15 — 화면에 나가기 전에 **원천이 말이 되는지** 본다 (FN-023).
    # lite는 수치를 코드가 만들기 때문에, 입력이 깨져 있으면 아주 그럴듯한 거짓 화면이 나온다.
    N = doc.get("norm", {})
    years = doc.get("years", [])
    # 임계는 '이례적'이 아니라 '설명 불가'를 잡는 선. 순이익은 지분 처분이익 하나로 매출을
    # 넘길 수 있고(한미반도체 FY23 168% 실측 = 정상), OCF도 지주·금융 성격이면 커진다.
    for k, limit in (("op", 100.0), ("ni", 400.0), ("cogs", 200.0), ("ocf", 300.0)):
        for i, v in enumerate(N.get(k) or []):
            if v is not None and abs(v) > limit:
                y = years[i] if i < len(years) else i
                errs.append(
                    f"R14 norm.{k}[{y}]={v:.1f} — 매출 100 기준으로 불가능한 값. "
                    "firm JSON 원천 결함 의심 (FN-023)"
                )
    rev = S.get("revenue") or []
    for i in range(1, len(rev) - 1):
        a, b, c2 = rev[i - 1], rev[i], rev[i + 1]
        if a and b and c2 and b < a * 0.2 and c2 > b * 5:
            y = years[i] if i < len(years) else i
            errs.append(
                f"R15 series.revenue[{y}] — 급락 후 급반등(연결·별도 기준 혼재 의심). "
                "원천 확인 전 화면에 내보내지 말 것 (FN-023)"
            )
    return errs


def check_manifests() -> list[str]:
    """R10 — 골든/lite 매니페스트가 서로 오염되지 않았는가."""
    errs: list[str] = []
    gi, li = DATA / "galaxy_index.json", DATA / "galaxy_lite_index.json"
    g = (
        json.loads(gi.read_text(encoding="utf-8")).get("tickers", [])
        if gi.exists()
        else []
    )
    l = (
        json.loads(li.read_text(encoding="utf-8")).get("tickers", [])
        if li.exists()
        else []
    )
    for t in g:
        if not re.fullmatch(r"\d{6}", t):
            errs.append(
                f"R10 galaxy_index: 티커가 아닌 항목 '{t}' — lite 산출물 혼입 (FN-022)"
            )
    for t in set(g) & set(l):
        errs.append(f"R10 {t}: 골든·lite 매니페스트 동시 등록 — 골든 우선 규칙 위반")
    return errs


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    paths = sorted(glob.glob(str(DATA / "galaxy_lite_*.json")))
    paths = [p for p in paths if not p.endswith("galaxy_lite_index.json")]
    if only:
        paths = [p for p in paths if p.endswith(f"galaxy_lite_{only}.json")]

    total = 0
    for p in paths:
        t = Path(p).name[len("galaxy_lite_") : -len(".json")]
        doc = json.loads(Path(p).read_text(encoding="utf-8"))
        errs = check_doc(t, doc)
        total += len(errs)
        name = (doc.get("corp") or {}).get("name", "")
        notes = len(doc.get("notes") or [])
        if errs:
            print(f"[FAIL] {t} {name} (주석카드 {notes}장)")
            for e in errs:
                print("   -", e)
        else:
            print(f"[PASS] {t} {name} (주석카드 {notes}장)")

    merrs = check_manifests()
    total += len(merrs)
    for e in merrs:
        print("   -", e)

    print(f"\n검사 {len(paths)}사 / 위반 {total}건")
    if total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
