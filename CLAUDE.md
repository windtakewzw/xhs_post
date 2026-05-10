# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

xhs_post is a Xiaohongshu (小红书) content publishing system for real estate projects. It generates real-estate-themed social media posts (copy + images) and publishes them to Xiaohongshu via browser automation.

Current project stage: early implementation — rules system being built first.

## Planned Modules

1. **Rules System** — maintainable Markdown rule files (personas, content types, copywriting, images, hashtags)
2. **Content Generation** — topic selection + Claude API copywriting + Seedream API image generation
3. **Publishing Engine** — Playwright browser automation + scheduling + multi-account management
4. **Comment Tracking** — monitor and collect comments on published posts
5. **Comment Reply** — AI-assisted or automated replies to comments

See `docs/superpowers/specs/` for design docs, `docs/superpowers/plans/` for implementation plans.

## Commands

```bash
# Activate virtual environment
source venv/Scripts/activate

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/rules/test_models.py -v

# Run a single test function
python -m pytest tests/rules/test_models.py::test_persona_creation -v
```

## Architecture

**Rules are Markdown files**, not code. The `src/rules/loader.py` parses them into Python dataclasses (`src/rules/models.py`). The assembler (`src/rules/assembler.py`) builds AI prompt context from structured rules.

Rules are two-tiered:
- `rules/*.md` — global rules shared across all projects (copywriting, image generation, hashtag strategy)
- `rules/{project}/rules.md` — per-project rules (personas, content strategy, taboos)

The upstream design references are in `D:\project\yj_skills\skills\xiaohongshu\references\` (not a runtime dependency).

## Dependencies

- Python 3.11+ (virtual env at `venv/`)
- PyYAML for frontmatter parsing
- pytest for testing
