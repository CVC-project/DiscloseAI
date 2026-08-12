const fs = require("fs");
const path = require("path");

const DATA_DIR = path.join(__dirname, "data");
const PILOT_DATA = path.join(
  __dirname,
  "..",
  "..",
  "docs",
  "prototype",
  "eqs_data_v3_kospi48_pilot.json",
);
const PROTECTED_STOCK_CODES = new Set(
  fs.existsSync(PILOT_DATA)
    ? JSON.parse(fs.readFileSync(PILOT_DATA, "utf8")).map((firm) => firm.stock_code)
    : [],
);

const INVALID_TITLE_RE =
  /^(판매\s*구분|판매구분|매출구분|제품구분|용도구분|법인\s*구분|고객\s*구분|지역구분|품목\s*구분|게임\s*구분|출시시점|장르|대상|총예산|직접\s*일자리|번호|내용|설명|적용제품|납기|납기일자|기납품액|진행률|상용화\s*여부|시제품\s*생산\s*완료|생산\(판매\)개시일|매입처|매입처명|반제품|비\s*고|비고|사진|권리자|구성비|생산실적|생산품목|완제품명|자사\s*제품|매출1위|제품설명|기대효과|연구내용|개발기관|등록일|분류|특허|국가|브랜드|국내등|사업부분|관련제품|제품류|제품상품용역기타|제품의\s*사용목적|사용목적|허가\s*획득일|게임명|게임\s*장르|No\.|소계\s*\(제품\+상품\)|용역|A사|USD\)|대\)|해|-?\s*국내|금액|판매금액|총계약금액|용역기간|연구기간|제\d+기|상품매출|제품매출|기타제품|용역매출|기타매출|영업수익|제품판매|제품합계|상품매출용역매출|상품\s*및\s*기타매출|계속영업사업\s*합계)$/;

const INVALID_TITLE_CONTAINS = [
  "내부거래",
  "금융보증계약",
  "계약자산",
  "계약부채",
  "매출채권",
  "연결조정",
  "기타매출",
  "수익인식금액",
  "계약상대방",
  "작업시간",
  "설계의뢰",
  "매입액",
  "상품 설명",
  "관련제품",
  "서비스)",
  "기타특수관계인",
  "특수관계인",
  "배관공급업",
  "구체적 사업내용",
  "구체적내용",
  "상세내용",
  "사업의 내용",
  "제품사진",
  "개발내용",
  "등록번호",
  "사고내용",
  "허가번호",
  "세부 설명",
  "세부설명",
  "게임 설명",
  "계약내용",
  "품목혀가번호",
  "서비스내용",
  "무인지로공과금수납기",
  "실내용",
];

const INVALID_CAPTION_RE =
  /(사업보고서상 주요 사업부문|중심으로 매출을 만드는 사업입니다|주요 사업부문입니다)/;

const GENERIC_CAPTION_RE =
  /(상품매출|용역매출|기타매출|영업수익|금액|기간|구분)을 중심으로 매출/;

const COMMON_FALLBACKS = {
  bio: [
    ["의약품", "치료제와 바이오 의약품 후보물질을 중심으로 사업을 전개합니다.", "bio", "BIO"],
    ["바이오 기술", "사업보고서의 연구개발과 기술이전 내용을 함께 봐야 하는 바이오 사업입니다.", "bio", "BIO"],
  ],
  software: [
    ["소프트웨어", "기업이나 개인 고객에게 필요한 소프트웨어 제품과 서비스를 제공합니다.", "platform", "SW"],
    ["IT 서비스", "시스템 구축, 운영, 유지보수 같은 디지털 서비스를 제공합니다.", "platform", "IT"],
  ],
  education: [
    ["교육 서비스", "학습 콘텐츠와 교육 프로그램을 제공하는 사업입니다.", "service", "EDU"],
    ["온라인 교육", "디지털 강의와 학습 플랫폼을 통해 수강생을 확보합니다.", "platform", "ONLINE"],
  ],
  construction: [
    ["건축공사", "건물과 주택을 짓는 공사 매출이 핵심입니다.", "construction", "BUILD"],
    ["토목공사", "도로, 교량, 기반시설 같은 인프라 공사를 수행합니다.", "construction", "CIVIL"],
  ],
  device: [
    ["장비·기기", "고객사의 생산이나 검사 공정에 쓰이는 장비를 공급합니다.", "service", "EQUIP"],
    ["부품·소모품", "장비에 반복 투입되는 부품과 소모품 수요가 실적에 연결됩니다.", "service", "PARTS"],
  ],
  food: [
    ["식품", "소비자가 반복 구매하는 식품 제품을 판매합니다.", "consumer", "FOOD"],
    ["건강기능식품", "건강관리 수요와 브랜드 신뢰가 중요한 제품군입니다.", "consumer", "HEALTH"],
  ],
  finance: [
    ["금융 서비스", "이자, 수수료, 투자 관련 수익이 실적에 연결됩니다.", "bank", "FIN"],
    ["자산 운용", "운용자산 규모와 시장 상황이 수수료 수익에 영향을 줍니다.", "securities", "AUM"],
  ],
  general: [
    ["주력 제품·서비스", "사업보고서의 제품과 서비스 설명을 바탕으로 정리한 핵심 사업입니다.", "service", "BUSINESS"],
    ["부가 사업", "주력 사업을 보완하는 제품이나 서비스 매출입니다.", "service", "SERVICE"],
  ],
};

function text(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function isInvalidTitle(title) {
  const clean = text(title);
  if (!clean) return true;
  if (INVALID_TITLE_RE.test(clean)) return true;
  if (INVALID_TITLE_CONTAINS.some((part) => clean.includes(part))) return true;
  if (clean.length <= 1) return true;
  if (/^[\d.,%()/*\- ]+$/.test(clean)) return true;
  return false;
}

function isInvalidForPayload(title, payload) {
  const clean = text(title);
  const source = `${payload.sector || ""} ${payload.display_category || ""} ${payload.name || ""}`;
  if (clean === "보험" && !/금융|보험|은행|증권/.test(source)) return true;
  if (clean === "방산" && /식품|의약|바이오|건강|전자부품|반도체/.test(source)) return true;
  if (clean === "배터리" && /의료|의약|바이오|식품/.test(source)) return true;
  if (clean === "의약품" && !/의약|제약|바이오|의료|연구개발/.test(source)) return true;
  if (
    /^[A-Z]{2,4}$/.test(clean) &&
    !/(DRAM|NAND|HBM|CIS|OLED|LED|SDC|MLCC|PACS|MRO|OTT|PG|VAN|ESS|EMS|SI|RF|AP|IP|AI|CPU|GPU)$/.test(clean)
  ) return true;
  return false;
}

function normalizeTitle(title) {
  let clean = text(title);
  clean = clean.replace(/^[-ㆍ·]\s*/, "");
  clean = clean.replace(/\s*사업부\s*합계$/, "사업부");
  clean = clean.replace(/\s*사업\s*합계$/, "");
  clean = clean.replace(/\s*합계$/, "");
  clean = clean.replace(/\s*매출$/, "");
  clean = clean.replace(/\s*외$/, "");
  return text(clean);
}

function sectorType(payload) {
  const source = `${payload.name || ""} ${payload.sector || ""} ${payload.display_category || ""}`;
  if (/금융|은행|증권|보험|투자|여신|자산운용/.test(source)) return "finance";
  if (/바이오|의약|제약|의료|연구개발/.test(source)) return "bio";
  if (/소프트웨어|정보|인터넷|게임|플랫폼|데이터|포털/.test(source)) return "software";
  if (/교육|학원|교습/.test(source)) return "education";
  if (/건설|건축|토목|주택/.test(source)) return "construction";
  if (/식품|음료|담배|농수산|건강기능/.test(source)) return "food";
  if (/기계|장비|정밀기기|전자부품|반도체/.test(source)) return "device";
  return "general";
}

function normalizeCaption(title, caption) {
  const clean = text(caption);
  if (!clean || INVALID_CAPTION_RE.test(clean) || GENERIC_CAPTION_RE.test(clean)) {
    return `${title} 관련 제품·서비스가 매출에 연결됩니다.`;
  }
  return clean;
}

function imageFor(kind, payload) {
  const source = `${kind || ""} ${payload.name || ""} ${payload.sector || ""} ${payload.display_category || ""}`;
  const file =
    /반도체/.test(source) ? "business_image_local_semiconductor_part.svg" :
    /바이오|의약|제약/.test(source) ? "business_image_local_pharma.svg" :
    /의료/.test(source) ? "business_image_local_medical_device.svg" :
    /교육|학원|교습/.test(source) ? "business_image_local_education.svg" :
    /건설|토목|건축|주택/.test(source) ? "business_image_local_construction.svg" :
    /전력|전기/.test(source) ? "business_image_local_power.svg" :
    /보안|경비|경호/.test(source) ? "business_image_local_security.svg" :
    /소프트웨어|플랫폼|IT|클라우드|인터넷|게임|콘텐츠/.test(source) ? "business_image_local_software.svg" :
    /식품|음식료|음료|담배|농수산/.test(source) ? "business_image_food_packaged.svg" :
    /금융|은행|여신/.test(source) ? "business_image_local_bank.svg" :
    /증권|투자/.test(source) ? "business_image_local_securities.svg" :
    /보험/.test(source) ? "business_image_local_insurance.svg" :
    /항공|방산|우주/.test(source) ? "business_image_local_safety.svg" :
    /화학|소재/.test(source) ? "business_image_local_chemical.svg" :
    /기계|장비/.test(source) ? "business_image_local_machinery.svg" :
    "business_image_local_default_a.svg";
  return `../data/business_images/${file}`;
}

function candidateNames(payload) {
  const snippets = payload.snippets || {};
  const candidates = [];
  for (const name of snippets.products || []) candidates.push(name);
  for (const seg of snippets.segment_breakdown || []) {
    if (seg && seg.name) candidates.push(seg.name);
  }
  for (const card of payload.business_cards || []) candidates.push(card.title);
  return candidates
    .map(normalizeTitle)
    .filter((name) => name && !isInvalidTitle(name));
}

function makeCard(title, caption, kind = "service", visual = "BUSINESS", baseCard = {}) {
  return {
    ...baseCard,
    title,
    caption: normalizeCaption(title, caption),
    kind: baseCard.kind || kind,
    visual: baseCard.visual || visual,
    image: baseCard.image || imageFor(baseCard.kind || kind, {}),
    image_source: baseCard.image_source || "Local curated visual",
  };
}

function sanitizeCards(payload) {
  const cards = payload.business_cards || [];
  const result = [];
  const seen = new Set();

  for (const card of cards) {
    if (isInvalidTitle(card.title)) continue;
    const title = normalizeTitle(card.title);
    if (isInvalidTitle(title)) continue;
    if (isInvalidForPayload(title, payload)) continue;
    if (seen.has(title)) continue;
    seen.add(title);
    result.push(makeCard(title, card.caption, card.kind, card.visual, card));
  }

  for (const name of candidateNames(payload)) {
    if (result.length >= 2) break;
    if (seen.has(name)) continue;
    if (isInvalidForPayload(name, payload)) continue;
    seen.add(name);
    result.push(makeCard(name, "", "service", "BUSINESS", { image: imageFor("service", payload) }));
  }

  if (result.length < 2) {
    const fallback = COMMON_FALLBACKS[sectorType(payload)] || COMMON_FALLBACKS.general;
    for (const [title, caption, kind, visual] of fallback) {
      if (result.length >= 2) break;
      if (seen.has(title)) continue;
      seen.add(title);
      result.push(makeCard(title, caption, kind, visual, { image: imageFor(kind, payload) }));
    }
  }

  return result;
}

function needsSanitize(payload) {
  return (payload.business_cards || []).some((card) => {
    if (isInvalidTitle(card.title)) return true;
    const title = normalizeTitle(card.title);
    return isInvalidTitle(title) || INVALID_CAPTION_RE.test(text(card.caption)) || GENERIC_CAPTION_RE.test(text(card.caption));
  });
}

let scanned = 0;
let changed = 0;
const changedCompanies = [];

for (const file of fs.readdirSync(DATA_DIR).filter((name) => /^business_\d{6}\.json$/.test(name)).sort()) {
  const fullPath = path.join(DATA_DIR, file);
  const payload = JSON.parse(fs.readFileSync(fullPath, "utf8"));
  scanned += 1;
  if (PROTECTED_STOCK_CODES.has(payload.stock_code || file.slice(9, 15))) continue;
  const before = JSON.stringify(payload.business_cards || []);
  payload.business_cards = sanitizeCards(payload);
  const after = JSON.stringify(payload.business_cards || []);
  if (before !== after) {
    fs.writeFileSync(fullPath, JSON.stringify(payload, null, 2), "utf8");
    changed += 1;
    changedCompanies.push({
      code: payload.stock_code || file.slice(9, 15),
      name: payload.name,
      cards: payload.business_cards.map((card) => card.title),
    });
  }
}

console.log(JSON.stringify({ scanned, changed, samples: changedCompanies.slice(0, 40) }, null, 2));
