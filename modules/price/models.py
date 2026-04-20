"""Price 모듈 로컬 테이블 정의"""
from sqlalchemy import Column, String, Integer, Float, Date, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class PriceLocal(Base):
    __tablename__ = "price_local"

    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_code = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False)
    close_price = Column(Float)
    daily_return = Column(Float)
    post_disclosure_5d = Column(Float)
    label = Column(String)
    disclosure_id = Column(String)


class VkospiLocal(Base):
    """일별 VKOSPI (한국판 VIX) 데이터"""
    __tablename__ = "vkospi_local"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    vkospi = Column(Float, nullable=False)          # VKOSPI 값
    is_low_vol = Column(Boolean, default=False)     # 저변동 시기 여부 (< 임계값)
