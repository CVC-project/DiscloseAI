# DiscloseAI v2 — Corporate Galaxy Atlas

> v2 디자인 prototype을 React + Babel(in-browser)로 신규 구축한 UI (정본 트랙).
> v1(`../v1/dashboard.html`)은 fallback으로 유지.

## 구동

```bash
# 프로젝트 루트에서
python -m http.server 8000

# 브라우저에서 열기
# http://localhost:8000/integration/v2/index.html
```

## 진행 상황 (Phase J 시리즈)

| ID | 상태 | 내용 |
|---|---|---|
| J1 | ✅ 완료 | 디코드 + IntroScreen 골격 |
| J2 | ✅ | TopTabs + Galaxy 진입 화면 |
| J3 | ✅ | 데이터 wiring layer (loader + valuation + narration + mock) |
| J4 | ✅ | Sector 단계 (SectorOverviewPanel + DAILY HIGHLIGHTS) |
| J5 | ✅ | Company Dossier + ENTER CORPORATION |
| K  | ✅ | standalone JSX 직접 이식 (`src/bundle.jsx`) + 실데이터 wiring |

상세 진행 기록: [PROGRESS.md](PROGRESS.md)

## 폴더 구조

상세는 [CLAUDE.md](CLAUDE.md) 참조.

```
integration/v2/
├── index.html        # 진입점 (loader → adapter → bundle 로드)
├── src/              # React 소스 (bundle.jsx 정본 + adapter.js + galaxy/solar/companies/app)
├── data/             # wiring 모듈 (loader/valuation/narration/mock)
├── assets/           # 폰트(16), 이미지(2)
└── styles.css        # v2 CSS (46.6KB, 298 rules)
```

> 디코드 도구(`_decode/`)·구버전(`_archive/`)은 1회용이라 제거됨 — 필요 시 git 이력에서 복원.

## 데이터

`../data/*.json`(= `integration/data/`, v1 `extract_data.py` 산출물) + `../../modules/relation/data/graph_top50.json`을 `data/loader.js`가 fetch. 실패 시 `data/mock.js` fallback.

## 절대 규칙

- `../v1/dashboard.html` **기능** 수정 금지 (fallback 안정성) — 경로 조정만 예외
- `../v1/extract_data.py` 로직 수정 금지 (JSON 스키마 단일 출처)
- 빌드 도구 도입 금지 (React-CDN + Babel-in-browser 유지)
