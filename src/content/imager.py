import os
import requests


class Imager:
    API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    SIZE = "2304x4096"
    NEGATIVE_PROMPT = (
        "text overlay, watermarks, QR codes, phone numbers, logos, "
        "distorted architecture, unrealistic proportions, blurry, low quality, "
        "cartoon, illustration, 3D render style, overly saturated"
    )

    VISUAL_STYLES = {
        "investment-advisor": {
            "colors": "cool tones, navy, silver, white, blue-gray",
            "lighting": "bright, clean, professional",
            "atmosphere": "confident, authoritative",
        },
        "lifestyle-advisor": {
            "colors": "warm tones, beige, wood, gold, sage green",
            "lighting": "soft natural light, golden hour",
            "atmosphere": "warm, inviting, serene",
        },
        "family-advisor": {
            "colors": "neutral tones, warm gray, light blue, soft green",
            "lighting": "diffused natural light",
            "atmosphere": "cozy, safe, practical",
        },
    }

    IMAGE_CONFIGS = {
        "market-analysis": {"content_type": "market-analysis", "image_count": 5,
            "sequence": ["cover", "chart", "project", "cta"]},
        "area-value": {"content_type": "area-value", "image_count": 6,
            "sequence": ["cover", "planning", "amenity", "location", "info", "cta"]},
        "product-analysis": {"content_type": "product-analysis", "image_count": 6,
            "sequence": ["cover", "living_room", "bedroom", "balcony", "floorplan", "cta"]},
        "buying-guide": {"content_type": "buying-guide", "image_count": 5,
            "sequence": ["cover", "tip_card", "tip_card", "project", "cta"]},
        "community-life": {"content_type": "community-life", "image_count": 7,
            "sequence": ["cover", "landscape", "pool", "detail", "detail", "detail", "cta"]},
        "home-aesthetics": {"content_type": "home-aesthetics", "image_count": 7,
            "sequence": ["cover", "light", "material", "panorama", "inspo", "inspo", "cta"]},
        "family-living": {"content_type": "family-living", "image_count": 7,
            "sequence": ["cover", "living", "kids_room", "kitchen", "education", "detail", "cta"]},
        "trend-jacking": {"content_type": "trend-jacking", "image_count": 5,
            "sequence": ["cover", "trend", "project", "project", "cta"]},
    }

    @staticmethod
    def decide_mode(has_photos: bool, has_renders: bool, is_cover: bool) -> tuple[str, float | None, str | None]:
        if is_cover:
            return ("text2img", None, None)
        if has_photos:
            return ("img2img", 0.35, None)
        if has_renders:
            return ("img2img", 0.45, "效果图仅供参考")
        return ("text2img", None, "概念示意图，以实际为准")

    @staticmethod
    def get_image_config(content_type: str) -> dict:
        return Imager.IMAGE_CONFIGS.get(content_type,
            {"content_type": content_type, "image_count": 5, "sequence": ["cover", "content", "content", "cta"]})

    @staticmethod
    def get_visual_style(persona_type: str) -> dict:
        return Imager.VISUAL_STYLES.get(persona_type, Imager.VISUAL_STYLES["lifestyle-advisor"])

    @staticmethod
    def build_text2img_prompt(image_type: str, title: str, visual_elements: str,
                               auxiliary_elements: str, persona_style: dict) -> str:
        return (
            f"A real estate social media {image_type} image for Xiaohongshu. "
            f"The {image_type} features {visual_elements}, with {auxiliary_elements}. "
            f'Large Chinese title text "{title}" prominently placed, modern typography. '
            f"Color palette: {persona_style['colors']}. "
            f"Lighting: {persona_style['lighting']}. "
            f"Atmosphere: {persona_style['atmosphere']}. "
            f"Clean modern design, vertical 9:16 format, "
            f"no QR code, no phone numbers, no watermarks, "
            f"professional real estate photography style."
        )

    @staticmethod
    def build_img2img_prompt(scene_type: str, keep_features: str, enhance_aspects: str,
                               persona_style: dict) -> str:
        return (
            f"Real estate property photo, {scene_type}. "
            f"Keep the original {keep_features}. "
            f"Enhance {enhance_aspects}. "
            f"Color tone: {persona_style['colors']}, {persona_style['lighting']}. "
            f"Maintain architectural accuracy, realistic style, no distortion, "
            f"professional real estate photography, vertical 9:16."
        )

    @staticmethod
    def get_compliance_label(mode: str, has_real_photos: bool) -> str | None:
        if mode == "text2img" and not has_real_photos:
            return "概念示意图，以实际为准"
        if mode == "img2img" and not has_real_photos:
            return "效果图仅供参考"
        return None

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.environ.get("SEEDREAM_API_KEY", "")
        self.model = model or "seedream-5.0-lite"

    def _check_photos(self, project_dir: str) -> bool:
        photos_dir = os.path.join(project_dir, "media", "photos")
        return os.path.isdir(photos_dir) and len(os.listdir(photos_dir)) > 0

    def _check_renders(self, project_dir: str) -> bool:
        renders_dir = os.path.join(project_dir, "media", "renders")
        return os.path.isdir(renders_dir) and len(os.listdir(renders_dir)) > 0

    def _visual_elements_for(self, img_type: str) -> str:
        elements = {
            "cover": "eye-catching title card with real estate theme",
            "chart": "data visualization with clean charts",
            "project": "premium real estate exterior photography",
            "cta": "call-to-action design with subtle branding",
            "planning": "urban planning diagram",
            "amenity": "luxury amenities showcase",
            "location": "location map with key landmarks",
            "info": "clean information card design",
            "living_room": "bright spacious living room",
            "bedroom": "comfortable master bedroom",
            "balcony": "scenic balcony view",
            "floorplan": "architectural floor plan with annotations",
            "tip_card": "informative tip card",
            "landscape": "beautiful garden landscape",
            "pool": "resort-style swimming pool",
            "detail": "architectural detail close-up",
            "light": "natural light interior shot",
            "material": "premium material texture",
            "panorama": "panoramic interior view",
            "inspo": "design inspiration mood board",
            "living": "family living space",
            "kids_room": "children's room design",
            "kitchen": "modern kitchen design",
            "education": "nearby school exterior",
            "trend": "trending topic visual",
        }
        return elements.get(img_type, "real estate photography")

    def _call_text2img(self, prompt: str) -> str:
        response = requests.post(
            self.API_ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model, "prompt": prompt,
                "negative_prompt": self.NEGATIVE_PROMPT,
                "size": self.SIZE, "seed": -1, "scale": 7.5, "ddim_steps": 30,
            },
            timeout=120,
        )
        data = response.json()
        return data["data"]["image_urls"][0]

    def _call_img2img(self, prompt: str, source_url: str, strength: float) -> str:
        response = requests.post(
            self.API_ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model, "prompt": prompt,
                "negative_prompt": self.NEGATIVE_PROMPT,
                "image_url": source_url, "strength": strength,
                "size": self.SIZE, "seed": -1, "scale": 7.5, "ddim_steps": 30,
            },
            timeout=120,
        )
        data = response.json()
        return data["data"]["image_urls"][0]

    def _download(self, url: str, output_dir: str, index: int) -> str:
        os.makedirs(output_dir, exist_ok=True)
        filename = f"image-{index:02d}.jpg"
        path = os.path.join(output_dir, filename)
        response = requests.get(url, timeout=60)
        with open(path, "wb") as f:
            f.write(response.content)
        return path
