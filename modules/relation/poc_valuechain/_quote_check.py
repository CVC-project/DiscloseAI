# -*- coding: utf-8 -*-
"""Temporary quote verification script (delete after use)."""
import io, os

BASE = r"C:\Users\yangw\AIportfolio\CVC-project\DiscloseAI\modules\relation\poc_valuechain\data"
FILES = {
    "s": "semi_005930_삼성전자.txt",
    "h": "semi_000660_SK하이닉스.txt",
    "d": "semi_005290_동진쎄미켐.txt",
    "b": "semi_357780_솔브레인.txt",
    "w": "semi_240810_원익IPS.txt",
}
texts = {}
for k, fn in FILES.items():
    with io.open(os.path.join(BASE, fn), "r", encoding="utf-8-sig") as f:
        texts[k] = f.read()

QUOTES = [
("s","S1","부품 사업은 DS(Device Solutions) 부문에서 DRAM, NAND Flash, 모바일AP 등의 제품을 생산ㆍ판매하고"),
("s","S2","당사는 TV, 냉장고, 세탁기, 에어컨, 스마트폰 등 완제품과"),
("s","S3","SDC가 스마트폰용 OLED 패널 등을 생산ㆍ판매하고 있습니다"),
("s","S4","Harman에서는 디지털 콕핏(Digital Cockpit), 카오디오 등 전장제품과"),
("s","S5","Foundry 사업은 팹리스(Fabless) 업체가 설계한 반도체를 위탁 생산해서 공급해주는"),
("s","S6","DX 부문은 모바일AP 솔루션, Camera Module 등을 Qualcomm, 삼성전기㈜ 등에서 공급받고 있으며"),
("s","S7","TVㆍ모니터용 디스플레이 패널 등을 CSOT 등으로부터 공급받고 있습니다"),
("s","S8","DS 부문은 Chemical, Wafer 등을 솔브레인㈜, SILTRONIC 등으로부터"),
("s","S9","SDC는 FPCA, Cover Glass 등을 ㈜비에이치, Apple 등으로부터 공급받고 있습니다"),
("s","S10","Harman은 MCU(Micro Controller Unit)를 포함한 SOC(System-On-Chip), 통신 모듈 등을 NVIDIA, WNC 등에서 공급받고 있습니다"),
("s","S11","| Qualcomm, MediaTek"),
("s","S12","| 삼성전기㈜, 엠씨넥스 등"),
("s","S13","| 솔브레인㈜, 동우화인켐㈜ 등"),
("s","S14","| SILTRONIC, SK실트론㈜ 등"),
("s","S15","주요 매출처는 Alphabet, Apple, Deutsche Telekom, Hong Kong Techtronics, Supreme Electronics 등(알파벳순)"),
("s","S16a","| Tesla, Inc.\n| 반도체 위탁생산"),
("s","S16b","| Tesla, Inc.\r\n| 반도체 위탁생산"),
("s","S17","| 통신사업자(SK텔레콤㈜, ㈜케이티, ㈜LG유플러스)"),
("h","H1","주력 제품은 DRAM 및 NAND를 중심으로 하는 메모리 반도체이며, Foundry 사업도 병행하고 있습니다"),
("h","H2","당사는 휘발성 메모리인 DRAM과 비휘발성 메모리인 NAND Flash를 주력 생산하고 있습니다"),
("h","H3","연간 HBM 매출은 전년 대비 2배 이상 확대되며 DRAM 실적에 크게 기여하였습니다"),
("h","H4","하반기 기업용 SSD 중심 수요 회복에 대응하며 연간 기준 최대 매출을 기록하였습니다"),
("h","H5","생산공정에 투입되는 원재료는 크게 웨이퍼(Wafer), Substrate, PCB(Printed Circuit Board) 그리고 기타 재료 등으로 구성됩니다"),
("h","H6","그 외 가스 및 화학약품, 소자류 등이 반도체 제조 공정에 투입되는 원재료로 소요됩니다"),
("h","H7","업계의 주요 공급사로부터 반도체 공정의 원자재인 300mm 웨이퍼 완제품을 공급받고 있습니다"),
("h","H8","라이선스 계약을 통해 반도체 전 제품 기술 관련 램버스 보유 특허에 대한 사용권한을 확보하여"),
("h","H9","| Intel의 NAND 사업 영업양수"),
("h","H10","Solidigm과의 통합 시너지를 강화하고"),
("h","H11","업계 최초로 출시된 H3C Pooling System 에 당사 CMM-DDR5 제품을 탑재하여"),
("h","H12","DRAM의 경우 세계 유수의 모바일 및 컴퓨팅 관련 전자 업체에 제품을 공급하고 있습니다"),
("d","D1","당사가 제조하는 반도체 및 디스플레이용 재료는 감광액(Photoresist), 반사방지막(BARC), SOC(Spin-on-carbon), 연마제(CMP Slurry)"),
("d","D2","연마제(CMP Slurry), Wet Chemical, Colored Resist, Organic Insulating Layer, Column Spacer 등으로"),
("d","D3","산업용 기초소재인 발포제를 국내외 화학회사에 주로 납품하고 있으며"),
("d","D4","최적화된 고밀도 도전재 분산 기술을 응용한 고출력, 고용량 도전재 슬러리를 제품화하였고"),
("d","D5","고출력, 고내구성 MEA 제조 기술을 확보하였으며"),
("d","D6","정제유 등 : TFT LCD 화학제품 등(Wet chemical etc.)의 Recycling용 폐액을 수거"),
("d","D7","전자재료 제조에 소요되는 Solvent. PAC. RESIN을 위하여 641,215백만원의 원재료를 매입하였고"),
("d","D8","당사는Mitsubishi Gas Chemical Trading, Inc., PURAC ASIA PACIFIC PTE LTD, Ashland Inc.등 해외구매처와"),
("d","D9","(주)삼양엔씨켐, (주)동진첨단소재, 재원산업(주) 등 국내업체로부터"),
("d","D10","제53기 현재 당사의 주요 매출처는 삼성전자(주), 에스케이하이닉스(주), 엘지디스플레이(주) 등 입니다"),
("d","D11","삼성전자, 엘지디스플레이, 삼성디스플레이 등 반도체 및 평판디스플레이제조 업체에 관련 감광액 등 전자재료 제품 공급에 대한 기본계약"),
("d","D12","중국의 경우 BOE, CSOT 등 중국 디스플레이 제조사와 국내디스플레이 제조사의 중국 10세대 공장들의 가동률 증가"),
("b","B1","당사는 반도체 공정용 화학 소재, 디스플레이 공정용 화학 소재, 2차전지 소재 등을 생산하고 있으며"),
("b","B2","| HF, B.O.E, CMP Slurry, Precursor, 라이닝 외"),
("b","B3","| Etchant, Thin Glass, 유기재료 외"),
("b","B4","| Electrolytes 외"),
("b","B5","2016년 1월에는 반도체용 고순도 인산 생산 및 판매를 위한 솔브레인라사 주식회사를 설립하였습니다"),
("b","B6a","| H3PO4 외\n| 291,801"),
("b","B6b","| H3PO4 외\r\n| 291,801"),
("b","B7","반도체 소재의 원재료가격은 전년(제5기) 대비 약 7% 상승하였고"),
("b","B8","디스플레이 소재의 원재료가격은 전년(제5기) 대비 약 41% 상승하였고"),
("b","B9","2차전지 소재의 원재료가격은 전년(제5기) 대비 약 35% 하락하였고"),
("b","B10","당사는 현재 삼성전자, SK하이닉스, 삼성디스플레이, LG디스플레이 등 국내 반도체 및 디스플레이 제조사에 공정용 화학 소재 등을 안정적으로 공급하고"),
("b","B11","삼성SDI, SK온, LG에너지솔루션 등의 국내 2차전지 제조사에 관련 제품을 공급하고"),
("b","B12","회사의 주요매출처는 삼성전자, SK하이닉스, LG디스플레이 및 삼성SDI 입니다"),
("b","B13","| 김명운 등 6인(주식회사 디엔에프)"),
("w","W1","당사는 반도체, Display 및 Solar Cell 제조용 핵심 장비를 생산ㆍ판매하고 있습니다"),
("w","W2","| PECVD, ALD, Diffusion Thermal System 등"),
("w","W3","| Dry Etcher, PECVD, LTPS Furnace, PI Curing 등"),
("w","W4","대표적으로 웨이퍼 기판의 반사율을 낮추는데 사용되는 RIE 장비를 공급하고 있습니다"),
("w","W5","박막 형성을 위한 증착 장비와 열처리 장비를 주로 공급하고 있습니다"),
("w","W6","| 장비 및 장치 유지보수에 필요한부품, 기술용역 등"),
("w","W7","당사 제품의 주요 원재료는 Heater, Generator 등이 있으며"),
("w","W8","| VAPORIZATION SYSTEM"),
("w","W9","| POWER SUPPLIES"),
("w","W10a","| TM MODULE\n| 16,668"),
("w","W10b","| TM MODULE\r\n| 16,668"),
("w","W11","3D NAND 분야의 핵심 증착 장비(CUARTO, CLARO, NOA 등), DRAM 분야의 핵심 증착 장비(HYETA, GEMINI, PRESTO 등)"),
]

fails = 0
for fk, qid, q in QUOTES:
    ok = q in texts[fk]
    n = len(q)
    flag = "OK " if ok else "FAIL"
    lenflag = "" if 15 <= n <= 100 else f"  <-- LEN {n} OUT OF [15,100]"
    if not ok or lenflag:
        fails += 1
    print(f"{flag} len={n:3d} {qid}{lenflag}")
print("---")
print("fail-or-len-issue count:", fails)
