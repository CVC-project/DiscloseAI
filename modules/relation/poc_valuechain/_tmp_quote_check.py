# -*- coding: utf-8 -*-
"""Deterministic quote verification for semiconductor value-chain extraction.

Checks every quote (produces / consumes / named_partners) against the source
filing text using whitespace-insensitive substring matching:
    norm = lambda t: re.sub(r'\\s+', '', t)
    passes iff norm(quote) in norm(file_text)
Files are read in text mode with universal newlines (CRLF -> LF).
"""
import json
import re
import sys

BASE = "c:/Users/yangw/AIportfolio/CVC-project/DiscloseAI/modules/relation/poc_valuechain/data/"
FILEMAP = {
    "삼성전자": "semi_005930_삼성전자.txt",
    "SK하이닉스": "semi_000660_SK하이닉스.txt",
    "동진쎄미켐": "semi_005290_동진쎄미켐.txt",
    "솔브레인": "semi_357780_솔브레인.txt",
    "원익IPS": "semi_240810_원익IPS.txt",
}

DATA = json.load(open(
    "c:/Users/yangw/AIportfolio/CVC-project/DiscloseAI/modules/relation/poc_valuechain/_tmp_extraction.json",
    encoding="utf-8"))

norm = lambda t: re.sub(r"\s+", "", t)

total = 0
passed = 0
failed = []  # (company, section, label, quote)

for comp in DATA["companies"]:
    name = comp["name"]
    with open(BASE + FILEMAP[name], encoding="utf-8") as f:
        text = norm(f.read())
    for section in ("produces", "consumes", "named_partners"):
        for entry in comp.get(section, []):
            label = entry.get("item") or entry.get("partner")
            q = entry["quote"]
            total += 1
            if norm(q) in text:
                passed += 1
            else:
                failed.append((name, section, label, q))

result = {
    "total": total,
    "passed": passed,
    "failed_quotes": [
        {"company": c, "section": s, "label": l, "quote": q}
        for c, s, l, q in failed
    ],
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0 if passed == total else 1)
