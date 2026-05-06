"""extract_v2_assets.py — DiscloseAI v2 standalone HTML 1회용 디코더.

목적: v2 standalone에서 **CSS와 assets만** 추출한다. JSX 본체는 추출하지 않음
(우리 데이터 모델에 맞춰 새로 작성하기 때문).

원본 디코드 로직 (standalone-original.html L48-170)을 Python으로 재현:
  1. <script type="__bundler/manifest"> JSON
     → {uuid: {data: base64, compressed: bool, mime: ...}}
  2. <script type="__bundler/ext_resources"> JSON
     → [{uuid, id}, ...] 매핑 (id가 있으면 fname으로 사용)
  3. 각 entry: base64 decode + (compressed면 gzip.decompress)
  4. MIME에 따라 분류:
     - text/css           → styles.css에 합산
     - font/* image/*     → assets/<fname>.<ext>로 저장
     - 그 외              → assets/ 기타 (드뭄)
  5. <style> 인라인 블록도 styles.css 앞에 합산
  6. CSS 텍스트 안의 UUID 참조를 정적 경로 ./assets/<fname>로 치환

입력: ./standalone-original.html (이 스크립트와 같은 폴더)
출력:
  ../styles.css            인라인 <style> + asset CSS 합산
  ../assets/<fname>.<ext>  폰트·이미지 등 바이너리 자산

사용:
    cd modules/integration/v2/_decode
    python extract_v2_assets.py

이 스크립트는 read-only로 standalone-original.html만 읽고
v2/styles.css·v2/assets/만 쓴다 (dashboard.html과 무관).
"""

from __future__ import annotations

import base64
import gzip
import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
ROOT = Path(__file__).parent.parent  # modules/integration/v2/
SRC = Path(__file__).parent / "standalone-original.html"
ASSETS_DIR = ROOT / "assets"
STYLES_OUT = ROOT / "styles.css"

# MIME → 확장자
MIME_EXT = {
    "text/css": "css",
    "image/svg+xml": "svg",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "font/woff2": "woff2",
    "font/woff": "woff",
    "font/ttf": "ttf",
    "application/font-woff2": "woff2",
    "application/font-woff": "woff",
    "application/javascript": "js",
    "text/javascript": "js",
    "application/json": "json",
    "text/plain": "txt",
}

UUID_RE = re.compile(
    r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
)


def slugify(s: str, ext: str) -> str:
    """ext_resources의 id를 안전한 파일명으로."""
    base = s.split("/")[-1]
    base = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    if not base.endswith("." + ext):
        base = f"{base}.{ext}"
    return base


def main() -> int:
    if not SRC.exists():
        print(f"[ERR] source not found: {SRC}", file=sys.stderr)
        return 1

    html = SRC.read_text(encoding="utf-8")
    print(f"[INFO] source: {SRC} ({SRC.stat().st_size:,} bytes)")

    # 1. <style>...</style> 인라인 블록 모두 추출
    style_blocks = re.findall(
        r"<style[^>]*>(.*?)</style>",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    inline_css = "\n\n".join(b for b in style_blocks if b.strip())
    print(f"[INFO] inline <style> blocks: {len(style_blocks)} ({len(inline_css):,} chars)")

    # 2. manifest 파싱
    m = re.search(
        r'<script\s+type="__bundler/manifest">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    if not m:
        print("[ERR] manifest script tag not found", file=sys.stderr)
        return 2
    manifest = json.loads(m.group(1))
    print(f"[INFO] manifest entries: {len(manifest)}")

    # 3. ext_resources (선택)
    me = re.search(
        r'<script\s+type="__bundler/ext_resources">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    ext_resources = json.loads(me.group(1)) if me else []
    uuid_to_id = {e["uuid"]: e.get("id", "") for e in ext_resources}
    print(f"[INFO] ext_resources mappings: {len(uuid_to_id)}")

    # 4. assets 디코드 + 분류
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    raw_js_dir = Path(__file__).parent / "raw_js"
    raw_js_dir.mkdir(exist_ok=True)
    uuid_to_fname: dict[str, str] = {}  # CSS url 치환용
    css_assets: list[tuple[str, str]] = []  # (fname, css_text)
    saved = {"css": 0, "font": 0, "image": 0, "other": 0, "js": 0}

    for uuid, entry in manifest.items():
        data_b64 = entry.get("data", "")
        mime = entry.get("mime", "application/octet-stream")
        compressed = bool(entry.get("compressed", False))

        try:
            raw = base64.b64decode(data_b64)
            if compressed:
                raw = gzip.decompress(raw)
        except Exception as exc:
            print(f"[WARN] decode failed {uuid[:8]}: {exc}", file=sys.stderr)
            continue

        ext = MIME_EXT.get(mime, "bin")
        ident = uuid_to_id.get(uuid)
        fname = slugify(ident, ext) if ident else f"{uuid[:8]}.{ext}"
        uuid_to_fname[uuid] = fname

        # JS는 `_decode/raw_js/`에 보관 (참조용, 우리는 새로 작성하지만
        # CSS-in-JS 패턴이나 mock 데이터 추출에 도움이 됨)
        if mime in ("application/javascript", "text/javascript"):
            (raw_js_dir / fname).write_bytes(raw)
            saved["js"] += 1
            continue

        if mime == "text/css":
            css_assets.append((fname, raw.decode("utf-8", errors="replace")))
            saved["css"] += 1
        elif mime.startswith("font/") or mime.startswith("application/font-"):
            (ASSETS_DIR / fname).write_bytes(raw)
            saved["font"] += 1
        elif mime.startswith("image/"):
            (ASSETS_DIR / fname).write_bytes(raw)
            saved["image"] += 1
        else:
            (ASSETS_DIR / fname).write_bytes(raw)
            saved["other"] += 1

    print(
        f"[INFO] saved: css={saved['css']} font={saved['font']} "
        f"image={saved['image']} other={saved['other']} js={saved['js']}"
    )

    # 5. CSS 텍스트의 UUID → 정적 경로 치환
    def patch(text: str) -> str:
        def replace(m: re.Match) -> str:
            uuid = m.group(0)
            fname = uuid_to_fname.get(uuid.lower()) or uuid_to_fname.get(uuid)
            return f"./assets/{fname}" if fname else uuid
        return UUID_RE.sub(replace, text)

    inline_css_p = patch(inline_css)
    css_assets_p = [(n, patch(t)) for n, t in css_assets]

    # 6. styles.css 작성
    sections = []
    if inline_css_p.strip():
        sections.append("/* ===========================================================\n"
                        " * v2 standalone <style> blocks (inline)\n"
                        " * =========================================================== */\n"
                        + inline_css_p)
    for fname, text in css_assets_p:
        sections.append(f"/* ===========================================================\n"
                        f" * asset: {fname}\n"
                        f" * =========================================================== */\n"
                        + text)
    final_css = "\n\n".join(sections) + "\n"
    STYLES_OUT.write_text(final_css, encoding="utf-8")

    print(f"[INFO] styles.css   : {STYLES_OUT.stat().st_size:>10,} bytes")
    asset_files = list(ASSETS_DIR.iterdir())
    print(f"[INFO] assets/      : {len(asset_files):>10,} files")

    # 7. 디버깅 보조 — uuid_to_fname 매핑을 manifest.json으로 보관
    map_out = Path(__file__).parent / "_uuid_map.json"
    map_out.write_text(
        json.dumps(uuid_to_fname, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[INFO] uuid map     : {map_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
