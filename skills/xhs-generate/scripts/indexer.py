"""Batch generate initial index.md files for image directories.

Scans materials/{project}/ subdirectories for images, generates a starter
index.md with filenames and auto-inferred tags. Descriptions are placeholder
and should be refined manually.
"""
import os
import sys
from datetime import datetime

TEMPLATE = """---
directory: {rel_dir}
updated: {date}
---

| 文件 | 描述 | 标签 | 适用 |
|------|------|------|------|
{rows}
"""


def _is_image(fname):
    return os.path.splitext(fname)[1].lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _infer_tags_tags(fname, dirname):
    """Infer basic tags from filename and directory name."""
    tags = set()
    name_lower = fname.lower()
    dir_lower = os.path.basename(dirname).lower()

    keyword_map = {
        "客厅": ["living_room", "living", "light", "inspo"],
        "卧室": ["bedroom", "inspo"],
        "主卧": ["bedroom", "inspo"],
        "儿童": ["kids_room"],
        "厨房": ["kitchen"],
        "餐厅": ["kitchen", "living"],
        "卫生间": ["detail", "material"],
        "阳台": ["balcony", "panorama"],
        "书房": ["detail", "living"],
        "园林": ["landscape", "detail"],
        "景观": ["landscape", "panorama"],
        "泳池": ["pool"],
        "外立面": ["project", "material", "trend"],
        "别墅": ["project", "living_room", "bedroom"],
        "样板间": ["living_room", "bedroom"],
        "悦海天境": ["landscape", "project", "detail"],
        "逸璟台": ["landscape", "project"],
        "海悦天璟": ["living_room", "bedroom"],
        "公园": ["amenity", "landscape"],
        "学校": ["education", "amenity"],
        "海边": ["amenity", "location", "pool"],
        "游艇": ["amenity"],
        "码头": ["amenity"],
        "营销中心": ["amenity", "location"],
        "区位": ["location", "planning"],
        "航拍": ["panorama", "landscape"],
        "户型": ["floorplan"],
        "平面": ["floorplan"],
        "效果图": ["project", "planning"],
        "鸟瞰": ["panorama", "landscape", "planning"],
    }

    for kw, types in keyword_map.items():
        if kw in name_lower or kw in dir_lower:
            tags.update(types)

    if not tags:
        if "interior" in dir_lower or "室内" in dir_lower:
            tags.update(["living_room", "bedroom", "detail"])
        elif "exterior" in dir_lower or "外立面" in dir_lower:
            tags.update(["project", "material"])
        elif "landscape" in dir_lower or "园林" in dir_lower:
            tags.update(["landscape", "detail", "pool"])
        elif "amenities" in dir_lower or "配套" in dir_lower:
            tags.update(["amenity", "education", "location"])
        elif "location" in dir_lower or "区位" in dir_lower:
            tags.update(["location", "planning"])
        elif "renders" in dir_lower or "效果图" in dir_lower:
            tags.update(["project", "floorplan", "planning"])

    if not tags:
        tags.add("placeholder")  # mark as auto-generated, needs manual review
    return sorted(tags)


def _infer_labels(fname, dirname):
    name_lower = fname.lower()
    dir_lower = os.path.basename(dirname).lower()

    label_map = {
        "客厅": "客厅", "卧室": "卧室", "主卧": "主卧", "儿童": "儿童房",
        "厨房": "厨房", "餐厅": "餐厅", "阳台": "阳台", "书房": "书房",
        "外立面": "外立面", "园林": "园林", "泳池": "泳池", "海景": "海景",
        "户型": "户型", "平面": "户型图", "效果图": "效果图",
        "公园": "公园", "学校": "学校", "码头": "码头", "样板间": "样板间",
        "鸟瞰": "鸟瞰", "航拍": "航拍", "区位": "区位",
        "别墅": "别墅", "电梯": "电梯", "楼梯": "楼梯",
        "逸璟台": "逸璟台", "悦海天境": "悦海天境", "海悦天璟": "海悦天璟",
    }

    labels = []
    for kw, label in label_map.items():
        if kw in name_lower or kw in dir_lower:
            labels.append(label)
    return labels[:3] if labels else ["素材"]


def generate_index(image_dir, project_dir):
    """Generate index.md for a single image directory."""
    full_dir = os.path.join(project_dir, image_dir)
    if not os.path.isdir(full_dir):
        return False

    images = sorted([f for f in os.listdir(full_dir) if _is_image(f)])
    if not images:
        return False

    rows = []
    for img in images:
        labels = _infer_labels(img, image_dir)
        tags = _infer_tags_tags(img, image_dir)
        row = f"| {img} | {' / '.join(labels)}详情，待补充描述 | {', '.join(labels[:5])} | {', '.join(tags[:6])} |"
        rows.append(row)

    content = TEMPLATE.format(
        rel_dir=image_dir,
        date=datetime.now().strftime("%Y-%m-%d"),
        rows="\n".join(rows)
    )

    out_path = os.path.join(full_dir, "index.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Wrote {out_path} ({len(images)} images)")
    return True


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    materials_dir = os.path.join(project_dir, "materials")

    for root, dirs, files in os.walk(materials_dir):
        # Skip if already has index.md
        if "index.md" in files:
            has_images = any(_is_image(f) for f in files)
            if has_images:
                # Already indexed, skip
                continue

        has_images = any(_is_image(f) for f in files)
        if not has_images:
            continue

        rel_dir = os.path.relpath(root, project_dir).replace("\\", "/")
        generate_index(rel_dir, project_dir)


if __name__ == "__main__":
    main()
