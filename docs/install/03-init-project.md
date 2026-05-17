# 初始化项目

向 Claude 说"按 docs/install/03-init-project.md 初始化项目"。

## 异常检测

初始化前必须逐项检查，任一不满足则中止并告知用户。

### 检查 1：依赖

```bash
source venv/Scripts/activate
python -c "import playwright; print('OK')" 2>&1
rclone --version 2>&1 | head -1
```

| 异常 | 处理 |
|------|------|
| playwright 未安装 | 先执行 01-install.md |
| rclone 未安装 | 先执行 02-materials.md |

### 检查 2：materials 已挂载且非空

```bash
ls materials/ 2>&1
```

| 异常 | 处理 |
|------|------|
| 目录不存在 | 先执行 02-materials.md |
| 目录为空 | OSS 挂载异常，检查 Bucket 配置和网络 |

### 检查 3：materials 中有项目目录

```bash
ls -d materials/*/ 2>/dev/null | sed 's|materials/||;s|/||'
```

| 异常 | 处理 |
|------|------|
| 无任何子目录 | 先在 OSS 中创建项目素材目录 |

### 检查 4：各项目有素材子目录

项目素材目录结构如下（OSS 端 `sales/data/{项目}/` 下）：

| 目录 | 内容 |
|------|------|
| `楼盘简介/` | 项目概况、区位、开发商、亮点等 |
| `楼盘参数/` | 容积率、绿化率、栋数、总户数等技术指标 |
| `户型清单/` | 各户型面积、格局、配置说明 |
| `销售说辞/` | 各卖点的标准话术 |
| `抗性说辞/` | 针对客户异议的应对话术 |
| `百问百答/` | 常见问题解答 |

验证：

```bash
for proj in $(ls -d materials/*/ | sed 's|materials/||;s|/||'); do
  missing=""
  for dir in 楼盘简介 楼盘参数 户型清单 销售说辞 抗性说辞 百问百答; do
    ls "materials/$proj/$dir/"*.md 1>/dev/null 2>&1 || missing="$missing $dir"
  done
  [ -z "$missing" ] && echo "[OK] $proj" || echo "[MISS] $proj — 缺:$missing"
done
```

| 异常 | 处理 |
|------|------|
| 某项目缺少必需子目录 | 在 OSS 的 `{项目}/` 下补充对应素材目录和 .md 文件 |

## 步骤 1：选择项目

```bash
ls -d materials/*/ | sed 's|materials/||;s|/||'
```

Claude 展示列表，让用户选择初始化哪个。

## 步骤 2：从模板创建项目规则

```bash
cp -r rules/_template "rules/{项目名}"
```

模板 `rules/_template/rules.md` 中 `{{ }}` 为占位符。Claude 读取 `materials/{项目}/` 下各素材子目录（楼盘简介、楼盘参数、户型清单、销售说辞、抗性说辞、百问百答等）了解项目信息后，与用户对话逐一替换。

### 2.1 确认基本信息

- 项目名、城市（从素材推断，用户确认）
- 项目类型（高端改善盘 / 刚需盘 / 海景度假盘 / TOD盘 等）
- 项目特性（海景、园林、精装、地铁等）

替换 rules.md frontmatter。

### 2.2 确认人设

Claude 询问本项目需要哪几个（可选三种）：
- 投资置业顾问（investment-advisor）：数据控，市场/区域/投资
- 生活品质顾问（lifestyle-advisor）：感性，园林/美学/生活
- 家庭置业顾问（family-advisor）：务实，户型/学区/家庭

每个人设确认：姓名、口头禅、语言风格偏好。

### 2.3 调整内容策略

- 每个人设的内容类型占比
- 项目内容禁忌
- 发布频次

替换全部 `{{ }}` 占位符。

## 步骤 3：配置账号

Claude 确认每个人设绑定的账号 ID，替换 `rules/{项目}/accounts.yaml` 中的占位符。

`login_status` 初始为 `inactive`。

## 步骤 4：初始化数据目录

```bash
PROJECT="{项目名}"
mkdir -p "data/$PROJECT/drafts"
cat > "data/$PROJECT/drafts/index.md" << EOF
---
project: $PROJECT
updated:
---

| 日期 | 序号 | 人设 | 内容类型 | 标题 | 状态 | 笔记ID |
|------|------|------|---------|------|------|--------|
EOF
```

## 步骤 5：登录账号

```bash
source venv/Scripts/activate
python scripts/login.py {账号ID}
```

登录后更新 `login_status` 为 `active`。

## 验证

```bash
grep -c "{{" rules/{项目}/rules.md && echo "! 还有未替换的占位符" || echo "规则 OK"
grep -c "{{" rules/{项目}/accounts.yaml && echo "! 账号配置还有占位符" || echo "配置 OK"
test -f "data/{项目}/drafts/index.md" && echo "索引 OK" || echo "索引 MISSING"
```
