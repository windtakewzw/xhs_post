"""Seedream API image generator for xiaohongshu posts."""
import argparse
import os
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

VISUAL_ELEMENTS = {
    "cover": "eye-catching title card with real estate theme",
    "chart": "data visualization with clean charts",
    "project": "premium real estate exterior photography",
    "cta": "call-to-action design with subtle branding",
}


def decide_mode(project_dir: str, is_cover: bool) -> tuple:
    """Returns (mode, strength, compliance_label)."""
    if is_cover:
        return ("text2img", None, None)
    photos = os.path.isdir(os.path.join(project_dir, "media", "photos"))
    renders = os.path.isdir(os.path.join(project_dir, "media", "renders"))
    if photos:
        return ("img2img", 0.35, None)
    if renders:
        return ("img2img", 0.45, "效果图仅供参考")
    return ("text2img", None, "概念示意图，以实际为准")


def build_prompt(img_type: str, title: str, style: dict) -> str:
    elements = VISUAL_ELEMENTS.get(img_type, "real estate photography")
    return (
        f"A real estate social media {img_type} image for Xiaohongshu. "
        f"The {img_type} features {elements}. "
        f'Large Chinese title text "{title}" prominently placed, modern typography. '
        f"Color palette: {style['colors']}. Lighting: {style['lighting']}. "
        f"Atmosphere: {style['atmosphere']}. "
        f"Clean modern design, vertical 9:16 format, no QR code, no watermarks, "
        f"professional real estate photography style."
    )


def generate(args):
    api_key = args.api_key or os.environ.get("SEEDREAM_API_KEY", "")
    if not api_key:
        print("Error: SEEDREAM_API_KEY not set")
        sys.exit(1)

    style = VISUAL_STYLES.get(args.persona_type, VISUAL_STYLES["lifestyle-advisor"])
    count, sequence = IMAGE_CONFIGS.get(args.content_type, (5, ["cover", "content", "content", "cta"]))
    os.makedirs(args.output_dir, exist_ok=True)

    for i, img_type in enumerate(sequence[:count], 1):
        is_cover = (img_type == "cover")
        mode, strength, label = decide_mode(args.project_dir, is_cover)
        prompt = build_prompt(img_type, args.title, style)

        payload = {
            "model": args.model, "prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "size": SIZE, "seed": -1, "scale": 7.5, "ddim_steps": 30,
        }
        if mode == "img2img" and strength is not None:
            payload["strength"] = strength

        resp = requests.post(API_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload, timeout=120)
        data = resp.json()

        if data.get("code") != 0:
            print(f"Error on image {i}: {data}")
            continue

        url = data["data"]["image_urls"][0]
        img_data = requests.get(url, timeout=60).content
        path = os.path.join(args.output_dir, f"image-{i:02d}.jpg")
        with open(path, "wb") as f:
            f.write(img_data)
        label_str = f" [标注: {label}]" if label else ""
        print(f"  image-{i:02d}.jpg ({img_type}){label_str}")


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
