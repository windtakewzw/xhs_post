# 安装

向 Claude 说"按 docs/install/01-install.md 执行"。

## 步骤 1：Python 环境

```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

## 步骤 2：Chromium 浏览器

```bash
python -m playwright install chromium
```

## 步骤 3：安装 Skill 到 Claude Code

```bash
mkdir -p ~/.claude/skills/
cp -r skills/xhs-generate ~/.claude/skills/
cp -r skills/xhs-publish ~/.claude/skills/
cp -r skills/xhs-monitor ~/.claude/skills/
cp -r skills/xhs-reply ~/.claude/skills/
```

重启 Claude Code。

## 验证

```bash
source venv/Scripts/activate
python -c "import playwright; print('OK')"
python skills/xhs-publish/scripts/publisher.py --help
python skills/xhs-monitor/scripts/fetcher.py --help
ls ~/.claude/skills/xhs-*/
```
