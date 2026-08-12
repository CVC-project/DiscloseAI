const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "dossier", "data");
const IMG = "../data/business_images/";

const IMAGE_RULES = [
  [["면제품", "라면", "당면", "국수", "NOODLE"], "business_image_food_noodle.svg", "Local visual"],
  [["양념", "소스", "카레", "케찹", "케첩", "마요네즈", "SAUCE"], "business_image_food_sauce.svg", "Local visual"],
  [["농수산", "참치", "가공식품", "간편식", "만두", "김치", "햇반", "PACKAGED", "CANNED"], "business_image_food_packaged.svg", "Local visual"],
  [["소재식품", "설탕", "밀가루", "식용유", "원당", "유지", "INGREDIENT"], "business_image_food_ingredient.svg", "Local visual"],
  [["사료", "축산", "FEED"], "business_image_food_feed.svg", "Local visual"],
  [["HBM", "고대역폭"], "business_image_df7b448e6d568266.jpg", "Wikimedia Commons"],
  [["DRAM", "메모리"], "business_image_10774ca82ea41202.jpg", "Wikimedia Commons"],
  [["NAND", "SSD", "스토리지"], "business_image_b24ab2723180c79f.jpg", "Wikimedia Commons"],
  [["CIS", "이미지센서", "카메라모듈"], "business_image_025006447be31665.jpg", "Wikimedia Commons"],
  [["Probe", "검사장치", "테스트", "패키징", "PKG", "반도체칩"], "business_image_63ecaf002e77f353.jpg", "Wikimedia Commons"],
  [["Si-Parts", "SiC-Parts", "실리콘부품", "공정소모품", "Electrode", "Ring", "식각"], "business_image_63ecaf002e77f353.jpg", "Wikimedia Commons"],
  [["반도체", "웨이퍼", "Foundry", "파운드리"], "business_image_63ecaf002e77f353.jpg", "Wikimedia Commons"],
  [["OLED", "디스플레이", "패널"], "business_image_d41fecd0a3904c17.jpg", "Wikimedia Commons"],
  [["스마트폰", "Galaxy", "TV", "모니터", "생활가전", "네트워크"], "business_image_141eab6519656e30.jpg", "Wikimedia Commons"],
  [["디지털 콕핏", "카오디오", "Harman"], "business_image_8b1b40ffeb79bd60.jpg", "Wikimedia Commons"],
  [["자동차", "완성차", "전기차", "하이브리드", "모빌리티"], "business_image_3918919e2e6dfce9.avif", "Unsplash"],
  [["전장부품", "자동차부품"], "business_image_e310d326cafd0fb3.jpg", "Wikimedia Commons"],
  [["배터리", "2차전지", "양극재", "음극재", "전해액"], "business_image_d2545c8e29d092d8.avif", "Unsplash"],
  [["조선", "선박", "LNG", "해양", "플랜트"], "business_image_5184e050831a4460.avif", "Unsplash"],
  [["FM", "PM", "시설관리", "자산관리", "건물관리"], "business_image_d205f8d7b04d385e.avif", "Unsplash"],
  [["보안", "시큐리티", "경비", "출동"], "business_image_281a9ea62f3d74e6.avif", "Unsplash"],
  [["물류", "배송", "택배", "창고", "운송"], "business_image_3078a83d5189713b.avif", "Unsplash"],
  [["할인점", "트레이더스", "이마트", "소매", "유통", "마트"], "business_image_33f95df49fba7bd7.jpg", "Wikimedia Commons"],
  [["은행", "대출", "예금", "금융"], "business_image_6d251c6de8f8e995.jpg", "Wikimedia Commons"],
  [["증권", "브로커리지", "투자", "운용"], "business_image_c1540b930934e19f.avif", "Unsplash"],
  [["보험", "손해보험", "생명보험"], "business_image_837140a1a79dbc33.jpg", "Wikimedia Commons"],
  [["바이오", "의약품", "제약", "CDMO", "임상", "백신"], "business_image_88477d76a420ca8a.avif", "Unsplash"],
  [["화학", "소재", "정유", "철강", "금속", "원재료"], "business_image_c5e03278f3aee100.jpg", "Wikimedia Commons"],
  [["전력", "발전", "송전", "전선", "OPGW", "케이블"], "business_image_93b560bdbc084531.jpg", "Wikimedia Commons"],
  [["통신", "광케이블", "광섬유", "네트워크", "무선"], "business_image_ca24250faeb63812.avif", "Unsplash"],
  [["게임", "콘텐츠", "미디어", "광고"], "business_image_7a64e307a92ba431.avif", "Unsplash"],
  [["식품", "담배", "화장품", "생활"], "business_image_c346f28a524bc889.avif", "Unsplash"],
];

const BAD_PARTS = [
  "기타부문", "기타 사업", "기타", "주요 사업", "사업", "서비스", "제품",
  "내부거래", "금융보증계약", "계약자산", "매출채권", "리스부채", "사용권자산",
  "영업부문", "보고부문", "연결조정", "조정", "B2B전자결제",
  "제품매출", "테스트 매출",
  "직접판매", "간접판매", "부가서비스제공가능여부", "무인증", "특징",
  "- 상용", "일용직 인사", "노무법인", "관련 부속품", "제품용역", "개발",
  "코스닥증권", "신규 서비스 확장성", "예산", "카드",
];

const CUSTOMER_PARTS = [
  "삼성전자, SK하이닉스", "삼성전자", "SK하이닉스", "삼성디스플레이", "윈팩",
  "LG전자", "현대차", "기아", "Apple", "NVIDIA", "TSMC", "Micron", "Intel", "Qualcomm",
  "Procera Networks", "MicroSoft", "Microsoft", "현대정보기술",
];

const EXACT_OVERRIDES = {
  "007310": [
    ["면제품류", "라면, 당면, 국수처럼 오뚜기의 대표적인 면류 제품을 제조·판매합니다.", "consumer", "NOODLE"],
    ["양념소스류", "카레, 케첩, 마요네즈, 소스류처럼 가정식 조리에 쓰이는 제품군입니다.", "consumer", "SAUCE"],
    ["농수산가공품류", "참치캔과 즉석식품 등 저장·간편식 수요에 연결되는 가공식품입니다.", "consumer", "CANNED"],
  ],
  "097950": [
    ["식품사업", "햇반, 만두, 김치, 간편식 등 국내외 소비자 식품 브랜드가 주력입니다.", "consumer", "FOOD"],
    ["소재식품", "설탕, 밀가루, 식용유 등 식품 제조와 외식 원가에 연결되는 기초 식품 소재를 공급합니다.", "consumer", "INGREDIENT"],
    ["바이오·FNT", "아미노산, 조미소재, 영양 소재처럼 글로벌 식품·사료 산업에 쓰이는 바이오 소재를 판매합니다.", "bio", "BIO"],
    ["사료·축산", "사료와 축산 사업은 곡물 가격과 글로벌 축산 수요 영향을 함께 받습니다.", "consumer", "FEED"],
  ],
  "066590": [
    ["자동차 파워트레인 부품", "변속기·엔진 등에 들어가는 알루미늄 다이캐스팅 부품을 생산합니다.", "auto", "PARTS"],
    ["자동차부품 상품 유통", "완성차와 부품 고객사의 생산·정비 수요에 맞춰 자동차부품 상품을 공급합니다.", "auto", "AUTO"],
  ],
  "210980": [
    ["데이터센터", "기업의 서버와 클라우드 수요를 받치는 데이터센터 개발·운영 사업입니다.", "infra", "DATA"],
    ["부동산 개발·운영", "오피스·상업시설 등 부동산 자산을 개발하고 임대·운영 수익을 만듭니다.", "realestate", "REAL"],
    ["재생에너지 전력판매", "태양광·풍력 등 발전자산에서 만든 전력을 판매하는 에너지 사업입니다.", "power", "SOLAR"],
  ],
  "000440": [
    ["유류판매", "주유소와 대리점 채널을 통해 일반유·LPG 등 에너지 제품을 판매합니다.", "material", "OIL"],
    ["부대 용역", "유류 판매와 함께 발생하는 부대 서비스 수익을 더합니다.", "service", "SERVICE"],
    ["부동산 임대", "보유 지점 부동산 임대수익이 보조 수익원으로 붙습니다.", "service", "RENT"],
    ["태양광 발전", "종속회사를 통해 태양광 전기발전 사업도 함께 운영합니다.", "power", "SOLAR"],
  ],
  "012790": [
    ["의약품 제조", "일반·전문·동물용 의약품과 위탁생산 제품을 다품종으로 만듭니다.", "bio", "PHARMA"],
    ["기능성 화장품", "제약 기술을 바탕으로 팜트리 브랜드 화장품을 판매합니다.", "consumer", "COSMETIC"],
    ["건강기능식품", "비타민 등 건강기능식품이 의약품 외 제품군을 보완합니다.", "consumer", "HEALTH"],
    ["의약외품", "마스크 등 생활 방역·위생 관련 제품을 함께 취급합니다.", "bio", "MED"],
  ],
  "067310": [
    ["반도체 패키징·테스트", "반도체 칩을 제품으로 쓸 수 있게 포장하고 검사하는 후공정 서비스입니다.", "chip", "PKG"],
    ["반도체 재료·Si-Parts", "식각 장비에 들어가는 실리콘·실리콘카바이드 소모성 부품을 공급합니다.", "chip", "Si"],
    ["반도체 공정소모품", "고객사의 공정 장비에서 반복 교체되는 부품이라 설비투자와 가동률 영향을 받습니다.", "chip", "PARTS"],
  ],
  "039570": [
    ["건설솔루션", "건축·기전·조경 인테리어 등 공간 시공과 시설 구축 프로젝트를 수행합니다.", "construction", "BUILD"],
    ["FM·PM 시설관리", "건물 설비와 자산을 운영·관리해 반복적인 관리 서비스 매출을 만듭니다.", "service", "FM"],
    ["라이프솔루션", "공간 운영과 생활 편의 서비스를 결합해 고객 건물의 운영 효율을 높입니다.", "service", "SERVICE"],
  ],
  "042500": [
    ["네트워크 구축·통합", "기업 고객의 네트워크 장비를 설계·구축하고 시스템을 통합하는 IT 서비스입니다.", "telecom", "NET"],
    ["클라우드 서비스", "클라우드 인프라와 관련 리셀·운영 서비스를 제공해 반복 수익을 만듭니다.", "platform", "CLOUD"],
    ["데이터센터 인프라", "서버와 네트워크 장비가 안정적으로 돌아가도록 인프라 구축·운영을 지원합니다.", "infra", "DATA"],
  ],
  "046310": [
    ["무전기·통신장비", "무전기와 통신장비를 생산해 산업·특수 통신 수요에 대응합니다.", "telecom", "RADIO"],
    ["블랙박스·차량기기", "차량용 영상기기와 전장 제품을 공급하는 전자장비 사업입니다.", "auto", "DVR"],
    ["레이더디텍터", "차량용 전자기기 라인업 중 운전자 보조 성격의 제품군입니다.", "auto", "RADAR"],
  ],
  "166090": [
    ["Si-Parts", "반도체 전공정 중 에칭 장비 안에서 웨이퍼를 깎는 데 쓰이는 실리콘 소모성 부품입니다.", "chip", "Si"],
    ["SiC-Parts", "고온·플라즈마 환경을 견디는 실리콘카바이드 부품으로 식각 공정 장비에 쓰입니다.", "chip", "SiC"],
    ["Electrode·Ring", "전극과 링처럼 반도체 식각 장비에 반복 투입되는 교체용 부품입니다.", "chip", "PARTS"],
  ],
  "131290": [
    ["Probe Card", "웨이퍼 위 반도체 칩이 정상 작동하는지 검사할 때 쓰는 핵심 테스트 부품입니다.", "chip", "PROBE"],
    ["Interface Board", "검사장비와 반도체 칩 사이의 신호를 연결해주는 테스트용 기판입니다.", "chip", "BOARD"],
    ["Contact Probe", "칩과 검사장비를 전기적으로 접촉시켜 불량 여부를 확인하는 미세 접촉 부품입니다.", "chip", "PROBE"],
    ["Interposer", "고성능 반도체 테스트 과정에서 신호 전달을 보조하는 정밀 부품입니다.", "chip", "TEST"],
  ],
  "003030": [
    ["강관 계열사", "세아제강 등 강관 사업 계열의 실적과 배당 흐름을 함께 보는 지주회사입니다.", "material", "PIPE"],
    ["지주·투자", "자회사 지분가치와 배당수익이 기업가치의 중심입니다.", "securities", "HOLD"],
  ],
  "011150": [
    ["수산가공식품", "어묵·맛살 등 수산가공 제품 판매가 핵심입니다.", "consumer", "FOOD"],
    ["식품 유통", "대형 유통채널과 식품 고객사 공급망이 매출에 연결됩니다.", "consumer", "RETAIL"],
  ],
  "093050": [
    ["패션 브랜드", "의류와 잡화 브랜드 판매가 핵심 사업입니다.", "consumer", "FASHION"],
    ["유통 채널", "오프라인 매장과 온라인몰을 함께 운영합니다.", "platform", "ONLINE"],
  ],
  "106190": [
    ["원료의약품", "의약품 생산에 쓰이는 원료의약품을 제조·판매합니다.", "bio", "API"],
    ["제약 소재", "고객 제약사의 생산 계획과 수출 수요가 실적에 연결됩니다.", "bio", "PHARMA"],
  ],
  "153890": [
    ["전기전자 부품", "전자제품 제조에 들어가는 부품을 공급합니다.", "service", "PARTS"],
    ["부품 제조", "고객사 생산량과 제품 교체 수요가 매출에 영향을 줍니다.", "service", "MFG"],
  ],
  "253450": [
    ["드라마 제작", "방송·OTT용 드라마 콘텐츠를 기획하고 제작합니다.", "platform", "CONTENT"],
    ["콘텐츠 유통", "방영권·판권·해외 판매가 매출에 연결됩니다.", "platform", "IP"],
  ],
  "365660": [
    ["모바일 헬스케어", "병원·환자용 모바일 서비스를 제공하는 헬스케어 플랫폼입니다.", "platform", "HEALTH"],
    ["의료 데이터 서비스", "병원 시스템과 환자 서비스를 연결하는 디지털 솔루션을 운영합니다.", "platform", "DATA"],
  ],
  "387690": [
    ["의료·전자 부품", "의료기기와 전자제품에 쓰이는 부품·장비를 공급합니다.", "service", "MED"],
    ["정밀 장비", "고객사 제품 개발과 생산 일정에 맞춰 장비·부품 매출이 발생합니다.", "service", "EQUIP"],
  ],
  "439960": [
    ["로봇 제품", "산업 현장과 서비스 영역에 쓰이는 로봇 제품을 개발합니다.", "service", "ROBOT"],
    ["자동화 솔루션", "공장·물류 자동화 수요가 사업 확장에 연결됩니다.", "service", "AUTO"],
  ],
  "466100": [
    ["로봇 소프트웨어", "로봇을 움직이고 관리하는 소프트웨어 플랫폼을 제공합니다.", "platform", "ROBOT"],
    ["로봇 관제", "여러 로봇을 한 화면에서 운영·관리하는 관제 솔루션이 핵심입니다.", "platform", "CONTROL"],
  ],
  "477850": [
    ["산업 AI 플랫폼", "제조·산업 데이터를 분석해 설비와 공정 의사결정을 돕는 AI 솔루션입니다.", "platform", "AI"],
    ["AI 운영 솔루션", "기업이 AI 모델을 배포하고 관리하는 소프트웨어를 제공합니다.", "platform", "MLOPS"],
  ],
  "493330": [
    ["DI-KIT", "재난·안전 분야에서 쓰이는 탐지·대응 장비 제품입니다.", "service", "SAFETY"],
    ["안전 장비", "소방·안전 현장의 장비 수요가 매출에 연결됩니다.", "service", "FIRE"],
  ],
  "950250": [
    ["검사 장비", "산업 현장에서 소재와 부품을 검사하는 장비 사업을 봅니다.", "service", "TEST"],
    ["장비 솔루션", "고객사 품질관리와 생산 공정에 연결되는 솔루션을 제공합니다.", "service", "EQUIP"],
  ],
};

function text(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function writeJson(file, value) {
  fs.writeFileSync(file, JSON.stringify(value, null, 2), "utf8");
}

function hasAny(source, words) {
  const lower = source.toLowerCase();
  return words.some((word) => lower.includes(String(word).toLowerCase()));
}

function isBadName(name, sector = "") {
  const clean = text(name).replace(/[.,/·ㆍ-]+$/g, "");
  if (clean.length < 2 || clean.length > 42) return true;
  if (/^[\d.,%()/*\- ]+$/.test(clean)) return true;
  if (CUSTOMER_PARTS.some((part) => clean.includes(part))) return true;
  if (BAD_PARTS.some((part) => clean === part || clean.startsWith(part + " ") || clean.includes(part + "(*"))) return true;
  if (!/금융|은행|증권|보험|투자/.test(sector) && /금융|예대|수수료|투자 등 금융/.test(clean)) return true;
  return false;
}

function sectorFallbackTitles(payload) {
  const sector = `${payload.sector || ""} ${payload.display_category || ""}`;
  if (/컴퓨터 프로그래밍|시스템 통합|정보서비스|SI|소프트웨어/.test(sector)) return ["시스템 구축·통합", "IT 인프라 운영", "소프트웨어·솔루션"];
  if (/통신|광케이블|네트워크/.test(sector)) return ["네트워크 장비·공사", "통신 인프라", "유지보수 서비스"];
  if (/식품|음식료|농수산|가공식품|음료/.test(sector)) return ["식품사업", "소재식품", "가공식품"];
  if (/소매|유통|마트|백화점|할인점/.test(sector)) return ["할인점", "전문점·온라인", "식품·생활용품"];
  if (/건설|토목|건축/.test(sector)) return ["건축", "토목", "주택·개발"];
  if (/섬유|의복|패션|방적/.test(sector)) return ["의류·섬유제품", "브랜드·상품", "임대·유통"];
  if (/의약|제약|바이오/.test(sector)) return ["전문의약품", "일반의약품", "건강기능·동물의약"];
  if (/자동차/.test(sector)) return ["자동차부품", "전장부품", "A/S·서비스"];
  if (/전자부품|전기장비/.test(sector)) return ["전자부품", "모듈·장비", "고객사 생산부품"];
  if (/철강|금속/.test(sector)) return ["철강제품", "가공제품", "임대·기타"];
  if (/석유|화학/.test(sector)) return ["석유·화학제품", "소재·원료", "임대·기타"];
  if (/부동산|임대/.test(sector)) return ["부동산 개발", "임대운영", "에너지·인프라"];
  return ["주력 제품·서비스", "부가 제품·서비스"];
}

function sectorType(payload) {
  const s = `${payload.sector || ""} ${payload.display_category || ""} ${payload.name || ""}`;
  if (/금융|은행|증권|보험/.test(s)) return "finance";
  if (/식품|음식료|농수산|가공식품|음료/.test(s)) return "food";
  if (/반도체|전자부품|정밀기기/.test(s)) return "semiconductor";
  if (/SI|소프트웨어|IT서비스|정보서비스|시스템|데이터센터/.test(s)) return "it_service";
  if (/통신|광케이블|네트워크/.test(s)) return "telecom";
  if (/건설|토목|건축|플랜트/.test(s)) return "construction";
  if (/섬유|의류|패션/.test(s)) return "textile";
  if (/시멘트|레미콘|건자재|유리|목재/.test(s)) return "building_material";
  if (/화학|석유|정유|소재|탄소/.test(s)) return "chemical";
  if (/소매|유통|마트|백화점/.test(s)) return "retail";
  if (/경비|경호|보안/.test(s)) return "security";
  if (/자동차/.test(s)) return "auto";
  if (/조선|선박|해양/.test(s)) return "ship";
  if (/바이오|의약품|제약/.test(s)) return "bio";
  return "general";
}

function incompatibleWordsForType(type) {
  const common = ["금융보증계약", "계약자산", "매출채권", "리스부채", "사용권자산", "단기매매증권", "현금,B2B전자결제"];
  if (type === "semiconductor") return [...common, "항공기", "방산", "화학약품", "신기술사업금융", "데이터센터", "전력사업"];
  if (type === "food") return [...common, "항공기", "방산", "데이터센터", "반도체", "전력사업", "신기술사업금융"];
  if (type === "finance") return ["항공기", "방산", "화학약품", "반도체 공정소모품", "패키징", "식품사업", "데이터센터"];
  if (type === "retail") return [...common, "항공기", "방산", "반도체", "전력사업"];
  if (type === "it_service") return [...common, "항공기", "방산", "식품사업", "화학약품", "은행", "보험", "증권"];
  if (type === "telecom") return [...common, "MLCC", "구리", "금융보증", "데이터센터"];
  if (type === "security") return [...common, "항공기", "방산", "식품사업", "화학약품"];
  if (type === "chemical") return [...common, "항공기", "데이터센터", "금융보증"];
  return common;
}

function productScore(name, payload) {
  const n = text(name);
  const type = sectorType(payload);
  let score = 10;
  if (incompatibleWordsForType(type).some((word) => n.includes(word))) score -= 160;
  if (type === "semiconductor") {
    if (/패키징|테스트|PKG|반도체칩부품화|OSAT/i.test(n)) score += 95;
    if (/Si-Parts|SiC-Parts|실리콘부품|공정소모품|Electrode|Ring|식각/i.test(n)) score += 90;
    if (/Probe|Probe Card|Contact Probe|Interposer|검사장치|BGA|PCB/i.test(n)) score += 80;
    if (/DRAM|NAND|HBM|CIS|이미지센서|Foundry|파운드리/i.test(n)) score += 70;
    if (/SSD|배터리|구리|화학약품/i.test(n)) score -= 45;
  } else if (type === "food") {
    if (/식품|소재식품|가공식품|면|라면|당면|국수|소스|양념|카레|케찹|케첩|마요네즈|참치|농수산|간편식|HMR|만두|김치|햇반|바이오|FNT|아미노산|조미소재|사료|축산/.test(n)) score += 90;
    if (/항공|항공기|방산|데이터센터|전력|반도체|금융보증|B2B전자결제|의약품|신기술사업금융/.test(n)) score -= 140;
  } else if (type === "retail") {
    if (/할인점|트레이더스|마트|백화점|온라인|이커머스|식품|생활|전문점/.test(n)) score += 80;
    if (/IT서비스|데이터센터|금융보증/.test(n)) score -= 60;
  } else if (type === "security") {
    if (/보안|시큐리티|경비|FM|PM|시설관리|자산관리|보안SI/.test(n)) score += 80;
  } else if (type === "it_service") {
    if (/SI|IT서비스|시스템|유지보수|인프라|데이터센터|클라우드|소프트웨어|솔루션|플랫폼|보안SI|VAN/.test(n)) score += 85;
  } else if (type === "telecom") {
    if (/통신|광케이블|광섬유|네트워크|OPGW|전력선|케이블/.test(n)) score += 85;
  } else if (type === "construction") {
    if (/건설|건축|토목|플랜트|주택|분양|공사|개발/.test(n)) score += 85;
  } else if (type === "textile") {
    if (/의류|패션|섬유|원단|브랜드|봉제|직물/.test(n)) score += 85;
  } else if (type === "building_material") {
    if (/시멘트|레미콘|건자재|유리|목재|합판|골재/.test(n)) score += 85;
  } else if (type === "chemical") {
    if (/화학|석유|정유|소재|수지|필름|도료|탄소|첨단소재|윤활유/.test(n)) score += 85;
  } else if (type === "finance") {
    if (/은행|대출|예금|카드|증권|브로커리지|보험|자산관리|운용|리스/.test(n)) score += 70;
  } else {
    if (/사업보고서상|고객사|거래처/.test(n)) score -= 80;
  }
  if (isBadName(n, payload.sector || "")) score -= 100;
  return score;
}

function kindVisual(name, payload) {
  const source = `${name} ${payload.sector || ""}`;
  if (/HBM|DRAM|NAND|반도체|PKG|Probe|Si-|실리콘|식각|PCB|BGA|검사/.test(source)) return ["chip", /HBM/.test(source) ? "HBM" : "CHIP"];
  if (/OLED|디스플레이|패널/.test(source)) return ["display", "OLED"];
  if (/배터리|2차전지|양극재/.test(source)) return ["battery", "BATTERY"];
  if (/자동차|전기차|하이브리드/.test(source)) return ["auto", "AUTO"];
  if (/선박|LNG|조선|해양/.test(source)) return ["ship", "SHIP"];
  if (/보안|경비|시큐리티/.test(source)) return ["service", "SECURITY"];
  if (/은행|대출|예금/.test(source)) return ["bank", "BANK"];
  if (/증권|운용|투자/.test(source)) return ["securities", "AUM"];
  if (/보험/.test(source)) return ["insurance", "INS"];
  if (/바이오|의약품|제약|CDMO/.test(source)) return ["bio", "BIO"];
  if (/통신|광케이블|네트워크/.test(source)) return ["telecom", "NET"];
  if (/전력|발전|송전|케이블/.test(source)) return ["power", "POWER"];
  if (/게임|플랫폼|콘텐츠/.test(source)) return ["platform", "APP"];
  if (/화학|소재|철강|금속|정유/.test(source)) return ["material", "MAT"];
  if (/소매|유통|식품|담배|화장품|생활/.test(source)) return ["consumer", "SHOP"];
  return ["service", "BUSINESS"];
}

function captionFor(name, payload) {
  const n = text(name);
  if (/시스템 유지보수/.test(n)) return "고객사의 업무 시스템과 장비가 안정적으로 돌아가도록 운영·점검하는 IT 서비스입니다.";
  if (/시스템 구축·통합/.test(n)) return "기업 업무에 필요한 서버, 네트워크, 소프트웨어를 묶어 하나의 시스템으로 구축합니다.";
  if (/IT 인프라 운영/.test(n)) return "서버, 네트워크, 보안 장비 같은 기업 IT 기반을 운영·관리하는 서비스입니다.";
  if (/데이터센터 인프라/.test(n)) return "서버와 네트워크 장비가 안정적으로 돌아가도록 데이터센터 기반을 구축·운영합니다.";
  if (/클라우드 서비스/.test(n)) return "기업이 서버와 소프트웨어를 직접 보유하지 않고 빌려 쓰도록 돕는 IT 서비스입니다.";
  if (/소프트웨어·솔루션/.test(n)) return "고객 업무를 자동화하거나 관리 효율을 높이는 소프트웨어 제품군입니다.";
  if (/플랫폼 서비스/.test(n)) return "여러 이용자와 서비스를 한곳에서 연결해 반복 이용을 만드는 디지털 서비스입니다.";
  if (/콘텐츠 서비스/.test(n)) return "차량·모바일·온라인 환경에서 소비되는 콘텐츠와 부가 서비스를 제공합니다.";
  if (/HR·급여관리 솔루션/.test(n)) return "임직원 급여, 인사, 근태 같은 기업 관리 업무를 소프트웨어로 처리하는 서비스입니다.";
  if (/무선랜/.test(n)) return "기업과 공공기관의 무선 네트워크 접속 환경을 구축하는 장비·서비스입니다.";
  if (/컨설팅/.test(n)) return "고객사의 업무 흐름과 IT 환경을 진단하고 시스템 개선 방향을 설계하는 서비스입니다.";
  if (/B2B 정비사업/.test(n)) return "차량과 서비스 사업자가 연결되는 기업 대상 정비·관리 플랫폼 사업입니다.";
  if (/면제품|라면|당면|국수/.test(n)) return "라면, 당면, 국수처럼 반복 구매가 많은 면류 제품군입니다.";
  if (/양념|소스|카레|케찹|케첩|마요네즈/.test(n)) return "가정식 조리와 외식 수요에 함께 쓰이는 소스·조미 제품군입니다.";
  if (/농수산|참치|가공식품|간편식|HMR|만두|김치|햇반/.test(n)) return "저장식품과 간편식처럼 소비자 식탁에 바로 닿는 가공식품입니다.";
  if (/소재식품|설탕|밀가루|식용유|원당|유지류/.test(n)) return "다른 식품을 만드는 데 들어가는 기초 소재라 원재료 가격 영향을 받습니다.";
  if (/사료|축산|F&C/.test(n)) return "곡물 가격과 축산 수요에 영향을 받는 사료·축산 사업입니다.";
  if (/패키징|테스트|PKG|반도체칩부품화|OSAT/i.test(n)) return "반도체 칩을 제품으로 쓸 수 있게 포장하고 검사하는 후공정 서비스입니다.";
  if (/Si-Parts|SiC-Parts|실리콘부품|공정소모품|Electrode|Ring|식각/i.test(n)) return "반도체 공정 장비에 들어가는 교체·소모성 부품입니다.";
  if (/Probe|Probe Card|Contact Probe|Interposer|검사장치/i.test(n)) return "반도체와 전자제품이 정상 작동하는지 검사하는 장비·부품입니다.";
  if (/DRAM|NAND|HBM|SSD/.test(n)) return "데이터 저장과 AI 서버 수요에 연결되는 메모리 제품입니다.";
  if (/CIS|이미지센서|카메라모듈/.test(n)) return "스마트폰과 전장 카메라에 들어가는 이미지 처리 부품입니다.";
  if (/OLED|디스플레이|패널/.test(n)) return "스마트폰·TV·IT기기에 화면을 제공하는 디스플레이 제품입니다.";
  if (/보안|시큐리티|경비/.test(n)) return "출동경비와 디지털 보안처럼 안전을 관리하는 서비스입니다.";
  if (/FM|PM|시설관리|자산관리/.test(n)) return "건물과 부동산 시설을 운영·관리하는 인프라 서비스입니다.";
  if (/은행|대출|예금/.test(n)) return "예금과 대출에서 이자이익을 만드는 금융 서비스입니다.";
  if (/증권|브로커리지|운용|자산관리/.test(n)) return "투자 중개와 자산관리 수수료가 실적에 연결됩니다.";
  if (/보험/.test(n)) return "보험료와 손해율이 실적을 좌우하는 금융 서비스입니다.";
  return `${n}을 중심으로 매출을 만드는 사업입니다.`;
}

function chooseImage(card, payload) {
  const source = `${card.title} ${card.caption} ${card.visual} ${payload.sector || ""}`;
  for (const [words, file, imageSource] of IMAGE_RULES) {
    if (hasAny(source, words)) return [IMG + file, imageSource];
  }
  return [IMG + "business_image_d205f8d7b04d385e.avif", "Unsplash"];
}

function makeCard(title, payload) {
  const [kind, visual] = kindVisual(title, payload);
  const card = { title, caption: captionFor(title, payload), kind, visual };
  const [image, image_source] = chooseImage(card, payload);
  return { ...card, image, image_source };
}

function normalizeCandidateName(name, payload) {
  const n = text(name);
  const type = sectorType(payload);
  if (type === "it_service") {
    if (/유지보수/.test(n)) return "시스템 유지보수";
    if (/급여|인사|노무/.test(n)) return "HR·급여관리 솔루션";
    if (/차세대|SI|시스템.?통합|구축/.test(n)) return "시스템 구축·통합";
    if (/인프라|서버|네트워크/.test(n)) return "IT 인프라 운영";
    if (/데이터센터/.test(n)) return "데이터센터 인프라";
    if (/클라우드|Cloud/i.test(n)) return "클라우드 서비스";
    if (/VAN/.test(n)) return "VAN 대행관리";
    if (/소프트웨어|솔루션|자사제품/.test(n)) return "소프트웨어·솔루션";
    if (/플랫폼/.test(n)) return "플랫폼 서비스";
    if (/콘텐츠/.test(n)) return "콘텐츠 서비스";
    if (/직접판매|간접판매/.test(n)) return "";
  }
  if (type === "telecom") {
    if (/광케이블|광섬유|OPGW/.test(n)) return "광케이블·통신선";
    if (/네트워크|통신/.test(n)) return "통신 네트워크";
    if (/유지보수/.test(n)) return "유지보수 서비스";
  }
  return n;
}

function candidateNames(payload) {
  const snippets = payload.snippets || {};
  const candidates = [];
  for (const product of snippets.products || []) candidates.push(normalizeCandidateName(product, payload));
  for (const seg of snippets.segment_breakdown || []) {
    if (seg && seg.name && text(seg.desc) !== "사업보고서상 주요 사업부문") {
      candidates.push(normalizeCandidateName(seg.name, payload));
    }
  }
  for (const card of payload.business_cards || []) candidates.push(normalizeCandidateName(card.title, payload));
  return [...new Set(candidates.filter(Boolean))];
}

function repairCards(payload) {
  const ticker = String(payload.stock_code || "").padStart(6, "0");
  if (EXACT_OVERRIDES[ticker]) {
    return EXACT_OVERRIDES[ticker].map(([title, caption, kind, visual]) => {
      const card = { title, caption, kind, visual };
      const [image, image_source] = chooseImage(card, payload);
      return { ...card, image, image_source };
    });
  }

  const names = candidateNames(payload)
    .map((name) => [name, productScore(name, payload)])
    .filter(([name, score]) => score > 0 && !isBadName(name, payload.sector || ""))
    .sort((a, b) => b[1] - a[1])
    .map(([name]) => name);

  const cards = [];
  for (const name of names) {
    if (cards.some((card) => card.title === name || card.title.includes(name) || name.includes(card.title))) continue;
    cards.push(makeCard(name, payload));
    if (cards.length >= 4) break;
  }
  if (cards.length >= 2) return cards;

  const existing = (payload.business_cards || []).filter((card) => !isBadName(card.title, payload.sector || ""));
  for (const card of existing) {
    if (cards.some((item) => item.title === card.title)) continue;
    cards.push(makeCard(card.title, payload));
    if (cards.length >= 2) break;
  }
  for (const title of sectorFallbackTitles(payload)) {
    if (cards.length >= 2) break;
    if (cards.some((item) => item.title === title)) continue;
    cards.push(makeCard(title, payload));
  }
  return cards;
}

function cleanOverviewText(value, payload) {
  const raw = text(value);
  if (!raw) return raw;
  const type = sectorType(payload);
  const banned = [...incompatibleWordsForType(type), ...CUSTOMER_PARTS];
  if (!["construction", "ship"].includes(type)) {
    banned.push("계약을 따낸 뒤", "제작·공사·납품", "수주형 사업", "건설 사업", "공사·납품", "프로젝트 구성이 이익");
  }
  if (!["semiconductor", "it_service", "telecom", "security"].includes(type)) {
    banned.push("데이터센터", "네트워크 구축", "Cloud서비스 리셀러");
  }
  if (["it_service", "telecom", "security"].includes(type)) {
    banned.push("제품을 만들고 판매하는 제조 기반 회사", "직접판매", "간접판매");
  }
  if (type !== "food") {
    banned.push("면제품류", "농수산가공품류", "양념소스류", "종합식품기업");
  }
  const sentences = raw
    .split(/(?<=[.!?。]|다\.|니다\.)\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean)
    .filter((sentence) => !banned.some((word) => sentence.includes(word)));
  return sentences.join(" ");
}

function cleanSnippets(payload) {
  const snippets = payload.snippets || {};
  snippets.segment_breakdown = (snippets.segment_breakdown || []).filter((seg) => {
    if (!seg || isBadName(seg.name, payload.sector || "")) return false;
    return text(seg.desc) !== "사업보고서상 주요 사업부문";
  });
  snippets.products = [...new Set((snippets.products || []).map(text).filter((name) => productScore(name, payload) > -20 && !isBadName(name, payload.sector || "")))];
  snippets.overview = cleanOverviewText(snippets.overview, payload);
  snippets.segment_finance = cleanOverviewText(snippets.segment_finance, payload);
  snippets.investor_note = cleanOverviewText(snippets.investor_note, payload);
  payload.snippets = snippets;
}

function needsRepair(payload) {
  const ticker = String(payload.stock_code || "").padStart(6, "0");
  if (EXACT_OVERRIDES[ticker]) return true;
  const cards = payload.business_cards || [];
  if (cards.length < 2) return true;
  if (cards.some((card) => isBadName(card.title, payload.sector || ""))) return true;
  if (cards.some((card) => text(card.caption).length < 8)) return true;
  if (cards.some((card) => /다른 식품|을 중심으로 매출을 만드는 사업입니다/.test(card.caption || ""))) return true;
  const type = sectorType(payload);
  const banned = incompatibleWordsForType(type);
  if (cards.some((card) => banned.some((word) => `${card.title} ${card.caption}`.includes(word)))) return true;
  if (type === "semiconductor" && cards.some((card) => /배터리|구리|화학약품|현금|B2B/.test(`${card.title} ${card.caption}`))) return true;
  if (type === "food" && cards.some((card) => /항공|항공기|방산|데이터센터|전력|금융보증|B2B전자결제|신기술사업금융/.test(`${card.title} ${card.caption}`))) return true;
  if (type === "food" && new Set(cards.map((card) => card.image)).size === 1 && cards.length >= 3) return true;
  if (cards.some((card) => /사업보고서상 주요 사업부문|주요 사업부문입니다/.test(card.caption || ""))) return true;
  return false;
}

let scanned = 0;
let repaired = 0;
for (const file of fs.readdirSync(DATA_DIR).filter((name) => /^business_\d{6}\.json$/.test(name)).sort()) {
  const full = path.join(DATA_DIR, file);
  const payload = readJson(full);
  scanned += 1;
  const before = JSON.stringify(payload);
  cleanSnippets(payload);
  if (needsRepair(payload)) {
    payload.business_cards = repairCards(payload);
  }
  if (JSON.stringify(payload) !== before) {
    writeJson(full, payload);
    repaired += 1;
  }
}

console.log(JSON.stringify({ scanned, repaired }, null, 2));
