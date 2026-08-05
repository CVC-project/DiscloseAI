const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "dossier", "data");
const IMAGE_DIR = path.join(ROOT, "data", "business_images");
const IMG = "../data/business_images/";

const LOCAL_VISUALS = {
  alcohol: ["business_image_local_alcohol.svg", "Local curated visual", "주류", "#40e0d0", "#f6d365", "bottle"],
  wood: ["business_image_local_wood.svg", "Local curated visual", "목재", "#c88b4a", "#6ee7b7", "planks"],
  textile: ["business_image_local_textile.svg", "Local curated visual", "섬유", "#a78bfa", "#38bdf8", "fabric"],
  fashion: ["business_image_local_fashion.svg", "Local curated visual", "패션", "#fb7185", "#facc15", "shirt"],
  construction: ["business_image_local_construction.svg", "Local curated visual", "건설", "#38bdf8", "#f97316", "crane"],
  housing: ["business_image_local_housing.svg", "Local curated visual", "주택", "#34d399", "#60a5fa", "building"],
  cement: ["business_image_local_cement.svg", "Local curated visual", "시멘트", "#94a3b8", "#fde68a", "blocks"],
  tire: ["business_image_local_tire.svg", "Local curated visual", "타이어", "#60a5fa", "#111827", "tire"],
  instrument: ["business_image_local_instrument.svg", "Local curated visual", "악기", "#f59e0b", "#a78bfa", "piano"],
  packaging: ["business_image_local_packaging.svg", "Local curated visual", "포장", "#22d3ee", "#a3e635", "box"],
  crystal: ["business_image_local_crystal.svg", "Local curated visual", "수정진동자", "#67e8f9", "#818cf8", "chip"],
  machinery: ["business_image_local_machinery.svg", "Local curated visual", "기계", "#fbbf24", "#38bdf8", "gear"],
  oil: ["business_image_local_oil.svg", "Local curated visual", "윤활유", "#f59e0b", "#111827", "drop"],
  rubber: ["business_image_local_rubber.svg", "Local curated visual", "고무", "#64748b", "#22d3ee", "molecule"],
  feed: ["business_image_local_feed.svg", "Local curated visual", "사료", "#84cc16", "#f59e0b", "grain"],
  agro: ["business_image_local_agro.svg", "Local curated visual", "농약", "#22c55e", "#eab308", "leaf"],
  mro: ["business_image_local_mro.svg", "Local curated visual", "MRO", "#38bdf8", "#f97316", "tools"],
  pharma: ["business_image_local_pharma.svg", "Local curated visual", "제약", "#22d3ee", "#a78bfa", "pill"],
  cosmetics: ["business_image_local_cosmetics.svg", "Local curated visual", "화장품", "#f472b6", "#facc15", "drop"],
  education: ["business_image_local_education.svg", "Local curated visual", "교육", "#60a5fa", "#facc15", "book"],
  content: ["business_image_local_content.svg", "Local curated visual", "콘텐츠", "#a78bfa", "#22d3ee", "play"],
  robot: ["business_image_local_robot.svg", "Local curated visual", "로봇", "#22d3ee", "#f472b6", "robot"],
  ai: ["business_image_local_ai.svg", "Local curated visual", "AI", "#22d3ee", "#818cf8", "nodes"],
  healthcare: ["business_image_local_healthcare.svg", "Local curated visual", "헬스케어", "#34d399", "#60a5fa", "cross"],
  medical_device: ["business_image_local_medical_device.svg", "Local curated visual", "의료기기", "#38bdf8", "#f472b6", "device"],
  safety: ["business_image_local_safety.svg", "Local curated visual", "안전", "#fb7185", "#facc15", "shield"],
  network: ["business_image_local_network.svg", "Local curated visual", "네트워크", "#22d3ee", "#60a5fa", "nodes"],
  cloud: ["business_image_local_cloud.svg", "Local curated visual", "클라우드", "#38bdf8", "#a78bfa", "cloud"],
  datacenter: ["business_image_local_datacenter.svg", "Local curated visual", "데이터센터", "#60a5fa", "#22d3ee", "server"],
  software: ["business_image_local_software.svg", "Local curated visual", "소프트웨어", "#22d3ee", "#34d399", "window"],
  fm: ["business_image_local_fm.svg", "Local curated visual", "FM/PM", "#38bdf8", "#facc15", "building"],
  security: ["business_image_local_security.svg", "Local curated visual", "보안", "#22d3ee", "#fb7185", "shield"],
  retail: ["business_image_local_retail.svg", "Local curated visual", "유통", "#34d399", "#facc15", "store"],
  department: ["business_image_local_department.svg", "Local curated visual", "백화점", "#f472b6", "#60a5fa", "store"],
  convenience: ["business_image_local_convenience.svg", "Local curated visual", "편의점", "#22d3ee", "#f97316", "store"],
  logistics: ["business_image_local_logistics.svg", "Local curated visual", "물류", "#38bdf8", "#f97316", "truck"],
  finance_hold: ["business_image_local_finance_hold.svg", "Local curated visual", "지주", "#60a5fa", "#facc15", "hold"],
  bank: ["business_image_local_bank.svg", "Local curated visual", "은행", "#22d3ee", "#34d399", "bank"],
  card: ["business_image_local_card.svg", "Local curated visual", "카드", "#38bdf8", "#f472b6", "card"],
  securities: ["business_image_local_securities.svg", "Local curated visual", "증권", "#34d399", "#facc15", "chart"],
  insurance: ["business_image_local_insurance.svg", "Local curated visual", "보험", "#60a5fa", "#a78bfa", "shield"],
  ship: ["business_image_local_ship.svg", "Local curated visual", "선박", "#38bdf8", "#60a5fa", "ship"],
  offshore: ["business_image_local_offshore.svg", "Local curated visual", "해양플랜트", "#22d3ee", "#f97316", "rig"],
  power: ["business_image_local_power.svg", "Local curated visual", "전력", "#facc15", "#38bdf8", "bolt"],
  cable: ["business_image_local_cable.svg", "Local curated visual", "전선", "#f97316", "#22d3ee", "cable"],
  steel: ["business_image_local_steel.svg", "Local curated visual", "철강", "#94a3b8", "#f97316", "beam"],
  chemical: ["business_image_local_chemical.svg", "Local curated visual", "화학", "#34d399", "#60a5fa", "molecule"],
  battery: ["business_image_local_battery.svg", "Local curated visual", "배터리", "#34d399", "#facc15", "battery"],
  display: ["business_image_local_display.svg", "Local curated visual", "디스플레이", "#a78bfa", "#22d3ee", "screen"],
  auto_part: ["business_image_local_auto_part.svg", "Local curated visual", "자동차부품", "#38bdf8", "#f97316", "gear"],
  semiconductor_part: ["business_image_local_semiconductor_part.svg", "Local curated visual", "반도체부품", "#fbbf24", "#22d3ee", "chip"],
  semiconductor_pkg: ["business_image_local_semiconductor_pkg.svg", "Local curated visual", "패키징", "#fbbf24", "#34d399", "box"],
  silicon_part: ["business_image_local_silicon_part.svg", "Local curated visual", "Si-Parts", "#22d3ee", "#fbbf24", "chip"],
  sic_part: ["business_image_local_sic_part.svg", "Local curated visual", "SiC", "#a78bfa", "#22d3ee", "chip"],
  electrode_ring: ["business_image_local_electrode_ring.svg", "Local curated visual", "Electrode", "#f472b6", "#fbbf24", "probe"],
  electronic_part: ["business_image_local_electronic_part.svg", "Local curated visual", "전자부품", "#38bdf8", "#facc15", "chip"],
  probe: ["business_image_local_probe.svg", "Local curated visual", "검사부품", "#22d3ee", "#a78bfa", "probe"],
  default_a: ["business_image_local_default_a.svg", "Local curated visual", "사업", "#22d3ee", "#64748b", "window"],
  default_b: ["business_image_local_default_b.svg", "Local curated visual", "제품", "#a78bfa", "#64748b", "box"],
  default_c: ["business_image_local_default_c.svg", "Local curated visual", "서비스", "#34d399", "#64748b", "nodes"],
  default_d: ["business_image_local_default_d.svg", "Local curated visual", "인프라", "#facc15", "#64748b", "building"],
  food_noodle: ["business_image_food_noodle.svg", "Local visual", "면류", "#22d3ee", "#facc15", "grain"],
  food_sauce: ["business_image_food_sauce.svg", "Local visual", "소스", "#fb7185", "#facc15", "drop"],
  food_packaged: ["business_image_food_packaged.svg", "Local visual", "가공식품", "#34d399", "#facc15", "box"],
  food_ingredient: ["business_image_food_ingredient.svg", "Local visual", "소재식품", "#fbbf24", "#a78bfa", "grain"],
  food_feed: ["business_image_food_feed.svg", "Local visual", "사료", "#84cc16", "#f59e0b", "grain"],
};

const REAL_ASSETS = [
  [["HBM", "고대역폭"], "business_image_df7b448e6d568266.jpg", "Wikimedia Commons"],
  [["DRAM", "메모리"], "business_image_10774ca82ea41202.jpg", "Wikimedia Commons"],
  [["NAND", "SSD", "스토리지"], "business_image_b24ab2723180c79f.jpg", "Wikimedia Commons"],
  [["CIS", "이미지센서"], "business_image_025006447be31665.jpg", "Wikimedia Commons"],
  [["OLED", "디스플레이", "패널"], "business_image_d41fecd0a3904c17.jpg", "Wikimedia Commons"],
  [["스마트폰", "Galaxy", "TV", "모니터", "생활가전"], "business_image_141eab6519656e30.jpg", "Wikimedia Commons"],
  [["Harman", "디지털 콕핏", "카오디오"], "business_image_8b1b40ffeb79bd60.jpg", "Wikimedia Commons"],
  [["자동차", "완성차", "전기차", "하이브리드"], "business_image_3918919e2e6dfce9.avif", "Unsplash"],
  [["항공엔진"], "business_image_1805fba8159acac6.avif", "Unsplash"],
  [["방산", "K9", "탄약"], "business_image_4ae102473975707c.jpg", "Wikimedia Commons"],
  [["우주", "위성"], "business_image_a36fe45e187e177c.jpg", "Wikimedia"],
];

const BAD_DUPES = new Set([
  "../data/business_images/business_image_c346f28a524bc889.avif",
  "../data/business_images/business_image_d205f8d7b04d385e.avif",
]);

function clean(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function hasAny(source, words) {
  const lower = source.toLowerCase();
  return words.some((word) => lower.includes(String(word).toLowerCase()));
}

function svgShape(type) {
  const common = 'stroke="rgba(255,255,255,.72)" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"';
  if (type === "bottle") return `<path ${common} d="M118 68h28v34c0 12 24 18 24 44v88c0 22-18 38-38 38s-38-16-38-38v-88c0-26 24-32 24-44V68z"/><path ${common} d="M210 96h44v176h-44z"/>`;
  if (type === "planks") return `<path ${common} d="M74 128h212M74 174h212M74 220h212"/><path ${common} d="M110 96v156M180 96v156M250 96v156"/>`;
  if (type === "fabric") return `<path ${common} d="M82 102c60 34 118-34 194 0v144c-76-34-134 34-194 0z"/><path ${common} d="M122 122v138M178 94v138M234 102v138"/>`;
  if (type === "shirt") return `<path ${common} d="M122 90l38 26 38-26 56 30-28 54-28-12v112h-76V162l-28 12-28-54z"/>`;
  if (type === "crane") return `<path ${common} d="M92 252h168M126 252V94h118M126 124l118-30 42 30M244 94v62l28 18"/><path ${common} d="M108 252l38-64h64l38 64"/>`;
  if (type === "building") return `<path ${common} d="M92 256V96h84v160M176 256V136h96v120"/><path ${common} d="M118 126h22M118 162h22M118 198h22M204 166h30M204 202h30"/>`;
  if (type === "blocks") return `<path ${common} d="M74 126h84v58H74zM166 126h84v58h-84zM112 194h84v58h-84zM204 194h84v58h-84z"/>`;
  if (type === "tire") return `<circle ${common} cx="180" cy="180" r="86"/><circle ${common} cx="180" cy="180" r="34"/><path ${common} d="M180 94v42M180 224v42M94 180h42M224 180h42"/>`;
  if (type === "piano") return `<path ${common} d="M84 122h196v92H84zM106 214v42M258 214v42"/><path ${common} d="M112 150v42M138 150v42M164 150v42M190 150v42M216 150v42M242 150v42"/>`;
  if (type === "box") return `<path ${common} d="M90 126l90-44 90 44v102l-90 50-90-50z"/><path ${common} d="M90 126l90 50 90-50M180 176v102"/>`;
  if (type === "chip") return `<rect ${common} x="110" y="110" width="140" height="140" rx="20"/><path ${common} d="M80 140h30M80 180h30M80 220h30M250 140h30M250 180h30M250 220h30M140 80v30M180 80v30M220 80v30M140 250v30M180 250v30M220 250v30"/>`;
  if (type === "gear") return `<circle ${common} cx="180" cy="180" r="48"/><path ${common} d="M180 84v38M180 238v38M84 180h38M238 180h38M112 112l28 28M220 220l28 28M248 112l-28 28M140 220l-28 28"/>`;
  if (type === "drop") return `<path ${common} d="M180 74c54 66 82 106 82 146 0 46-36 76-82 76s-82-30-82-76c0-40 28-80 82-146z"/>`;
  if (type === "molecule") return `<circle ${common} cx="108" cy="160" r="28"/><circle ${common} cx="210" cy="112" r="28"/><circle ${common} cx="238" cy="220" r="28"/><path ${common} d="M134 148l50-24M128 176l84 32"/>`;
  if (type === "grain") return `<path ${common} d="M180 72v220M180 128c-52-24-76-8-90 24 48 22 74 10 90-24zM180 184c52-24 76-8 90 24-48 22-74 10-90-24z"/>`;
  if (type === "leaf") return `<path ${common} d="M80 236c134-4 184-74 202-154-94 2-176 44-202 154z"/><path ${common} d="M100 220c50-50 98-80 156-104"/>`;
  if (type === "tools") return `<path ${common} d="M98 112l150 150M232 92l36 36-68 68-36-36zM104 236l44-44"/>`;
  if (type === "pill") return `<path ${common} d="M118 220a44 44 0 010-62l40-40a44 44 0 0162 62l-40 40a44 44 0 01-62 0z"/><path ${common} d="M150 150l60 60"/>`;
  if (type === "book") return `<path ${common} d="M82 104h92c24 0 38 12 38 32v128c0-20-14-32-38-32H82zM212 136c0-20 14-32 38-32h28v128h-28c-24 0-38 12-38 32z"/>`;
  if (type === "play") return `<rect ${common} x="82" y="106" width="196" height="132" rx="18"/><path ${common} d="M160 140l66 32-66 34z"/>`;
  if (type === "robot") return `<rect ${common} x="108" y="122" width="144" height="112" rx="22"/><path ${common} d="M180 82v40M138 162h4M218 162h4M148 204h64M82 172h26M252 172h26"/>`;
  if (type === "nodes") return `<circle ${common} cx="110" cy="178" r="24"/><circle ${common} cx="202" cy="112" r="24"/><circle ${common} cx="250" cy="226" r="24"/><path ${common} d="M130 164l52-38M130 190l96 26"/>`;
  if (type === "cross") return `<path ${common} d="M154 92h52v62h62v52h-62v62h-52v-62H92v-52h62z"/>`;
  if (type === "device") return `<rect ${common} x="104" y="86" width="152" height="204" rx="18"/><path ${common} d="M132 132h96M132 170h96M132 208h58"/>`;
  if (type === "shield") return `<path ${common} d="M180 74l94 38v70c0 62-40 96-94 118-54-22-94-56-94-118v-70z"/><path ${common} d="M140 180l28 28 58-68"/>`;
  if (type === "cloud") return `<path ${common} d="M118 226h116c28 0 50-18 50-44 0-24-20-42-46-42-12-38-66-52-96-14-34-4-64 18-64 50 0 28 18 50 40 50z"/>`;
  if (type === "server") return `<rect ${common} x="92" y="92" width="176" height="58" rx="12"/><rect ${common} x="92" y="162" width="176" height="58" rx="12"/><rect ${common} x="92" y="232" width="176" height="58" rx="12"/><path ${common} d="M124 121h6M124 191h6M124 261h6M154 121h74M154 191h74M154 261h74"/>`;
  if (type === "window") return `<rect ${common} x="90" y="100" width="180" height="150" rx="16"/><path ${common} d="M90 140h180M126 122h4M150 122h4M174 122h4"/>`;
  if (type === "store") return `<path ${common} d="M84 142l24-54h144l24 54M104 142v122h152V142M132 184h48v80M202 184h32"/>`;
  if (type === "truck") return `<path ${common} d="M74 142h128v78H74zM202 166h58l28 34v20h-86z"/><circle ${common} cx="122" cy="234" r="18"/><circle ${common} cx="242" cy="234" r="18"/>`;
  if (type === "hold") return `<path ${common} d="M90 218h180M110 218V118h140v100M134 146h24M188 146h38M134 182h92"/>`;
  if (type === "bank") return `<path ${common} d="M80 132l100-54 100 54zM104 132v116M154 132v116M206 132v116M256 132v116M76 248h208"/>`;
  if (type === "card") return `<rect ${common} x="78" y="112" width="204" height="136" rx="20"/><path ${common} d="M78 154h204M112 202h58"/>`;
  if (type === "chart") return `<path ${common} d="M86 252h188M116 218l44-48 42 26 58-86"/><path ${common} d="M116 218h2M160 170h2M202 196h2M260 110h2"/>`;
  if (type === "ship") return `<path ${common} d="M72 194h216l-36 58H108zM116 154h112l28 40H92z"/><path ${common} d="M132 154v-42h52v42"/>`;
  if (type === "rig") return `<path ${common} d="M96 248l84-156 84 156M132 248l48-90 48 90M112 184h136M144 124h72"/>`;
  if (type === "bolt") return `<path ${common} d="M192 74l-76 122h58l-22 90 92-132h-64z"/>`;
  if (type === "cable") return `<path ${common} d="M70 180c60-62 108 62 168 0 22-22 38-30 58-26"/><path ${common} d="M226 148l50 14-20 48"/>`;
  if (type === "beam") return `<path ${common} d="M82 112h196M82 248h196M122 112v136M238 112v136M122 180h116"/>`;
  if (type === "battery") return `<rect ${common} x="86" y="132" width="184" height="96" rx="16"/><path ${common} d="M270 164h22v32h-22M122 180h112"/>`;
  if (type === "screen") return `<rect ${common} x="78" y="96" width="204" height="132" rx="16"/><path ${common} d="M152 260h56M180 228v32"/>`;
  if (type === "probe") return `<path ${common} d="M88 132h184v92H88zM118 224v46M154 224v46M190 224v46M226 224v46M130 164h100"/>`;
  return `<rect ${common} x="92" y="98" width="176" height="154" rx="18"/><path ${common} d="M128 150h104M128 192h72"/>`;
}

function makeSvg(label, accentA, accentB, shape) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#07111f"/>
      <stop offset=".55" stop-color="#111827"/>
      <stop offset="1" stop-color="#171022"/>
    </linearGradient>
    <radialGradient id="glow" cx=".72" cy=".28" r=".55">
      <stop offset="0" stop-color="${accentA}" stop-opacity=".55"/>
      <stop offset=".35" stop-color="${accentB}" stop-opacity=".20"/>
      <stop offset="1" stop-color="#000" stop-opacity="0"/>
    </radialGradient>
    <filter id="blur"><feGaussianBlur stdDeviation="9"/></filter>
  </defs>
  <rect width="640" height="360" fill="url(#bg)"/>
  <rect width="640" height="360" fill="url(#glow)"/>
  <g opacity=".16">
    <circle cx="88" cy="72" r="2" fill="#fff"/><circle cx="540" cy="94" r="1.5" fill="#fff"/>
    <circle cx="502" cy="286" r="2" fill="#fff"/><circle cx="172" cy="284" r="1.5" fill="#fff"/>
  </g>
  <ellipse cx="410" cy="178" rx="166" ry="70" fill="none" stroke="${accentA}" stroke-opacity=".22" stroke-width="3"/>
  <g transform="translate(140 0)" filter="url(#blur)" opacity=".7">
    <circle cx="210" cy="160" r="54" fill="${accentA}"/>
  </g>
  <g transform="translate(140 0)">${svgShape(shape)}</g>
  <rect x="34" y="284" width="210" height="48" rx="24" fill="rgba(0,0,0,.46)" stroke="rgba(255,255,255,.16)"/>
  <text x="58" y="315" font-family="Arial, sans-serif" font-size="24" font-weight="800" fill="#fff">${label}</text>
</svg>
`;
}

function ensureVisuals() {
  fs.mkdirSync(IMAGE_DIR, { recursive: true });
  for (const [file, _source, label, a, b, shape] of Object.values(LOCAL_VISUALS)) {
    const full = path.join(IMAGE_DIR, file);
    if (!fs.existsSync(full)) fs.writeFileSync(full, makeSvg(label, a, b, shape), "utf8");
  }
}

function visualByKey(key) {
  const item = LOCAL_VISUALS[key] || LOCAL_VISUALS.default_a;
  return [IMG + item[0], item[1]];
}

function imageForCard(card, payload, index) {
  const source = `${card.title || ""} ${card.caption || ""} ${card.visual || ""} ${payload.sector || ""} ${payload.display_category || ""}`;
  if (hasAny(source, ["SiC-Parts", "실리콘카바이드", "SiC Ring", "SiC Tube", "SiC"])) return visualByKey("sic_part");
  if (hasAny(source, ["Si-Parts", "실리콘부품", "실리콘 Parts"])) return visualByKey("silicon_part");
  if (hasAny(source, ["Electrode", "Ring", "공정소모품", "식각"])) return visualByKey("electrode_ring");
  if (hasAny(source, ["패키징", "PKG", "OSAT", "반도체칩부품화"])) return visualByKey("semiconductor_pkg");
  if (hasAny(source, ["Probe", "Contact", "Interposer", "검사부품", "검사장치", "테스트"])) return visualByKey("probe");
  if (hasAny(source, ["MLCC", "콘덴서", "수정진동자", "Crystal", "SMD", "전자부품"])) return visualByKey("electronic_part");
  if (hasAny(source, ["바이오·FNT", "아미노산", "조미소재", "발효", "바이오 소재"])) return visualByKey("pharma");
  if (hasAny(source, ["면제품", "라면", "당면", "국수", "면류"])) return visualByKey("food_noodle");
  if (hasAny(source, ["양념", "소스", "카레", "케찹", "케첩", "마요네즈"])) return visualByKey("food_sauce");
  if (hasAny(source, ["농수산", "참치", "가공식품", "간편식", "HMR", "만두", "김치", "햇반", "식품사업", "식음료", "푸드", "스타벅스", "외식"])) return visualByKey("food_packaged");
  if (hasAny(source, ["소재식품", "설탕", "밀가루", "식용유", "원당", "전분", "전분당"])) return visualByKey("food_ingredient");
  if (hasAny(source, ["사료", "양돈", "양계", "축우", "배합사료"])) return visualByKey("food_feed");
  for (const [words, file, imageSource] of REAL_ASSETS) {
    if (hasAny(source, words)) return [IMG + file, imageSource];
  }

  if (hasAny(source, ["맥주", "소주", "테라", "켈리", "필라이트", "하이트", "주류", "음료"])) return visualByKey("alcohol");
  if (hasAny(source, ["합판", "파티클보드", "PB", "우드칩", "목재", "포르마린"])) return visualByKey("wood");
  if (hasAny(source, ["사류", "면사", "직물", "포류", "섬유", "원단", "니트", "방적"])) return visualByKey("textile");
  if (hasAny(source, ["의류", "란제리", "스타킹", "비너스", "와코루", "수영복", "패션", "침구"])) return visualByKey("fashion");
  if (hasAny(source, ["건축", "토목", "도급공사", "분양", "건설", "공사", "주택", "Haustory"])) return visualByKey(hasAny(source, ["분양", "주택"]) ? "housing" : "construction");
  if (hasAny(source, ["골판지", "포장", "상자", "원지", "패키지"])) return visualByKey("packaging");
  if (hasAny(source, ["시멘트", "레미콘", "콘크리트", "PHC", "PILE", "골재", "PC"])) return visualByKey("cement");
  if (hasAny(source, ["타이어", "N'FERA", "N'blue", "N'priz", "WINGUARD"])) return visualByKey("tire");
  if (hasAny(source, ["피아노", "악기", "어쿠스틱기타"])) return visualByKey("instrument");
  if (hasAny(source, ["수정진동자", "Crystal", "SMD"])) return visualByKey("crystal");
  if (hasAny(source, ["데이터센터"])) return visualByKey("datacenter");
  if (hasAny(source, ["클라우드"])) return visualByKey("cloud");
  if (hasAny(source, ["전장부품", "자동차부품", "파워트레인", "다이캐스팅", "블랙박스", "차량기기", "레이더디텍터"])) return visualByKey("auto_part");
  if (hasAny(source, ["네트워크", "광케이블", "광섬유", "무선랜", "통신"])) return visualByKey("network");
  if (hasAny(source, ["LM가이드", "볼나사", "베어링", "기계", "장비", "금형"])) return visualByKey("machinery");
  if (hasAny(source, ["윤활유", "고무배합유", "전기절연유", "유동파라핀", "유류", "LPG", "정유", "석유"])) return visualByKey("oil");
  if (hasAny(source, ["고무", "라텍스"])) return visualByKey("rubber");
  if (hasAny(source, ["사료", "양돈", "양계", "축우", "배합사료"])) return visualByKey("feed");
  if (hasAny(source, ["농약", "살균", "살충", "유액제", "수화제", "입제", "분제"])) return visualByKey("agro");
  if (hasAny(source, ["MRO", "구매대행", "엠알오"])) return visualByKey("mro");
  if (hasAny(source, ["의약", "제약", "치료제", "원료의약품", "API", "백신", "CDMO"])) return visualByKey("pharma");
  if (hasAny(source, ["화장품", "코스메틱"])) return visualByKey("cosmetics");
  if (hasAny(source, ["학원", "교육", "고시", "공무원시험"])) return visualByKey("education");
  if (hasAny(source, ["콘텐츠", "드라마", "OTT", "미디어", "광고", "게임"])) return visualByKey("content");
  if (hasAny(source, ["로봇"])) return visualByKey("robot");
  if (hasAny(source, ["AI", "인공지능", "MLOPS"])) return visualByKey("ai");
  if (hasAny(source, ["헬스케어", "의료 데이터", "병원", "모바일 헬스"])) return visualByKey("healthcare");
  if (hasAny(source, ["의료기기", "의료 장비", "정밀 장비"])) return visualByKey("medical_device");
  if (hasAny(source, ["소방", "안전", "DI-KIT"])) return visualByKey("safety");
  if (hasAny(source, ["소프트웨어", "솔루션", "SI", "시스템 구축", "시스템 유지보수", "IT 인프라", "VAN", "플랫폼 서비스"])) return visualByKey("software");
  if (hasAny(source, ["FM", "PM", "시설관리", "자산관리", "건물관리"])) return visualByKey("fm");
  if (hasAny(source, ["보안", "시큐리티", "경비", "출동"])) return visualByKey("security");
  if (hasAny(source, ["할인점", "마트", "트레이더스", "소매", "유통"])) return visualByKey("retail");
  if (hasAny(source, ["백화점"])) return visualByKey("department");
  if (hasAny(source, ["편의점"])) return visualByKey("convenience");
  if (hasAny(source, ["물류", "운송", "배송", "택배", "창고"])) return visualByKey("logistics");
  if (hasAny(source, ["지주", "자회사", "투자부문", "배당"])) return visualByKey("finance_hold");
  if (hasAny(source, ["은행", "대출", "예금"])) return visualByKey("bank");
  if (hasAny(source, ["카드", "결제"])) return visualByKey("card");
  if (hasAny(source, ["증권", "브로커리지", "운용", "자산관리"])) return visualByKey("securities");
  if (hasAny(source, ["보험", "손해율", "보험료"])) return visualByKey("insurance");
  if (hasAny(source, ["선박", "조선", "LNG", "상선"])) return visualByKey("ship");
  if (hasAny(source, ["해양", "플랜트", "Offshore"])) return visualByKey("offshore");
  if (hasAny(source, ["전력", "발전", "송전"])) return visualByKey("power");
  if (hasAny(source, ["전선", "케이블", "OPGW"])) return visualByKey("cable");
  if (hasAny(source, ["철강", "금속", "강관", "알루미늄", "구리", "비철"])) return visualByKey("steel");
  if (hasAny(source, ["화학", "소재", "수지", "필름", "도료", "탄소", "첨단소재"])) return visualByKey("chemical");
  if (hasAny(source, ["배터리", "2차전지", "양극재", "음극재", "전해액"])) return visualByKey("battery");
  if (hasAny(source, ["반도체", "Si-Parts", "SiC-Parts", "실리콘", "공정소모품", "패키징", "테스트", "PCB", "BGA", "MLCC", "콘덴서"])) return visualByKey("semiconductor_part");

  const fallbackKeys = ["default_a", "default_b", "default_c", "default_d"];
  return visualByKey(fallbackKeys[index % fallbackKeys.length]);
}

function needsImageRepair(cards) {
  const images = cards.map((card) => clean(card.image)).filter(Boolean);
  if (!images.length) return true;
  if (images.some((image) => BAD_DUPES.has(image))) return true;
  return cards.length >= 3 && new Set(images).size === 1;
}

ensureVisuals();

let scanned = 0;
let repaired = 0;
for (const file of fs.readdirSync(DATA_DIR).filter((name) => /^business_\d{6}\.json$/.test(name)).sort()) {
  const full = path.join(DATA_DIR, file);
  const payload = JSON.parse(fs.readFileSync(full, "utf8"));
  const cards = Array.isArray(payload.business_cards) ? payload.business_cards : [];
  scanned += 1;
  if (!cards.length) continue;
  const before = JSON.stringify(cards.map((card) => [card.title, card.image]));
  payload.business_cards = cards.map((card, index) => {
    const [image, image_source] = imageForCard(card, payload, index);
    return { ...card, image, image_source };
  });
  const after = JSON.stringify(payload.business_cards.map((card) => [card.title, card.image]));
  if (after !== before) {
    fs.writeFileSync(full, JSON.stringify(payload, null, 2), "utf8");
    repaired += 1;
  }
}

console.log(JSON.stringify({ scanned, repaired }, null, 2));
