# shared/ 폴더 규칙

**이 폴더는 프로젝트 리드만 수정합니다.** 변경이 필요하면 프로젝트 리드에게 요청하세요.

## 이 폴더의 역할
- DB 연결 설정 (db.py)
- 테이블 정의 = DB 스키마 (models.py)
- 환경변수 로드 (config.py)

## 모든 모듈이 이 폴더를 공유합니다
```python
# 각 모듈에서 이렇게 사용:
from shared.db import get_session
from shared.models import FinancialData, DisclosureData
```
