const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "dossier", "data");
const IMAGE_DIR = path.join(ROOT, "data", "business_images");

const badTitle = [
  "기타부문",
  "내부거래",
  "금융보증계약",
  "계약자산",
  "매출채권",
  "리스부채",
  "사용권자산",
  "영업부문",
  "보고부문",
  "연결조정",
  "조정",
  "B2B전자결제",
  "제품매출",
  "테스트 매출",
];

const counterparties = [
  "삼성전자, SK하이닉스",
  "삼성디스플레이",
  "SK하이닉스",
  "삼성전자",
  "LG전자",
  "현대차",
  "기아",
  "Apple",
  "NVIDIA",
  "TSMC",
  "Micron",
  "Intel",
  "Qualcomm",
];

function clean(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function imageExists(image) {
  if (!image) return false;
  const file = image.replace("../data/business_images/", "");
  return fs.existsSync(path.join(IMAGE_DIR, file));
}

function sectorType(payload) {
  const source = `${payload.sector || ""} ${payload.display_category || ""} ${payload.name || ""}`;
  if (/식품|음식료|농수산|가공식품|음료/.test(source)) return "food";
  if (/반도체|전자부품|정밀기기/.test(source)) return "semiconductor";
  if (/소매|유통|마트|백화점/.test(source)) return "retail";
  if (/경비|경호|보안/.test(source)) return "security";
  return "general";
}

function sectorMismatch(payload, combined) {
  const type = sectorType(payload);
  if (type === "food") {
    return /항공|항공기|방산|데이터센터|전력|금융보증|B2B전자결제|신기술사업금융/.test(combined);
  }
  if (type === "semiconductor") {
    return /현금|B2B전자결제|금융보증/.test(combined);
  }
  return false;
}

const issueCounts = {};
const companies = [];
for (const file of fs.readdirSync(DATA_DIR).filter((name) => /^business_\d{6}\.json$/.test(name)).sort()) {
  const payload = JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), "utf8"));
  const cards = Array.isArray(payload.business_cards) ? payload.business_cards : [];
  const issues = [];
  if (cards.length < 2) issues.push("too_few_cards");
  for (const card of cards) {
    const title = clean(card.title);
    const caption = clean(card.caption);
    const combined = `${title} ${caption}`;
    if (!title) issues.push("empty_title");
    if (badTitle.some((part) => title.includes(part))) issues.push("bad_title");
    if (counterparties.some((part) => title.includes(part))) issues.push("counterparty_title");
    if (!caption || caption.length < 8) issues.push("bad_caption");
    if (/하며$|이고$|이며$|통해$|위해$|생산하며$|판매하며$|제공하며$/.test(caption)) issues.push("unfinished_caption");
    if (!imageExists(clean(card.image))) issues.push("missing_image");
    if (counterparties.some((part) => combined.includes(part))) issues.push("counterparty_text");
    if (sectorMismatch(payload, combined)) issues.push("sector_mismatch");
  }
  const images = cards.map((card) => clean(card.image)).filter(Boolean);
  const genericImageDupes = [
    "business_image_c346f28a524bc889.avif",
    "business_image_d205f8d7b04d385e.avif",
  ];
  if (
    cards.length >= 3 &&
    images.length === cards.length &&
    new Set(images).size === 1 &&
    genericImageDupes.some((name) => images[0].includes(name))
  ) {
    issues.push("duplicate_generic_images");
  }
  for (const issue of issues) issueCounts[issue] = (issueCounts[issue] || 0) + 1;
  if (issues.length) {
    companies.push({
      code: clean(payload.stock_code || file.match(/\d{6}/)?.[0]),
      name: clean(payload.name),
      sector: clean(payload.sector || payload.display_category),
      issues: [...new Set(issues)],
      cards: cards.map((card) => clean(card.title)),
    });
  }
}

const report = {
  scanned: fs.readdirSync(DATA_DIR).filter((name) => /^business_\d{6}\.json$/.test(name)).length,
  companies_with_issues: companies.length,
  issueCounts,
  sample: companies.slice(0, 30),
};

const reportDir = path.join(ROOT, "dossier", "reports");
fs.mkdirSync(reportDir, { recursive: true });
fs.writeFileSync(path.join(reportDir, "business_card_quality_quick.json"), JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));
