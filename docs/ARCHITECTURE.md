# DiscloseAI 시스템 아키텍처

> 이 문서는 팀원이 프로젝트 전체 구조를 이해하기 위한 가이드입니다.

---

## 1. 시스템 전체 그림

```
[데이터 소스]          [수집 & 계산]         [저장]           [서빙]            [사용자]
                                                                              
                                                                              
DART OpenAPI ──→  modules/disclosure/ ─┐                                      
(공시, 재무제표)   (B 담당, 로컬DB)    │                                      
                                      │   로컬 SQLite                        
yfinance ──────→  modules/price/     ─┤   (개발/테스트)   Supabase    FastAPI  
(주가 데이터)      (D 담당, 로컬DB)    ├──→ ─────────────→ (공용 DB) ─→ (api/) 
                                      │                                      
공정위/KRX ─────→  modules/relation/  ─┤                                      
(기업 관계)        (C 담당, 로컬DB)    │                                      
                                      │                                      
                  modules/financial/ ──┘                                      
                  (A 담당, 로컬DB)                                               
                      EQS 계산                                               
```

**핵심**: 각 팀원은 자기 폴더에서 데이터를 수집/계산 → DB에 저장. 프로젝트 리드가 API와 프론트엔드에서 DB를 조회하여 사용자에게 보여줌.

---

## 2. 폴더별 역할

### 공용 폴더 (프로젝트 리드만 수정)

| 폴더 | 한 줄 설명 |
|------|----------|
| `.claude/` | Skills, Agents, 설정. **절대 수정 금지** |
| `shared/` | 공용 DB 스키마, 연결 설정. **절대 수정 금지** |
| `docs/` | PRD, 아키텍처, 온보딩 가이드 |

### 개별 작업 폴더 (`modules/` 아래, 각 담당자만 수정)

| 폴더 | 담당 | 한 줄 설명 |
|------|------|----------|
| `modules/financial/` | A | 재무제표 수집 + EQS 등급 계산 |
| `modules/disclosure/` | B | DART 공시 수집 + 쉬운 설명 생성 |
| `modules/relation/` | C | 기업 간 관계 분석 (지분, 공급, 경쟁, 계열) |
| `modules/price/` | D | 주가 수집 + 공시 후 주가변동 라벨링 |

각 모듈에는 **로컬 DB**가 포함되어 있습니다:
- `db.py` — SQLite 연결 (개발/테스트용)
- `models.py` — 로컬 테이블 정의
- `data/` — DB 파일 저장 (gitignored)

개발 중에는 로컬 SQLite로 작업하고, 완성되면 Supabase(공용 DB)로 옮깁니다.

---

## 3. 데이터 흐름

```
A가 재무제표 수집 → financial DB 테이블에 저장
B가 공시 수집     → disclosure DB 테이블에 저장
C가 관계 구축     → relation DB 테이블에 저장
D가 주가 수집     → price DB 테이블에 저장

→ 모두 같은 Supabase DB에 저장됨
→ 프로젝트 리드가 API에서 DB 조회 → 프론트엔드에 전달
```

---

## 4. 모듈 간 연결 규칙

### 남의 코드를 import하지 않는다

```python
# 잘못된 예 (금지)
from financial.eqs.calculator import calculate_eqs

# 올바른 예 (DB를 통해 데이터 공유)
from shared.db import get_session
result = session.query(FinancialData).filter_by(corp_code="005930").first()
```

**왜?** 남의 코드가 바뀌어도 내 코드가 안 깨지니까. 모듈 간 유일한 연결점은 DB 테이블.

### 공유 테이블만 사용한다

각 모듈이 DB에 저장하는 테이블은 `shared/models.py`에 정의되어 있습니다. 이 파일을 보면 어떤 데이터가 어떤 형태로 저장되는지 알 수 있습니다.

---

## 5. 기술 용어 번역표

| 용어 | 쉬운 설명 |
|------|----------|
| **API** | 프로그램끼리 데이터를 주고받는 통로. "주문 창구" 같은 것 |
| **DB (데이터베이스)** | 엑셀 시트를 서버에 올려둔 것. 여러 사람이 동시에 사용 가능 |
| **DB 스키마** | 엑셀 시트의 열 이름(헤더)을 미리 정해둔 설계도 |
| **테이블** | 엑셀의 시트 하나. 예: 재무 테이블, 주가 테이블 |
| **ORM** | Python 코드로 DB를 조작하는 도구. SQL 몰라도 됨 |
| **Supabase** | 우리가 쓰는 DB 서비스 이름. 웹에서 데이터를 직접 볼 수 있음 |
| **FastAPI** | Python으로 만드는 API 서버. "주문 창구를 만드는 도구" |
| **Next.js** | React 기반 웹 프론트엔드 프레임워크. 화면을 만드는 도구 |
| **Three.js** | 3D 그래픽을 웹에서 그리는 라이브러리. 기업 우주 시각화에 사용 |
| **Celery** | 예약된 시간에 자동으로 코드를 실행해주는 스케줄러 |
| **WebSocket** | 서버가 브라우저에 실시간으로 알림을 보내는 방법 |
| **CatBoost** | 범주형 데이터에 강한 AI 분류 모델. 공시 영향 예측에 사용 |
| **pytest** | Python 코드가 올바르게 동작하는지 자동 확인하는 테스트 도구 |
| **Black** | Python 코드를 일정한 형식으로 자동 정리하는 포매터 |
| **CI (Continuous Integration)** | PR 올리면 자동으로 테스트 실행. 통과해야 merge 가능 |
| **PR (Pull Request)** | "내 작업 확인해주세요" 요청. GitHub에서 코드 리뷰 요청 |
| **Branch** | 내 작업 공간. 다른 사람 작업에 영향 X |
| **Merge** | 내 작업을 메인 코드에 합치는 것 |
| **MCP** | Claude Code가 외부 도구(GitHub, DB)와 대화하는 연결선 |
| **Skill** | Claude Code에 미리 짜둔 작업 레시피. `/이름`으로 호출 |
| **Agent** | Claude Code의 전문가 동료. Skill이 호출하여 작업 위임 |
| **Hook** | 자동 안전장치. 위험한 행동을 자동으로 막아줌 |
