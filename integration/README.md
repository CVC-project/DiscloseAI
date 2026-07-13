# integration/ — DiscloseAI 서빙 계층 (리더 소유)

`modules/`의 4개 데이터 생산자(financial·disclosure·relation·price) 산출물을 **교차 통합·시각화**하는 서빙 계층. 데이터 생산자와 구조로 분리하기 위해 DiscloseAI 루트로 승격됨(`modules/integration/` → `integration/`).

> 모듈 간 일반 규칙은 "import 금지"이지만, **이 폴더는 예외**(타 모듈 read-only 접근 허용, 단방향). 상세: [v1/CLAUDE.md](v1/CLAUDE.md).

## 구조

```
integration/
├── index.html   ← 안정 진입점 (→ v1/dashboard.html)
├── data/        ← 공유 산출물 (v1 extract_data.py 생성 → v1·v2 모두 fetch)
│   ├── eqs_summary.json · disclosures.json · price_scenarios.json
├── dossier/     ← 기업 상세 3탭 (ENTER CORPORATION) — v1·v2가 iframe 로드
│   ├── business.html · galaxy.html · firm.html · dc-runtime.js
│   ├── tokens.css · theme-galaxy.css · assets/fonts/
│   └── data/    ← per-ticker JSON (firm_*.json 48 · business_*.json · galaxy_*.json)
├── v1/          ← vanilla JS 통합 대시보드 (fallback)
│   ├── dashboard.html · extract_data.py · CLAUDE.md · PROGRESS.md
└── v2/          ← React(Babel in-browser) 정본 UI
    ├── index.html · src/ · data/ · assets/ · styles.css
```

- **v1 = fallback**, **v2 = 정본 트랙**. `data/`는 둘이 공유(생성 주체는 v1의 `extract_data.py`).
- 기업 상세는 `dossier/` 3탭(사업·기업 / 현금 은하수 / EQS) — 상세: [dossier/DOSSIER_TABS_PLAN.md](dossier/DOSSIER_TABS_PLAN.md).
- relation 그래프(`graph_top50.json`)는 extract 단계에서 `data/`로 **무변환 동기화** — 화면 fetch는 전부 `integration/` 아래 (정본은 `modules/relation/data/`).

## 실행

```bash
# 데이터 재생성(공유 JSON 4개 = 3개 생성 + relation 동기화) — 프로젝트 루트에서
python -m integration.build_data          # 오케스트레이터 (opt-in: --business --history)
# 또는 개별: python -m integration.v1.extract_data

# 로컬 확인
python -m http.server 8000
#  진입점:  http://localhost:8000/integration/
#  v1:      http://localhost:8000/integration/v1/dashboard.html
#  v2:      http://localhost:8000/integration/v2/index.html
```

## 배포 (GitHub Pages)

`.github/workflows/pages.yml`이 `dev` push 시 저장소 전체를 배포. 진입 URL은 `…/integration/`.

## 데이터·스키마 계약

각 모듈의 어떤 테이블·컬럼을 뽑는지는 [v1/CLAUDE.md](v1/CLAUDE.md)의 "데이터 소스 계약" 표 참조. 전체 DB 토폴로지는 [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
