"""T1/T2 추출기 모음.

T1(정형 파서, GPU 불요) — Phase V1:
  - related_party.py: 특수관계자 주석(연결주석) 매출/매입 거래금액
  - (신규 investigate 대상) 단일판매·공급계약 수시공시
  - (U1 재사용) 타법인출자현황 — RelationRaw(otrCprInvstmntSttus) 참조 (universe/PLAN.md U-D2)

T2(LLM 서술 추출, GPU 필요) — Phase V2~V3. chunker/·train/ 완성 후 착수.
"""
