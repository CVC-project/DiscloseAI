const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "dossier", "data");
const IMG = "../data/business_images/";

const IMAGE_RULES = [
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
];

const CUSTOMER_PARTS = [
  "삼성전자, SK하이닉스", "삼성전자", "SK하이닉스", "삼성디스플레이", "윈팩",
  "LG전자", "현대차", "기아", "Apple", "NVIDIA", "TSMC", "Micron", "Intel", "Qualcomm",
];

const EXACT_OVERRIDES = {
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
  if (/반도체|전자부품|정밀기기/.test(s)) return "semiconductor";
  if (/소매|유통|마트|백화점/.test(s)) return "retail";
  if (/경비|경호|보안/.test(s)) return "security";
  if (/자동차/.test(s)) return "auto";
  if (/조선|선박|해양/.test(s)) return "ship";
  if (/바이오|의약품|제약/.test(s)) return "bio";
  return "general";
}

function productScore(name, payload) {
  const n = text(name);
  const type = sectorType(payload);
  let score = 10;
  if (type === "semiconductor") {
    if (/패키징|테스트|PKG|반도체칩부품화|OSAT/i.test(n)) score += 95;
    if (/Si-Parts|SiC-Parts|실리콘부품|공정소모품|Electrode|Ring|식각/i.test(n)) score += 90;
    if (/Probe|Probe Card|Contact Probe|Interposer|검사장치|BGA|PCB/i.test(n)) score += 80;
    if (/DRAM|NAND|HBM|CIS|이미지센서|Foundry|파운드리/i.test(n)) score += 70;
    if (/SSD|배터리|구리|화학약품/i.test(n)) score -= 45;
  } else if (type === "retail") {
    if (/할인점|트레이더스|마트|백화점|온라인|이커머스|식품|생활|전문점/.test(n)) score += 80;
    if (/IT서비스|데이터센터|금융보증/.test(n)) score -= 60;
  } else if (type === "security") {
    if (/보안|시큐리티|경비|FM|PM|시설관리|자산관리|보안SI/.test(n)) score += 80;
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

function candidateNames(payload) {
  const snippets = payload.snippets || {};
  const candidates = [];
  for (const seg of snippets.segment_breakdown || []) {
    if (seg && seg.name && text(seg.desc) !== "사업보고서상 주요 사업부문") {
      candidates.push(text(seg.name));
    }
  }
  for (const product of snippets.products || []) candidates.push(text(product));
  for (const card of payload.business_cards || []) candidates.push(text(card.title));
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

function cleanSnippets(payload) {
  const snippets = payload.snippets || {};
  snippets.segment_breakdown = (snippets.segment_breakdown || []).filter((seg) => {
    if (!seg || isBadName(seg.name, payload.sector || "")) return false;
    return text(seg.desc) !== "사업보고서상 주요 사업부문";
  });
  snippets.products = [...new Set((snippets.products || []).map(text).filter((name) => productScore(name, payload) > -20 && !isBadName(name, payload.sector || "")))];
  payload.snippets = snippets;
}

function needsRepair(payload) {
  const ticker = String(payload.stock_code || "").padStart(6, "0");
  if (EXACT_OVERRIDES[ticker]) return true;
  const cards = payload.business_cards || [];
  if (cards.length < 2) return true;
  if (cards.some((card) => isBadName(card.title, payload.sector || ""))) return true;
  if (cards.some((card) => text(card.caption).length < 8)) return true;
  const type = sectorType(payload);
  if (type === "semiconductor" && cards.some((card) => /배터리|구리|화학약품|현금|B2B/.test(`${card.title} ${card.caption}`))) return true;
  if (cards.some((card) => /사업보고서상 주요 사업부문|주요 사업부문입니다/.test(card.caption || ""))) return true;
  return false;
}

let scanned = 0;
let repaired = 0;
for (const file of fs.readdirSync(DATA_DIR).filter((name) => /^business_\d{6}\.json$/.test(name)).sort()) {
  const full = path.join(DATA_DIR, file);
  const payload = readJson(full);
  scanned += 1;
  const before = JSON.stringify(payload.business_cards || []);
  cleanSnippets(payload);
  if (needsRepair(payload)) {
    payload.business_cards = repairCards(payload);
  }
  if (JSON.stringify(payload.business_cards || []) !== before) {
    writeJson(full, payload);
    repaired += 1;
  }
}

console.log(JSON.stringify({ scanned, repaired }, null, 2));
