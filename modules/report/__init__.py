"""modules/report — 사업보고서 원문·정형계정 수집 파이프라인 (Q1 승인, 리더 소유).

DART document(5개년) + fnlttSinglAcntAll(5개년) → reports.db → (Phase 4) LLM 하네스 → galaxy_<t>.json.
경계: 데이터 생산 모듈. 다른 데이터 모듈과 import 금지(단방향). integration이 publish/를 read-only pull.
상세: integration/dossier/DOSSIER_TABS_PLAN.md Phase 3·§2, modules/report/CLAUDE.md
"""
