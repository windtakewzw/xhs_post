"""Seedream API image generator for xiaohongshu posts.

Strategy: search project materials/ for matching reference images first (img2img),
fall back to text2img when no suitable reference exists.

Image indexing: each materials/ subdirectory may contain an index.md describing
images for semantic matching. Format:

    ---
    directory: media/photos/interior
    ---
    | 文件 | 描述 | 标签 | 适用 |
    |------|------|------|------|
    | img01.jpg | 客厅全景，落地窗采光好 | 客厅, 采光 | living_room, light |

Fields: 文件=filename, 描述=description, 标签=tags, 适用=img_types
"""
import argparse
import base64
import os
import random
import re
import sys
import requests

API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
SIZE = "2304x4096"
NEGATIVE_PROMPT = (
    "text overlay, watermarks, QR codes, phone numbers, logos, "
    "distorted architecture, unrealistic proportions, blurry, low quality, "
    "cartoon, illustration, 3D render style, overly saturated"
)

VISUAL_STYLES = {
    "investment-advisor": {"colors": "cool tones, navy, silver, white, blue-gray",
        "lighting": "bright, clean, professional", "atmosphere": "confident, authoritative"},
    "lifestyle-advisor": {"colors": "warm tones, beige, wood, gold, sage green",
        "lighting": "soft natural light, golden hour", "atmosphere": "warm, inviting, serene"},
    "family-advisor": {"colors": "neutral tones, warm gray, light blue, soft green",
        "lighting": "diffused natural light", "atmosphere": "cozy, safe, practical"},
}

# Image count + sequence per content type
IMAGE_CONFIGS = {
    "market-analysis": (5, ["cover", "chart", "project", "cta"]),
    "area-value": (6, ["cover", "planning", "amenity", "location", "info", "cta"]),
    "product-analysis": (6, ["cover", "living_room", "bedroom", "balcony", "floorplan", "cta"]),
    "buying-guide": (5, ["cover", "tip_card", "tip_card", "project", "cta"]),
    "community-life": (7, ["cover", "landscape", "pool", "detail", "detail", "detail", "cta"]),
    "home-aesthetics": (7, ["cover", "light", "material", "panorama", "inspo", "inspo", "cta"]),
    "family-living": (7, ["cover", "living", "kids_room", "kitchen", "education", "detail", "cta"]),
    "trend-jacking": (5, ["cover", "trend", "project", "project", "cta"]),
}

# img_type → materials/ subdirectories to search, ordered by relevance
IMAGE_SEARCH_MAP = {
    "project":       ["media/photos/exterior", "真实素材库/实拍照片/外立面实景",
                      "media/renders", "真实素材库/官方效果图"],
    "living_room":   ["media/photos/interior", "真实素材库/实拍照片/室内实景"],
    "bedroom":       ["media/photos/interior", "真实素材库/实拍照片/室内实景"],
    "balcony":       ["media/photos/exterior", "真实素材库/实拍照片/外立面实景",
                      "media/photos/landscape", "真实素材库/实拍照片/园林实景"],
    "floorplan":     ["media/renders", "真实素材库/官方效果图"],
    "landscape":     ["media/photos/landscape", "真实素材库/实拍照片/园林实景"],
    "pool":          ["media/photos/landscape", "真实素材库/实拍照片/园林实景",
                      "media/photos/amenities", "真实素材库/实拍照片/配套设施"],
    "detail":        ["media/photos/landscape", "真实素材库/实拍照片/园林实景",
                      "media/photos/exterior", "真实素材库/实拍照片/外立面实景",
                      "media/photos/amenities", "真实素材库/实拍照片/配套设施"],
    "light":         ["media/photos/interior", "真实素材库/实拍照片/室内实景"],
    "material":      ["media/photos/interior", "真实素材库/实拍照片/室内实景",
                      "media/photos/exterior", "真实素材库/实拍照片/外立面实景"],
    "panorama":      ["media/photos/landscape", "真实素材库/实拍照片/园林实景",
                      "media/photos/exterior", "真实素材库/实拍照片/外立面实景"],
    "inspo":         ["media/photos/interior", "真实素材库/实拍照片/室内实景"],
    "living":        ["media/photos/interior", "真实素材库/实拍照片/室内实景"],
    "kids_room":     ["media/photos/interior", "真实素材库/实拍照片/室内实景"],
    "kitchen":       ["media/photos/interior", "真实素材库/实拍照片/室内实景"],
    "education":     ["media/photos/amenities", "真实素材库/实拍照片/配套设施"],
    "amenity":       ["media/photos/amenities", "真实素材库/实拍照片/配套设施"],
    "location":      ["media/photos/location", "真实素材库/实拍照片/区位环境"],
    "planning":      ["media/renders", "真实素材库/官方效果图",
                      "media/photos/exterior", "真实素材库/实拍照片/外立面实景"],
    "trend":         ["media/photos/exterior", "真实素材库/实拍照片/外立面实景",
                      "media/photos/landscape", "真实素材库/实拍照片/园林实景"],
    "chart":         [],
    "info":          [],
    "tip_card":      [],
    "cover":         [],
    "cta":           [],
}

# Design-only types: always text2img, never search for references
TEXT2IMG_ONLY = {"cover", "cta", "chart", "info", "tip_card"}

# Keywords per img_type for scoring filename relevance
IMG_TYPE_KEYWORDS = {
    "project":      ["外立面", "外观", "建筑", "exterior", "效果图"],
    "living_room":  ["客厅", "起居室", "living", "样板间"],
    "bedroom":      ["主卧", "卧室", "bedroom", "样板间"],
    "balcony":      ["阳台", "露台", "景观", "园林", "室外"],
    "floorplan":    ["户型", "平面", "户型图", "floorplan"],
    "landscape":    ["园林", "景观", "花园", "绿化", "landscape"],
    "pool":         ["泳池", "海", "水景", "海滩", "码头", "pool"],
    "detail":       ["细节", "特写", "园林", "景观", "泳池", "会所", "配套"],
    "light":        ["采光", "光线", "阳光", "窗户", "阳台"],
    "material":     ["材质", "石材", "木", "细节", "外立面", "厨房"],
    "panorama":     ["全景", "鸟瞰", "航拍", "景观", "园林"],
    "inspo":        ["软装", "家具", "装饰", "风格", "样板间", "客厅", "卧室"],
    "living":       ["客厅", "家庭", "起居室", "living", "样板间"],
    "kids_room":    ["儿童", "小孩", "儿童房", "kids"],
    "kitchen":      ["厨房", "餐厅", "kitchen", "样板间"],
    "education":    ["学校", "教育", "配套", "学区"],
    "amenity":      ["配套", "会所", "泳池", "公园", "学校", "码头", "商业"],
    "location":     ["区位", "地图", "周边", "交通", "配套"],
    "planning":     ["规划", "鸟瞰", "总平", "区位", "效果图", "区域"],
    "trend":        ["热点", "趋势", "政策", "规划"],
}


def _img_ext(path):
    return os.path.splitext(path)[1].lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def parse_image_index(index_path):
    """Parse a materials/ subdirectory index.md into a dict keyed by filename.

    Returns dict: {filename: {"desc": str, "tags": [str], "types": [str]}}
    Returns empty dict if index.md doesn't exist or can't be parsed.
    """
    if not os.path.isfile(index_path):
        return {}

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return {}

    entries = {}
    # Match markdown table rows: | filename | desc | tags | types |
    table_pattern = re.compile(
        r'^\|?\s*([^|\n]+?)\s*\|\s*([^|\n]*?)\s*\|\s*([^|\n]*?)\s*\|\s*([^|\n]*?)\s*\|?\s*$',
        re.MULTILINE
    )

    for match in table_pattern.finditer(content):
        fname = match.group(1).strip()
        desc = match.group(2).strip()
        tags = [t.strip() for t in match.group(3).split(",") if t.strip()]
        types = [t.strip() for t in match.group(4).split(",") if t.strip()]

        # Skip header rows
        if fname in ("文件", "File", "文件名") or not _img_ext(fname):
            continue

        entries[fname] = {"desc": desc, "tags": tags, "types": types}

    return entries


def _score_path(filepath, img_type, title, index_entries=None):
    """Score a candidate image for relevance. Higher = better match.

    If index_entries is provided, prefer index-based scoring over filename heuristics.
    """
    basename = os.path.basename(filepath)
    dirname = os.path.dirname(filepath).lower()
    score = 0.0

    entry = None
    if index_entries is not None:
        entry = index_entries.get(basename)
        # Also try with stripped suffixes like " (1)", " (2)"
        if entry is None:
            name_no_ext = os.path.splitext(basename)[0]
            for key, val in index_entries.items():
                key_no_ext = os.path.splitext(key)[0]
                if key_no_ext == name_no_ext or key_no_ext.startswith(name_no_ext) or name_no_ext.startswith(key_no_ext):
                    entry = val
                    break

    if entry:
        # Index-based scoring
        if img_type in entry.get("types", []):
            score += 10  # strong match: explicitly listed as suitable
        tags = entry.get("tags", [])
        desc = entry.get("desc", "")
        keywords = IMG_TYPE_KEYWORDS.get(img_type, [])
        for kw in keywords:
            for tag in tags:
                if kw in tag:
                    score += 3
            if kw in desc:
                score += 2
        # Title overlap with description
        title_words = set(title[:30])
        desc_words = set(desc)
        overlap = len(title_words & desc_words)
        score += overlap * 0.5
    else:
        # Fallback: filename-based scoring
        basename_lower = basename.lower()
        keywords = IMG_TYPE_KEYWORDS.get(img_type, [])
        for kw in keywords:
            if kw.lower() in basename_lower:
                score += 3
            if kw.lower() in dirname:
                score += 1
        title_chars = set(title[:20])
        if title_chars:
            basename_chars = set(basename_lower)
            score += len(title_chars & basename_chars) * 0.5

    # Prefer real photos over renders for most types
    if "renders" in dirname or "效果图" in dirname:
        if img_type not in {"floorplan", "planning"}:
            score -= 2

    # Small random jitter for diversity
    score += random.uniform(-0.3, 0.3)

    return score


def find_reference(project_dir, img_type, title, used_paths):
    """Search materials/ for a matching reference image.

    Prefers index.md metadata when available; falls back to filename heuristics.
    Returns (filepath, compliance_label) or (None, fallback_label).
    """
    if img_type in TEXT2IMG_ONLY or not IMAGE_SEARCH_MAP.get(img_type):
        return None, None

    candidates = []
    search_dirs = IMAGE_SEARCH_MAP.get(img_type, [])

    for rel_dir in search_dirs:
        full_dir = os.path.join(project_dir, rel_dir)
        if not os.path.isdir(full_dir):
            continue

        # Load index.md if present
        index_path = os.path.join(full_dir, "index.md")
        index_entries = parse_image_index(index_path) if os.path.isfile(index_path) else None

        for root, _dirs, files in os.walk(full_dir):
            for fname in files:
                if not _img_ext(fname):
                    continue
                fpath = os.path.join(root, fname)
                if fpath in used_paths:
                    continue
                # Resolve index entry relative to the search dir root
                score = _score_path(fpath, img_type, title, index_entries)
                candidates.append((score, fpath))

    if not candidates:
        return None, "概念示意图，以实际为准"

    candidates.sort(key=lambda x: x[0], reverse=True)

    # Pick the best, occasionally pick #2 for variety (30% chance if >1 candidate)
    if len(candidates) > 1 and random.random() < 0.3:
        _, path = candidates[1]
    else:
        _, path = candidates[0]

    # Determine compliance label
    d = os.path.dirname(path).lower()
    if "renders" in d or "效果图" in d:
        label = "效果图仅供参考"
    else:
        label = None

    return path, label


def img2img_prompt(img_type, title, style):
    """Build prompt for img2img mode — enhances the reference photo."""
    return (
        f"Professional real estate photography, {img_type} shot for Xiaohongshu. "
        f"Enhance lighting and composition while preserving architectural accuracy. "
        f"Color palette: {style['colors']}. Lighting: {style['lighting']}. "
        f"Atmosphere: {style['atmosphere']}. "
        f"Clean modern look, vertical 9:16 format, no QR code, no watermarks."
    )


def text2img_prompt(img_type, title, style):
    """Build prompt for text2img mode — generates from scratch."""
    type_descriptions = {
        "cover": f"eye-catching title card with real estate theme. Large Chinese title '{title}' prominently placed",
        "chart": "data visualization with clean charts and key metrics about real estate",
        "project": "premium real estate exterior photography",
        "living_room": "luxurious living room with natural light, modern furniture",
        "bedroom": "spacious master bedroom with premium finishes",
        "balcony": "wide balcony with panoramic views",
        "floorplan": "clean architectural floorplan layout",
        "landscape": "beautiful landscaped garden with greenery and water features",
        "pool": "luxury swimming pool in resort-style setting",
        "detail": "architectural detail close-up shot",
        "light": "interior shot emphasizing natural light and shadows",
        "material": "close-up of premium materials and textures in interior design",
        "panorama": "wide panoramic view from high vantage point",
        "inspo": "interior design inspiration photo with beautiful decor",
        "living": "warm family living room with comfortable seating",
        "kids_room": "bright and cheerful children's bedroom design",
        "kitchen": "modern open kitchen with premium appliances",
        "education": "nearby school and education facilities",
        "amenity": "community amenities and facilities",
        "location": "location map and surrounding area highlights",
        "planning": "master planning layout with building arrangement",
        "trend": "trending topic visual with real estate context",
        "info": "information card with key facts, clean typography",
        "tip_card": "tips card with bullet points, modern design",
        "cta": "call-to-action design with subtle branding",
    }
    desc = type_descriptions.get(img_type, "real estate photography")
    return (
        f"A real estate social media {img_type} image for Xiaohongshu. "
        f"The {img_type} features {desc}. "
        f'Large Chinese title text "{title[:30]}" prominently placed, modern typography. '
        f"Color palette: {style['colors']}. Lighting: {style['lighting']}. "
        f"Atmosphere: {style['atmosphere']}. "
        f"Clean modern design, vertical 9:16 format, no QR code, no watermarks, "
        f"professional real estate photography style."
    )


def call_api(api_key, model, payload):
    resp = requests.post(API_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload, timeout=120)
    return resp.json()


def generate(args):
    api_key = args.api_key or os.environ.get("SEEDREAM_API_KEY", "")
    if not api_key:
        print("Error: SEEDREAM_API_KEY not set")
        sys.exit(1)

    style = VISUAL_STYLES.get(args.persona_type, VISUAL_STYLES["lifestyle-advisor"])
    count, sequence = IMAGE_CONFIGS.get(args.content_type, (5, ["cover", "content", "content", "cta"]))
    os.makedirs(args.output_dir, exist_ok=True)

    used_paths = set()
    for i, img_type in enumerate(sequence[:count], 1):
        is_t2i_only = img_type in TEXT2IMG_ONLY

        if is_t2i_only:
            # Cover, CTA, data cards: always text2img
            mode, ref_path, label = "text2img", None, None
        else:
            ref_path, label = find_reference(args.project_dir, img_type, args.title, used_paths)
            mode = "img2img" if ref_path else "text2img"

        if mode == "img2img":
            prompt = img2img_prompt(img_type, args.title, style)
            used_paths.add(ref_path)
        else:
            prompt = text2img_prompt(img_type, args.title, style)

        payload = {
            "model": args.model, "prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "size": SIZE, "seed": -1, "scale": 7.5, "ddim_steps": 30,
        }

        if mode == "img2img" and ref_path:
            with open(ref_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(ref_path)[1].lower().replace("jpeg", "jpg")
            payload["init_image"] = f"data:image/{ext.replace('.', '')};base64,{img_b64}"
            payload["strength"] = 0.35

        data = call_api(api_key, args.model, payload)

        if data.get("code") != 0:
            print(f"  Error on image {i}: {data}")
            continue

        url = data["data"]["image_urls"][0]
        img_data = requests.get(url, timeout=60).content
        path = os.path.join(args.output_dir, f"image-{i:02d}.jpg")
        with open(path, "wb") as f:
            f.write(img_data)

        source = f"ref:{os.path.basename(ref_path)}" if ref_path else "t2i"
        label_str = f" [标注: {label}]" if label else ""
        print(f"  image-{i:02d}.jpg ({img_type} | {source}){label_str}")


def main():
    p = argparse.ArgumentParser(description="Seedream image generator")
    p.add_argument("--content-type", required=True)
    p.add_argument("--persona-type", required=True)
    p.add_argument("--project-dir", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--model", default="seedream-5.0-lite")
    p.add_argument("--api-key", default=None)
    generate(p.parse_args())


if __name__ == "__main__":
    main()
