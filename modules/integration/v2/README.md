# DiscloseAI v2 — Corporate Galaxy Atlas

> v2 디자인 prototype을 React + Babel(in-browser)로 신규 구축한 신규 UI.
> dashboard.html은 5/8 데모 fallback으로 동결, v2/는 별도 트랙.

## 구동

```bash
# 프로젝트 루트에서
python -m http.server 8000

# 브라우저에서 열기
# http://localhost:8000/modules/integration/v2/index.html
```

## 진행 상황 (Phase J 시리즈)

| ID | 상태 | 내용 |
|---|---|---|
| J1 | ✅ 완료 | 디코드 + IntroScreen 골격 |
| J2 | ⏳ 다음 | TopTabs + Galaxy 진입 화면 |
| J3 | ⏳ | 데이터 wiring layer (loader + valuation + narration + mock) |
| J4 | ⏳ | Sector 단계 (SectorOverviewPanel + DAILY HIGHLIGHTS) |
| J5 | ⏳ | Company Dossier + ENTER CORPORATION |

상세 진행 기록: [PROGRESS.md](PROGRESS.md)

## 폴더 구조

상세는 [CLAUDE.md](CLAUDE.md) 참조.

```
v2/
├── index.html         # 진입점
├── app.jsx            # React 컴포넌트
├── styles.css         # 디코드된 v2 CSS (46.6KB, 298 rules)
├── data/              # J3 이후 wiring 모듈
├── assets/            # 폰트(16), 이미지(2)
└── _decode/           # 1회용 디코드 도구 + 원본 보관
```

## 디코드 재현

```bash
cd modules/integration/v2/_decode
python extract_v2_assets.py    # CSS·assets 추출
python patch_styles.py         # blob URL → 정적 경로 치환
```

자세한 절차는 [CLAUDE.md § 디코드 재현 절차](CLAUDE.md#디코드-재현-절차) 참조.

## 데이터 정책

1차에서 현재가는 "데이터 수집 중" 뱃지로 표시 (가짜 숫자 노출 금지). 공시 시간 자리는 날짜만, AI Co-pilot은 mock 그대로 유지. SECTOR PULSE는 mock + 워터마크. DAILY HIGHLIGHTS는 `disclosures.json` high_impact 즉시 wiring.

후속 phase에서 yfinance·Gemini API·SECTOR PULSE 실 계산 추가 예정.

## 절대 규칙

- `dashboard.html` 수정 금지 (5/8 fallback)
- `extract_data.py` 수정 금지 (JSON 스키마 단일 출처)
- 빌드 도구 도입 금지 (J1~J5 동안)
