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
