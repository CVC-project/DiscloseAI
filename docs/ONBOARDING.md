# DiscloseAI 팀원 온보딩 가이드

---

## Part 1: 오늘 당장 시작하기 (30분)

### Step 1. 프로그램 설치

아래 4개를 순서대로 설치하세요. 모두 무료입니다.

1. **Git** 설치: https://git-scm.com → Download → 설치 (기본 옵션 그대로 Next)
2. **Python 3.11** 설치: https://www.python.org → Downloads → 설치 시 **"Add to PATH" 반드시 체크**
3. **Node.js** 설치: https://nodejs.org → LTS 버전 다운로드 → 설치
4. **Claude Code** 설치: https://claude.ai/download → Desktop 앱 다운로드 → 설치

> Claude Max Plan ($100/월) 구독이 필요합니다: https://claude.ai (권장)

### Step 2. 레포 클론 (프로젝트 다운로드)

터미널(명령 프롬프트)을 열고 아래 명령어를 복붙하세요:

```bash
# 1. 원하는 위치로 이동 (예: 바탕화면)
cd ~/Desktop

# 2. 프로젝트 다운로드
git clone https://github.com/CVC-project/DiscloseAI.git

# 3. 프로젝트 폴더로 이동
cd DiscloseAI
```

### Step 3. 환경변수 설정

```bash
# 1. 환경변수 템플릿 복사
cp .env.example .env

# 2. .env 파일을 열어서 본인 API 키 입력
# DART_API_KEY=여기에_본인_DART_키
# SUPABASE_URL=프로젝트_리드가_알려줄_URL
# SUPABASE_KEY=프로젝트_리드가_알려줄_키
```

> DART API 키 발급: https://opendart.fss.or.kr → 회원가입 → 인증키 신청

### Step 4. 자기 브랜치로 이동

```bash
# A (재무)
git checkout feat/financial    # modules/financial/ 에서 작업

# B (공시)
git checkout feat/disclosure   # modules/disclosure/ 에서 작업

# C (관계)
git checkout feat/relation     # modules/relation/ 에서 작업

# D (주가)
git checkout feat/price        # modules/price/ 에서 작업
```

### Step 5. Claude Code 실행 + 첫 요청

```bash
# Claude Code 실행 (터미널에서)
claude
```

실행 후 아래처럼 채팅창이 나타납니다. 여기에 자연어로 요청하면 됩니다:

```
# 예시 (코딩 용어 몰라도 됨, CPA 용어 그대로 사용):

"DART에서 삼성전자 3년치 재무제표 수집하는 코드 짜줘."

"Beneish M-score 계산 코드 짜줘. DSRI, GMI, AQI, SGI, DEPI, SGAI, TATA, LVGI 8개 변수 사용. 금융업은 제외."

"yfinance로 KOSPI 전 종목 종가 수집해줘. 종목코드 뒤에 .KS 붙여야 해."
```

> **이렇게 보이면 성공**: Claude Code가 코드를 작성하기 시작하고, 파일이 생성되는 것을 볼 수 있습니다.

---

## Part 2: 매일 작업 루틴 (Day 2부터)

### 작업 시작

```bash
cd disclose-ai          # 프로젝트 폴더로 이동
git pull                # 다른 사람이 올린 최신 변경사항 받기
claude                  # Claude Code 실행
```

### 작업 중

CPA 용어로 자연어 요청. Claude Code가 알아서 코드 작성 + 테스트까지 수행.

### 로컬 DB 사용 (개발용)

각 모듈 폴더에 로컬 SQLite DB가 포함되어 있습니다. Claude Code에게 이렇게 요청하면 됩니다:

```
"로컬 DB 초기화해줘"           → data/ 폴더에 SQLite 파일 생성
"DART 데이터를 로컬 DB에 저장해줘"  → 수집한 데이터를 로컬에 저장
"로컬 DB에서 삼성전자 조회해줘"    → 저장된 데이터 확인
"로컬 DB를 Supabase로 옮겨줘"     → 완성 후 공용 DB로 이전
```

### 작업 끝 — `/check`로 최종 점검

작업이 끝나면 Claude Code 채팅창에 `/check` 입력:

```
/check
```

이렇게 하면 자동으로:
1. **코드 리뷰** (code-reviewer agent가 코드 품질 확인)
2. **테스트 실행** (test-generator agent가 테스트 생성 + 실행)
3. **결과 요약** (무엇을 했는지, 테스트 통과 여부)
4. **PROGRESS.md 기록** (진행경과 자동 저장)

결과를 확인하고, 회계적으로 맞는지 판단한 후:

```bash
git add .
git commit -m "feat: Beneish M-score 계산 구현"
git push
```

### 3개 공용 Skill 정리

| 명령어 | 언제 사용 | 무슨 일을 하나 |
|--------|----------|--------------|
| `/check` | 작업 끝난 후 | 리뷰 + 테스트 + 기록 **한번에** |
| `/review` | 중간에 방향 확인하고 싶을 때 | 리뷰**만** |
| `/test` | 테스트만 돌리고 싶을 때 | 테스트 생성 + 실행**만** |

---

## Part 3: 알면 좋은 것 (필요할 때 읽기)

### A. Git 개념

| Git 용어 | 비유 | 설명 |
|----------|------|------|
| Repository (레포) | 프로젝트 폴더 | 코드가 저장된 곳 |
| Branch (브랜치) | 내 작업 공간 | 다른 사람 작업에 영향 안 줌 |
| Commit (커밋) | 세이브 | "무엇을 바꿨는지" 메모와 함께 저장 |
| Push (푸시) | 세이브를 서버에 업로드 | 다른 사람이 내 작업을 볼 수 있게 됨 |
| Pull (풀) | 서버에서 최신 내용 다운로드 | 다른 사람이 올린 변경사항 받기 |
| Pull Request (PR) | "확인해주세요" 요청 | 내 작업을 메인 코드에 합치기 전 리뷰 요청 |
| Merge (머지) | 합치기 | 리뷰 통과 후 메인 코드에 반영 |
| Conflict (충돌) | 같은 줄을 서로 다르게 수정 | → "충돌 해결해줘" 라고 Claude에게 말하면 됨 |

매일 쓰는 명령어:
```bash
git pull                              # 시작할 때: 최신 받기
git add .                             # 끝날 때: 변경 파일 등록
git commit -m "feat: 작업 설명"        # 세이브
git push                              # 서버에 업로드
```

### B. Skill 직접 만드는 법

자기 도메인에 맞는 skill을 만들고 싶으면:

**Step 1.** `.claude/skills/` 폴더에 새 폴더 생성
```bash
mkdir -p .claude/skills/eqs-calculator
```

**Step 2.** `SKILL.md` 파일 작성
```markdown
---
name: eqs-calculator
description: EQS 5개 모듈을 계산하고 등급을 산출합니다.
auto-invocable: false
---

# /eqs-calculator

1. financial/ 폴더의 EQS 모듈(m1~m5)을 실행
2. 종합 점수 계산 (가중 합산 0~100점)
3. A/B/C/D/F 등급 산출
4. 결과를 DB에 저장
```

**Step 3.** 저장 후 Claude Code 채팅창에서 `/eqs-calculator`로 호출 가능

> 참고: 만든 skill은 PR로 올려서 프로젝트 리드가 확인 후 merge합니다.

### C. DB 스키마란?

**DB 스키마 = 엑셀 시트의 열 이름(헤더) 설계도**

예시 — `shared/models.py`에 이런 코드가 있으면:

```python
class FinancialData(Base):
    corp_code = Column(String)        # 기업코드 (예: "005930")
    year = Column(Integer)            # 연도 (예: 2024)
    revenue = Column(Float)           # 매출액 (조 단위)
    operating_income = Column(Float)  # 영업이익
    eqs_total = Column(Float)         # EQS 종합 점수
    eqs_grade = Column(String)        # EQS 등급 (A~F)
```

이건 엑셀로 치면 이런 표입니다:

| corp_code | year | revenue | operating_income | eqs_total | eqs_grade |
|-----------|------|---------|-----------------|-----------|-----------|
| 005930 | 2024 | 300.9 | 36.5 | 82 | A |
| 000660 | 2024 | 66.2 | 23.5 | 78 | B |

- **데이터 저장**: Claude Code에게 "이 데이터를 DB에 저장해줘" 라고 말하면 됨
- **데이터 조회**: "삼성전자의 최근 3년 매출 보여줘" 라고 말하면 됨
- **직접 확인**: Supabase 대시보드(https://supabase.com)에 로그인하면 웹에서 데이터를 직접 볼 수 있음

### D. Hooks / MCP / Sub-agent 개념

팀원이 직접 설정하거나 건드릴 일은 없지만, 알아두면 좋은 것:

| 도구 | 뭔지 | 팀원이 할 일 |
|------|------|------------|
| **Hook** | 자동 안전장치. 위험한 행동(force push, .env 커밋 등)을 자동 차단 | 없음 (이미 설정됨) |
| **MCP** | Claude Code가 GitHub, DB 등 외부 도구와 대화하는 연결선 | 없음 (이미 설정됨) |
| **Sub-agent** | Claude Code의 전문가 동료. `/check`이 자동으로 호출 | 없음 (`/check`만 치면 됨) |
| **Permissions** | 명령어 허용/금지 목록. force push 차단, .env 편집 차단 등 | 없음 (이미 설정됨) |

### E. 트러블슈팅

| 문제 | 해결법 |
|------|--------|
| Claude Code가 응답 안 함 | 터미널에서 `claude` 다시 실행 |
| `git push` 실패 | `git pull` 먼저 실행 후 다시 push |
| 테스트 실패 | Claude Code에게 "테스트 고쳐줘" 라고 말하기 |
| CI 빨간 X (GitHub) | Claude Code에게 "CI 실패 원인 알려줘" 라고 말하기 |
| `.env` 관련 에러 | `.env` 파일에 API 키를 입력했는지 확인 |
| 충돌(conflict) 발생 | Claude Code에게 "충돌 해결해줘" 라고 말하기 |
| MCP 연결 안 됨 | Claude Code에게 "MCP 연결 확인해줘" 라고 말하기 |
| 남의 폴더 수정 경고 | 자기 폴더(feat/xxx)에서만 작업. 다른 폴더는 금지 |

---

## 절대 하지 말 것

- ❌ 남의 폴더 파일 수정
- ❌ `shared/` 폴더 건드리기 (프로젝트 리드에게 요청)
- ❌ `.claude/` 폴더 건드리기 (프로젝트 리드에게 요청)
- ❌ `.env` 파일 커밋 (Permissions가 차단하지만 시도도 말 것)
- ❌ `main` 브랜치에 직접 push (Permissions가 차단)
- ❌ `git push --force` (Permissions가 차단)
