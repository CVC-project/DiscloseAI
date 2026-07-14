# 다음 세션 핸드오프 — 시작점 커밋 `4df8e25`

> 이 파일은 새 세션이 이어받는 지점. 완료되면 삭제.

## 먼저 읽기 (순서)
1. `modules/report/MILKYWAY_GENERATOR.md` — 하네스 정본(파이프라인·수렴 루프·규칙).
2. `modules/report/VARIATIONS.md` — 변형 레지스트리(**S0 필수 읽기**). 특히 **V-040~048**(이번 배치에서 코드화된 편차)와 채록 로그.
3. 이 파일.

## 지금 상태
- **완주 골든 4본**: 삼성 005930(제조·최상위 골든=기준), SK 000660(메모리), NAVER 035420(플랫폼), 셀트리온 068270(바이오 제조).
- **재사용 조립기 논리**: 이번 세션 scratchpad `build_mfg.py`(제조)·`build_naver.py`(플랫폼)는 **세션 소멸**. 재현 재료 = 커밋된 골든 JSON(셀트리온=제조 템플릿, NAVER=플랫폼 템플릿) + VARIATIONS V-046 서술 + `facts_*.json`. 필요시 `modules/report/`에 `assemble.py`로 정식 모듈화 권장.
- **facts 보유**: `modules/report/data/facts/` — 현대차 005380·NAVER 035420·LG화학 051910·셀트리온 068270. **SK 000660은 facts 없음**(수기 골든) → 재작성 시 note-extractor로 먼저 추출하거나 `reports.db report_section` 원문 직접 인용.
- 하네스는 **플랫폼·제조 두 구조를 galaxy.html 수정 0으로 렌더**(V-040/041/043/046 검증). check_golden·인터랙션 게이트 작동.

## Task 1 (최우선) — APPENDIX 전수 재작성: 일반론 → 삼성 골든 수준 (V-048)
**문제**: SK/NAVER/셀트리온 appendix가 '개념만 설명하는 일반론'(그 주석 실수치·링크 없음). check_golden이 이제 강제로 FAIL시킴(**SK 17·NAVER 54·셀트리온 74갭**).
**기준 = 삼성 골든 appendix**(예: `galaxy_005930.json`의 n26 EPS 카드):
- `amt` = 그 주석 실값(예 `"6,605원"`·`"종속기업 308개"` — 개념어 금지)
- `what` 2문장 = 그 주석의 **실제 수치 브래킷 ≥1(숫자)** + 용어 브래킷 (예 `[6,605원](전기 4,950)`·`[38.9조]`·`[58.9억주]`)
- `links` **≥1** = 재무제표 연결(IS/CF/BS/EQ 행 + a값) — 예 `{t:"IS",row:"is-ni-ctrl",txt:"분자=지배주주 순이익",a:"44.3조"}`
- `why` 2문장(회계원리+함의), `five: {skip}` 또는 series 있으면 차트
**절대 금지**: 사업보고서 주석 없이 개념만. 반드시 그 회사 그 주석 원문 수치 인용.
**순서**: 셀트리온 → NAVER → SK(→ 이후 현대차·LG화학은 Task 2에서 함께).
**작업법**: 회사별 `facts_<t>.json`(+ SK는 reports.db)에서 각 appendix 주석의 실수치를 뽑아 `galaxy_<t>.json`의 `appendix[]` 카드를 in-place 재작성 → `python -m modules.report.check_golden <t>` 갭 0까지. 삼성(005930) 무회귀 필수.

## Task 2 — 현대차·LG화학 골든 완주
- 둘 다 제조형(cogs/gross/sgna). **현대차**: 금융부문(할부금융·리스)·판매보증충당·부문(차량/금융/기타). **LG화학**: 4부문(석유화학 적자·LG에너지솔루션 절반·첨단소재·생명과학), capex 29.4조(배터리), **FY25 순손실 −1.0조(V-023)**, 기타영업손익 잔차(V-013), 중단영업순이익 0.74조(순이익 항등식 반영 필요).
- 조립: 셀트리온 JSON을 제조 템플릿으로 build_mfg 논리 재현(LG화학은 판관비를 fs_account 아닌 **주22 facts에서** 가져와야 — fs_account 'IS 판매비와관리비'가 0으로 오매칭됨). 구조 조립 → check_golden으로 필요 dive 확인 → 콘텐츠 dive + APPENDIX(Task 1 기준으로) 산문 → 5게이트.

## 검증(완주 게이트, 회사마다)
`check_golden <t>` PASS · `GALAXY_TICKER=<t> pytest tests/report/test_galaxy_interaction.py` · 삼성/SK 무회귀 · 렌더 콘솔에러 0 · 딥다이브 전수 열림(evaluate-click로 확인, `.click()`은 타이밍 오탐). 완주마다 VARIATIONS S7 채록 + galaxy JSON 커밋.

## 알아둘 것(이번 세션 교훈)
- 시그니처 dive(intangible·assoc·segment)가 k-dive와 행 공유하면 **미도달** → BS 고유행으로 재지정(intangible→무형자산행·assoc→관계기업행 완료, **segment는 미해결** — 고유 앵커 필요).
- viz_data `v`는 **숫자**(문자열 시 NaN, V-047). 링크 `t`는 IS/CF/BS/EQ/N만(V-043).
- 딥다이브 열림 테스트는 `page.evaluate("el.click()")` 사용(scroll+`.click()`은 bs-liab/bs-equity 오탐).
- 서버: `python -m http.server 8000`, URL `http://localhost:8000/integration/dossier/galaxy.html?ticker=<t>`.
