---
name: pptx-polish
description: "对 Gamma AI（或其他工具）导出的 PPTX 进行排版后处理：统一字体、提升最小字号、字号标准化、语义色彩映射、增强视觉层次、消解 shape 重叠。支持两种模式：Mode A (Polish) 一键优化，Mode B (Learn) 从手工修改中提取模式迭代改进 skill。"
aspg:
  origin:
    vendor: custom
    imported_at: 2026-03-31
---

# PPTX 排版优化 (pptx-polish)

## 目标

对 AI 工具（Gamma、Beautiful.ai 等）导出的 PPTX 进行一键后处理，解决常见排版问题：

| 问题 | 解决方案 |
|------|---------|
| 字体不统一（Inter / 系统默认字体） | 统一替换为目标字体（默认：微软雅黑） |
| 字号过小（最小可能只有 8-9pt） | 提升至最小字号（默认：16pt） |
| 非标准字号（16.5、21.5、29pt 等） | 精确重映射到标准档位（16、20、32pt） |
| 视觉层次单调（Shape 无区分） | 标题深蓝背景、待决策项黄色边框、完成项绿色边框 |
| 缺少语义色彩（状态无视觉区分） | 交通灯体系：绿=完成、橙=进行中、红=风险 |
| Shape 重叠 / 文字溢出 | 自动扩展 Shape 高度、按 Y 轴推挤消解重叠 |

---

## 执行模式

### Mode A: Polish（默认）

用户提供原始 PPTX → 运行 pptx_polish.py → 输出优化版本。
触发条件：用户提到优化/修复 PPTX 排版、字体乱了、字号太小、Gamma 导出文件需要后处理。

### Mode B: Learn（迭代优化）

触发条件：用户提供"原始版 + 手工修改版"两个文件，或明确说"学习/提取模式/优化 skill"。

执行流程：
1. 运行 `pptx_diff.py before.pptx after.pptx` 生成 diff 报告
2. 阅读报告，按"频次 + 置信度"双轨判定：
   - **高频模式**：出现 ≥2 次的一致性变更 → 直接编码到 pptx_polish.py
   - **高置信单点**：仅 1 次但 deterministic 且回归风险低 → 经用户确认后编码
   - **低置信观察**：仅 1 次且语义不稳定 → 仅记录到迭代日志
   - **结构变化**：新增/删除页 → 标记为非模式，跳过
3. 更新 pptx_polish.py 中的常量/规则
4. 更新本文件的迭代日志
5. 用原始文件重新运行脚本，与手工版 diff 验证差异缩小

---

## 使用方法

### Mode A: 基本用法

```bash
python "skills/pptx-polish/scripts/pptx_polish.py" "path/to/your.pptx"
# 输出：path/to/your_v2.pptx
```

### 自定义参数

```bash
python "skills/pptx-polish/scripts/pptx_polish.py" "path/to/your.pptx" \
  --font "微软雅黑" \
  --min-size 16 \
  --padding 4 \
  --output "path/to/output_v2.pptx"
```

### 完整参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pptx` | 必填 | 输入 PPTX 文件路径 |
| `--font` | `微软雅黑` | 统一替换的目标字体 |
| `--min-size` | `16` | 最小字号（pt），低于此值的字体将被提升 |
| `--padding` | `4` | 文本框内边距（pt） |
| `--output` | 原名+`_v2` | 输出文件路径（不覆盖原文件） |

### Mode B: 样式 Diff

```bash
python "skills/pptx-polish/scripts/pptx_diff.py" before.pptx after.pptx \
  --output diff_report.md
```

| 参数 | 说明 |
|------|------|
| `before` | 修改前的 PPTX |
| `after` | 修改后的 PPTX |
| `--output` / `-o` | 输出报告路径（默认打印到终端） |

---

## 执行流程（9步，顺序重要）

当用户触发 Mode A 时，按以下步骤执行：

### Step 1: 读取输入
- 确认 PPTX 文件路径存在
- 确认参数（字体、最小字号等），未指定则使用默认值
- **关键**：每次都从原始文件重新处理，不在已处理文件上叠加

### Step 2: 运行优化脚本

```bash
python "skills/pptx-polish/scripts/pptx_polish.py" "$PPTX_PATH" \
  --font "$FONT" \
  --min-size "$MIN_SIZE"
```

脚本内部执行顺序（顺序不可调换）：
1. **统一字体** → `a:rPr`/`a:endParaRPr`/`a:defRPr` 全部替换
2. **最小字号** → `sz < min_sz` 提升至 `min_sz`
3. **字号重映射** → 将已知非标准字号 snap 到标准档位（`SIZE_REMAP` 字典）
4. **文本框内边距** → `bodyPr lIns/tIns/rIns/bIns = 0` 设为 4pt
5. **标题配色** → `name="Text 0" + sz≥2000 + y<20%` 加深蓝背景（**必须在边框步骤之前**）
6. **边框着色** → 纯文本框保持透明；待决策项加黄色边框；完成项加绿色边框
7. ~~**语义色彩**~~ → 暂停，匹配逻辑需更精细（只对状态标签上色，非全 shape）
8. ~~**Shape 高度自适应**~~ → 暂停，高度估算对中文偏大导致布局混乱
9. ~~**重叠消解**~~ → 暂停，与 Step 8 级联后 shape 被推到页面底部

### Step 3: 视觉验证（如有 LibreOffice）

```bash
soffice --headless --convert-to pdf "$OUTPUT_PATH"
pdftoppm -r 150 -f 1 -l 1 "${OUTPUT_PATH%.pptx}.pdf" /tmp/slide_preview
```

如无 LibreOffice，告知用户直接在 PowerPoint/WPS 中打开 `_v2.pptx` 查看效果。

### Step 4: 告知用户结果

报告：
- 输出文件路径
- 处理的幻灯片数量
- 如有视觉验证，展示预览

---

## 语义色彩映射表

| 关键词 | 颜色 | 含义 |
|--------|------|------|
| `完成`, `达成`, `✅`, `achieved`, `completed` | `#28A745` (绿) | 完成/成功 |
| `进行中`, `推进`, `on track`, `⏳`, `in progress` | `#F0AD4E` (橙) | 进行中/注意 |
| `风险`, `延迟`, `blocked`, `⚠️`, `❌`, `critical`, `告警` | `#C00000` (红) | 风险/告警 |

优先级：红 > 橙 > 绿（同一 shape 内多个关键词时取最高优先级）。
映射表定义在 `pptx_polish.py` 的 `SEMANTIC_COLORS` 常量中，可直接扩展。

## 字号标准档位

| 档位 | 字号 | 语义 |
|------|------|------|
| body | 1600 (16pt) | 正文 |
| label | 2000 (20pt) | 副标题/标签 |
| heading | 3200 (32pt) | 强调标题 |

当前重映射规则（`SIZE_REMAP`）：`1650→1600`, `2150→2000`, `2900→3200`

---

## 已知限制与注意事项

### 颜色主题依赖
脚本中的颜色（深蓝 `#1E3A5F`、黄色 `#F0AD4E`）是 Blue Tone 主题的配色。
如果用户使用其他主题，颜色目前需手动修改脚本常量；字体可通过 `--font` 参数调整。

### 标题识别条件（重要）
标题 Shape 的识别条件为：`name="Text 0"` + 字号 ≥ 2000（即 20pt）+ y位置 < 20%。
如果 Gamma 生成的标题 Shape 命名不同，标题深蓝背景可能不生效。

### 语义色彩跳过标题
语义色彩映射会自动跳过已被识别为标题的 shape，避免覆盖标题的白色文字。

### 字体安装
`微软雅黑` 需要在目标播放设备上安装才能正常渲染。
如果用于 Windows 以外的环境，考虑使用 `--font "Noto Sans SC"` 或其他已安装的中文字体。

---

## 技术要点（OOXML 核心经验）

从 6 轮迭代中提取的关键知识，供调试时参考：

| 问题类型 | 规则 |
|---------|------|
| **noFill/solidFill 冲突** | `solidFill` 与 `noFill` 不能共存。修改 Shape 填充前，必须先 `spPr.remove(noFill_element)`，否则 noFill 优先级更高，solidFill 不生效 |
| **lxml 元素判断** | 永远用 `if element is not None:`，不要用 `if element:`——无子元素的 lxml Element 在布尔上下文中是 `False` |
| **sz 单位** | `sz="1600"` = 16pt（1/100pt 单位）。计算宽度/高度时必须先 `sz_pt = sz / 100`，再 × EMU（12700/pt） |
| **shape 分类** | 用 `name + sz + y位置` 多维判断，不要只靠数值阈值——KPI 大数字字号也可能 ≥ 2000，会被误判为标题 |
| **文本框透明** | 原始 noFill 的纯文本框不得添加填充色，否则会遮盖底层卡片 shape 的原有颜色 |
| **迭代方式** | 脚本非幂等。每次修改后必须从原始文件重新运行，不能在已处理文件上叠加 |

---

## 迭代日志

### v1.2 — 2026-04-13
- 来源：`forum-deck_kevin_v1.pptx` → `forum-deck_kevin_v2.pptx` 手工对比
- 新增窄规则：**短标签文字扩宽后，背后的空白底框 shape 同步扩宽**
- 本轮只编码高置信标签场景，不处理整行底板、表格背景、大卡片
- 宽度计算改为基于**文本框几何宽度**，并增加文字渲染宽度估算与安全系数，避免标签底框视觉上“刚刚卡边”
- 典型样本页：
  - slide 1：日期标签
  - slide 3：`执行摘要`
  - slide 4：时间范围标签
  - slide 8：页眉标签
  - slide 9：`行动计划`
- 新增相邻标签最小间距处理，避免扩大后左右紧邻标签发生 overlap
- 仍保留为观察项（未编码）：
  - slide 9 多行表格/清单底板整体加宽
  - 需要联动推挤其他 shape 的布局修复
  - 大段正文卡片与容器背景扩宽
- 回归目标：
  - 消除“文字已变宽，但标签底框仍停留旧宽度”的溢出问题
  - 避免误伤正文卡片和整页背景

### v1.1 — 2026-04-01
- 来源：v2→v3 手工对比（11 slides）
- 新增字号重映射 Step（`2150→2000`, `2900→3200`）
- 新建 `pptx_diff.py` 样式 diff 工具，支持 Mode B (Learn) 流程
- 新增 Mode B 执行模式（频次+置信度双轨判定）
- **暂停 3 个步骤**（代码保留但注释掉）：
  - 语义色彩：对整个 shape 上色太激进，误染叙述性文本
  - Shape 高度自适应：估算对中文严重偏大，shape 膨胀
  - 重叠消解：与高度膨胀级联，所有内容被推到页面底部（y 偏移 2-3x）
- **回归验证教训**：
  - `1650→1600` 映射看似单点高置信，实际 8 处 16.5pt 是刻意保留的，已回滚
  - Step 6+7 是 v1.0 就存在的 bug，之前未被发现因为缺少视觉验证
- 观察（未编码）：
  - slide 1 标题纯黑文字被清除
  - slide 8 紫色 `#6B46C1` 被移除
  - slides 5,6,7,9 手工新增 20pt 标签层（属于新增内容而非修改现有字号）

### v1.0 — 2026-03-31
- 初始版本，7 步处理流程
- 6 个核心 Pattern (P1-P6) 编码
- 来源：Gamma PPTX 后处理 6 轮迭代复盘
