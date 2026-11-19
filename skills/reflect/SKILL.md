---
name: 'reflect'
description: 'Run an end-to-end daily journal pipeline: process the inbox, write the journal, generate and publish a cover, and email the HTML result (host-specific paths are placeholders)'
argument-hint: '[日期 YYYYMMDD，可选；默认从 inbox 自动检测]'
---

# /reflect — 每日 Reflect 一键流水线

按照 `<journal-lib>/AGENTS.md` 的 3P 模型（Prepare / Process / Polish）和 Cognitive Layer 协议（Inspector / Writer / Linker / Chronicler），完成今日 daily journal 的端到端生产。

## 输入

- `$ARGUMENTS`（可选）：目标日期，格式 `YYYYMMDD`。
- 未提供时：从 `<journal-lib>/00_inbox/` 文件名（`transcript-YYYYMMDD.md` / `Google-Drive-YYYYMMDD.md`）自动检测。
- inbox 为空时：**明确告知"inbox 为空"并退出**，不要编造任何内容、不要生成空日记骨架。
- 可选标志：`--no-cover`（跳过 Phase 2.5）、`--force-cover`（已有有效封面也重生成）、`--cover-only`（inbox 已空但日记已定稿时，只补跑 Phase 2.5 + 日志追加，不属于“inbox 为空则退出”）。
  - `--no-email`（跳过 Phase 3.5 邮件投递）、`--email-only`（日记与封面均已定稿时，只补跑 Phase 3.5 并追加日志）。

---

## Phase 1 — Process（脚本自动化）

1. **Inbox scan**：
   ```bash
   find "<journal-lib>/00_inbox/" -type f
   ```
2. **Dry-run**（先检测 Python 命令，再执行）：
   ```bash
   # OS 适配：Windows 用 python，macOS/Linux 用 python3
   # 检测方式：先尝试 python3 --version，失败则用 python
   python3 "<journal-lib>/50_system/scripts/13.10_process-inbox_v1.0.py" --dry-run
   ```
   ⚠️ **Python 命令因 OS 而异**：
   - **macOS / Linux**：用 `python3`（系统无裸 `python`）
   - **Windows**：用 `python`（Python 3 解释器注册为 `python`，无 `python3`）
   - 如果 `python3` 返回 exit 49 / command not found，立即改用 `python`（PowerShell 执行）
3. **Execute**：去掉 `--dry-run` 实跑（同样遵循上述 OS 适配规则）。
4. **Verify 三项**：
   - `00_inbox/` 已清空（递归确认）
   - `00_transcripts/YYYYMMDD_*.md` 已落地
   - `10_daily/YYYY/YYYY-MM-DD.md` 骨架已创建

---

## Phase 2 — Polish（Cognitive Layer 认知层写作）

### Step A: Context Gathering（**绝不跳过**）

1. 读 transcripts：`00_transcripts/YYYYMMDD_transcript.md` + `00_transcripts/YYYYMMDD_transcript-google-drive.md`
2. **Deep Context Search**（跨域）：
   ```bash
   find . -type f \( -name "*YYYYMMDD*" -o -name "*YYYY-MM-DD*" \) 2>/dev/null | grep -v "/.git/"
   ```
   **必须跨 vault 搜索**：上面只覆盖 宿主 vault。主人的工作类事实（项目、会议、技能产出、任务会话）在 <work-vault>（`<work-vault>`，尤其 `tasks/sessions/YYYY-MM-DD/`、`20 Projects/`、`Daily/`、`.agents/skills/`）。检索时用 `grep -rIl` 加 `--include="*.md" --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.git`，避免命中依赖目录；只读不写。日记里引用该 vault 的内容用反引号路径，不用 wikilink。
   这一步是 v2.1 协议要求 —— transcripts 只是骨架，真正的"血肉"来自跨域文件（clippings、project docs、operation logs 等）。
3. **Calibration（v2.4 关键步骤）**：读 `10_daily/YYYY/` 中最近 1—2 篇 `status: active` 的日记作为活基准。当前推荐基准：`2026-05-14.md`、`2026-05-13.md`（必要时往前找最新的两篇）。校准点：
   - 时段粒度：`### 🌅 早间（HH:MM—HH:MM）：xxx × xxx × xxx` 格式
   - 章首"结论先行"段落 ≈ 120—250 字，因果链密集
   - 每个 bullet 3—4 句因果链 + 系统思维
   - 核心洞察 2—3 个，每个 "结论先行段" + 3—4 个深度 bullet
4. **Outline Mode 判定**：扫描 transcript 末尾是否有 `Outline` / `大纲` / `核心洞察大纲`：
   - 有 → **Guided Mode**（严格按用户给的洞察点展开，不自由发挥）
   - 无 → **Free Mode**（Pyramid Principle 自由综合 2—3 个洞察）

### Step B: Inspector QC（写前清扫）

- frontmatter：`jd_id: "13.10"` 正确 ✓；`status: draft` → `active`；`updated` 改为今天
- 标题：自动生成的`🤖星期X日志@YYYY/MM/DD：待定主题` 必须替换为具体主题
- WikiLink 卫生（§6.5）：`[[xxx.md]]` → `[[xxx]]`，去掉 `.md` 后缀
- 占位断链：`[[YYYYMMDD_gdrive-review-gdrive-activity]]` 这类骨架占位删除/替换为真实文件

### Step C: 全量覆写 daily journal

保持以下结构（绝对遵守 §6.4 自动化块边界）：

1. **frontmatter**：标题贴当天主题、tags 具体到当天关键词（不要泛化）、status: active、updated 改今天
2. **H1 + 章首段落**：H1 与 frontmatter title 一致；H1 下一段 120—250 字"结论先行"密集叙述
3. **🌟 章首总评** — 3 条：✨亮点 / ⚠️待改进 / 🗝️关键启发，每条 3—4 句因果链
4. **🧭 按时段回顾** — 4—6 段：标题 `### EMOJI 时段（HH:MM—HH:MM）：xxx × xxx`，每段 1—3 个粗体标题 bullet，每个 bullet 内嵌 3—4 句因果展开
5. 💻 数字足迹 (Digital Footprint) / 🎙️ 语音闪念 (Voice Insights) — **绝不覆盖**脚本生成的内容（§6.4 硬约束）；如有 `.md` 后缀污染，只允许做"语义不变的最小修正"
6. **💡 核心洞察阐述** — 2—3 个洞察：
   - 每个 `### 💡 (N)："标题"` + 标签行 `` **`[🏷️ 标签1 × 标签2 × 标签3]`** ``
   - "结论先行"段落（80—150 字，给整个洞察定调）
   - 3—4 个深度 bullet，每个粗体标题 + 3—4 句因果展开
7. **🔗 Related Links** — 按"📝 语音与日记原材料 / 📋 运行日志 / 📰 当日剪藏 / 📋 项目文档"分组，**包含 Phase 2 Step A.2 找到的所有跨域文件**
8. **🧭 日记导航** — `⬅️ [[YYYY-MM-DD-1]] | 📅 [[YYYY-MM]] | ➡️ [[YYYY-MM-DD+1]]`

### Step D: 写作风格（§6.6 强约束）

- **必须第一人称**（"我"），不要写成第三人称点评或"你应该…"教练口吻
- 每个 insight module = 一个独立故事：情境 + 叙述 + 反思 + 行动，高密度
- bullet 粗体标题 = 结论本身；**不要**套"背景/叙述/反思/判断/行动"固定模板
- 不写 review 注释；如有反馈先融入正文再删除
- **日记正文不得出现 agent 点评**：禁止“我没有在这次整理里找到…”“尚未独立验证/核对”“转写对齐结果”“口述与日报对照/证据边界”“不把…写成确定事实”这类口吻。日记是 作者的自述，可信度来自事实本身；查不到就先去下一个来源查（见 Step A.2），仍缺则直接不写该点，不要把检索过程或不确定性写进正文。来源间冲突、未核实项只记入运行日志的 Deviations，不进日记。

---

## Phase 2.5 — Cover（封面出图，默认执行；`--no-cover` 跳过）

在日记定稿（`status: active`、无模板占位）之后执行。核心契约吸收自 `.agents/skills/create-cover-illustration`（需要更多细节时读其 `references/`），执行辅助脚本为 `50_system/scripts/13.10_cover-generate_v1.0.py`（`hash` / `verify` / `codex` / `cmux`，JSON 输出，不改 Markdown、不上传）。

### 2.5.1 幂等前置门
- 日记 H1 紧邻处已有封面块且本地 `_assets/YYYY/MM/YYYYMMDD_journal-cover.png` 通过 `verify` → **跳过**，除非 `--force-cover`。
- 重新生成前先备份旧 PNG（加时间戳后缀），不覆盖已发布资产。

### 2.5.2 Storyboard → 冻结 prompt
读完整日记后在内存中构建 storyboard：`date`（精确日期）、`central_narrative`、`central_scene`、5–8 个 `event_clusters`（时间/角色、事件、2–4 个可见物件、1–3 个关键概念）、底部时间轴/情绪弧、`must_preserve`、`must_avoid`。覆盖主要时段与主线，不画每一句。然后编译为最终 prompt 并**冻结**，写到 scratchpad（不入 vault），用 `cover-generate hash` 记 SHA-256；任何重试逐字节复用，质量修订才产生新版本。

Prompt 模板：
```text
Create a hand-drawn 16:9 journal memory-map infographic from this storyboard.
Purpose: let the reader reconstruct the day at a glance; a rich daily memory map, not a minimalist cover.
Main title: choose a short, source-grounded Simplified-Chinese title; show the exact date [YYYY-MM-DD].
Central narrative: "[…]"   Central scene: [concrete scene]
Event clusters: 1. [position/time]: [event]; show [objects]; preserve [concepts, exact proper names] … (5–8)
Bottom timeline: [chronological or emotional arc].  Tone and palette: [source-grounded].
Keep it information-rich but legible via hierarchy and grouped panels. Do not invent events.
```

共享约束：横版 16:9 手绘卡通信息图；中文日记的标题与簇标题用简体中文，保留必要英文专名；暖色、记忆友好；优先具体动作/物件而非通用齿轮灯泡；禁止照片写实、3D、光泽 UI、暗色电影感、水印、香蕉/猴子元素（除非来源需要）；敏感/受版权人物用通用形象替代；避免官方 logo 与误导性背书。**人物**：配偶出现时必须画成成年人；孩子**仅在当天来源明确出现时**按“孩子”画（关系与人数写入 prompt 白名单），不得添加来源未提及的孩子或宠物，也不要写成绝对 “no children”。

### 2.5.3 出图路由（总尝试预算 3 次，prompt 不变）
- **路由 A（默认）Codex CLI**：
  ```bash
  python3 "<journal-lib>/50_system/scripts/13.10_cover-generate_v1.0.py" codex "<prompt.txt>" --out "<journal-lib>/_assets/YYYY/MM/YYYYMMDD_journal-cover.png"
  ```
  默认 `gpt-6-luna` + `medium`（与 宿主的 Codex 配置 一致）。运行中即等待，不算失败。产物以脚本校验过的 `--out` 为准，**不要**猜 `~/.codex/generated_images/` 的“最新文件”。
- **路由 B Cmux/Luna**（A 失败，或用户指定）：脚本现场从 `cmux tree --all` 解析 宿主指定的 workspace 里名为 `luna` 的 surface（不硬编码 ID），用 `--paste` 投递任务包指针 + `send-key enter`，要求 worker 出图后 `cp` 到 `--out`，轮询 `read-screen`（启动 ≤120s，约 25s 一次，软超时 ~7 分钟）：
  ```bash
  python3 "…/13.10_cover-generate_v1.0.py" cmux "<prompt.txt>" --out "<同上路径>"
  ```
  `send` 成功、屏幕回显、结束标记**都不算完成**，以 `verify` 通过的真实文件为准；超时标记 unknown，确认原 worker 已终止前不重复派发同一日期。
- 两条路由均失败：提示用户可手动用 Codex App 出图，把 PNG 放到 `--out` 路径后用 `--cover-only` 续跑；不编造任何图片或链接。

### 2.5.4 502 / VPN fallback
仅当路由返回**明确可重试的 502**（JSON `retryable: true`）且 VPN 原本为 connected 时：
1. 用 computer use 在 VPN 应用里**临时 Pause**（不关闭 Kill Switch），记录原状态；
2. 用同一 prompt 重试一次（计入 3 次预算）；
3. 无论成败**立即恢复**并核实 connected/protected；恢复不确定 → 停止后续上传、如实报告。
502 不等于 VPN 是原因，不要在非 502 失败时切 VPN。

### 2.5.5 质量门
硬门：真实 PNG 字节（`verify` 通过）、≈16:9、标题与日期正确、中心故事吻合、无虚构事件、关键标签可读且拼写正确、无禁用内容。偏好门：语义覆盖、个人特异性、层级、检索价值、平衡、可读性。局部缺陷定向编辑，日期错/主线错/关键文字不可读则重生成。

### 2.5.6 发布
1. 在 H1 与开篇段落之间插入**唯一**封面块（不用 Obsidian 图片 wikilink）：
   ```markdown
   ![具体可见内容的 alt（≤60 字）](../../_assets/YYYY/MM/YYYYMMDD_journal-cover.png)
   > ⬆️ *短记忆提示（≤30 字）*
   ```
2. 管线先 dry-run 再实跑：
   ```bash
   python3 "<journal-lib>/50_system/scripts/13.10_image-pipeline_v1.0.py" --date YYYY-MM-DD --dry-run
   python3 "<journal-lib>/50_system/scripts/13.10_image-pipeline_v1.0.py" --date YYYY-MM-DD
   ```
   dry-run 成功不是发布验收。
3. 验证：PNG/WebP 均存在且 MIME 正确、H1 紧邻处仅一个封面块、日记其余正文未漂移、URL map 与备份、托管 URL `HTTP 200` + `image/webp`（用 `curl -sI` 实测）。
4. **失败策略**：出图或上传失败**不回滚日记**，保留本地图片，在日志中记为 warning。

---

## Phase 3 — Logging（Chronicler 协议）

若 Phase 2.5 已执行，在运行日志**追加**（不覆盖）一个 `## Cover` 小节：路由与模型、总尝试与各次结果、prompt SHA-256、选定候选、本地路径、托管 URL、备份、URL map、caption、VPN 是否触发及恢复验证、最终日记 SHA-256、warnings。

写入 `90_logs/YYYYMMDD_operation_log.md`：

```markdown
---
title: "Operation Log YYYY-MM-DD"
jd_id: "13.10"
type: operation-log
tags: [ops-log, inbox-processing, cognitive-synthesis]
status: active
created: <今天日期>
---

# 📟 System Operation Log — YYYY-MM-DD（处理 YYYY-MM-DD 数据）

## Summary
<一段话总结：处理了什么 + 日记主题>

## Timeline
<表格：时间 | 动作 | 状态>

## Action Taken
### 1. Inbox 处理
### 2. 认知层写作 (v1.0 完成)
### 3. 已识别 Next Actions（未执行，记录备忘）

## Deviations from Standard Path
<偏离/特殊情况/警告>
```

然后回到日记的 Related Links 加入：
```markdown
### 📋 运行日志
- [[YYYYMMDD_operation_log]] — 系统运行日志：Inbox 自动化处理 + 认知层写作记录
```

---

## Phase 3.5 — Deliver（邮件投递，默认最后一步；`--no-email` 跳过）

日记（及封面，若执行）定稿并写完运行日志后，把日记发给家人收件人，抄送主人备份。**发送方式不限定**：有 Gmail MCP 用 Gmail MCP；没有则 fallback 到 macOS Mail.app（AppleScript / `osascript`）；其他可用的等价手段也可。无论哪种方式，都必须满足下面的 spec。

### 3.5.1 收件人与授权
- 默认：To `<PRIMARY_RECIPIENT>`，Cc `<BACKUP_CC>`。
- 只允许发往 `AGENTS.md` §4 的白名单地址（由宿主 `AGENTS.md` 维护的收件人白名单）；白名单外地址必须停止并询问用户。
- 主题：`【日记】YYYY-MM-DD 星期X｜<日记标题的 2—3 个关键短语>`。重发时在主题标注「重发」并在正文首行说明以此封为准。

### 3.5.2 内容 spec（所有发送方式通用，硬约束）
1. **必须是 HTML 邮件，不得把 Markdown 源码当纯文本发出**。把日记 Markdown 渲染为带行内样式（inline style）的 HTML：
   - 标题（`#`/`##`/`###`）→ `<h1>/<h2>/<h3>`；`**粗体**` → `<b>`；`*斜体*` → `<i>`；`` `代码` `` → `<code>`；列表 → `<ul><li>`；`---` → `<hr>`；
   - 不得残留 `#`、`**`、`- `、`![]()`、`[[wikilink]]` 等 Markdown/Obsidian 语法；wikilink 去括号只保留文字；
   - 去掉 frontmatter；去掉脚本生成的 `### 💻 数字足迹` 与 `### 🎙️ 语音闪念` 块；去掉 `## 🔗 Related Links` 与 `## 🧭 日记导航`（含本地路径与 vault 内部链接，对收件人无意义）；
   - 容器宽度约 680px，字体栈含 `-apple-system, 'PingFang SC'`，中文可读；页脚写“来自每日日记 · YYYY-MM-DD”（日期必须是当天，不得沿用旧值）。
   - 同时提供简短的 plain-text 备选正文（一句话说明即可），不得是 Markdown 全文。
2. **封面图必须能在邮件里直接预览**（若当天有封面）。外链 `<img src="https://…">` 会被部分发送链路（如 Gmail MCP）的服务端剥离，**不得只依赖外链**。优先使用**内嵌图片**：
   - 先把封面 PNG 转为体积适中的 JPEG（如 `sips -s format jpeg -s formatOptions 82 -Z 1400 <png> --out <scratchpad>/cover.jpg`，目标约 ≤1MB），不要原样塞 3MB 的 PNG；
   - 以内嵌附件（inline attachment / CID）方式随信发出，HTML 中 `<img src="cid:…">` 引用；Gmail MCP 用 `inline: true` 的附件并写 `cid:att0`（按附件序号）；Mail.app 用带 `Content-ID` 的 multipart/related，或至少把图片作为附件附上并同时保留 HTML 中的位置；
   - 若所用方式确实无法内嵌，退而求其次：HTML 中放外链 `<img>`，**同时**把 JPEG 作为普通附件附上，并在正文给出托管 URL 文本链接。
   - 当天无封面（`--no-cover` 或出图失败）则不放图，不得编造图片或链接。
3. **发送后必须回读核验，不得以“send 调用成功”当作完成**：
   - 在已发送中按主题检索并回读，确认 To/Cc 正确、HTML 正文存在、封面以内嵌或附件形式存在（`<img src="cid:…">` 未被剥成空 `<p>`）；
   - 若回读发现图片被剥离或正文变成纯文本，立刻用内嵌方式补救重发，并在主题与正文注明“重发”，在日志中如实记录两封的存在（已发出的邮件无法撤回）；
   - 对远端写入结果不确定时，先回读对账再决定是否重试，避免重复发送。
4. **Mail.app fallback（2026-11-19 实测可用的写法）**：Mail.app 的 AppleScript 不能直接写 CID，但 `html content` + 随后追加附件即可：Mail 会生成 multipart，把 JPEG 作为内嵌图片发出，HTML 中出现 `<img src="cid:…">`，收件方可直接预览。要点：
   ```applescript
   set htmlText to (do shell script "cat " & quoted form of "<渲染好的 html 路径>")
   tell application "Mail"
     set m to make new outgoing message with properties {subject:"…", visible:true, sender:"<发件账号地址>"}
     tell m
       make new to recipient at end of to recipients with properties {address:"…"}
       -- 有 Cc 时同样 make new cc recipient
       set html content to htmlText
     end tell
     delay 2
     tell m
       make new attachment with properties {file name:(POSIX file "<cover.jpg>")} at after the last paragraph of content
     end tell
     delay 2
     send m
   end tell
   ```
   - **顺序与位置很重要**：必须先 `set html content`，等待片刻后再追加附件，并用 `at after the last paragraph of content`；实测先附件、`at before the first paragraph`、再设 HTML 会丢图（收到的只有空 `<img>`，无附件）。
   - HTML 里不要放封面 `<img>` 占位或外链，图由 Mail 以内嵌附件形式插到正文末尾；若希望图在正文开头，改为先发送前在 HTML 顶部留空段落，并在回读后确认位置可接受。
   - Mail 会把正文包进一个无边框 `blockquote` 容器并改写为自己的字体样式，粗体/列表/标题层级保留，属正常现象；plain-text 备选由 Mail 自动生成，不需要手写。
   - 发送账号必须是 Mail.app 里已登录的账号；实测成功用的是 `visible:true`（首次失败同时用了 `visible:false` 与相反的顺序，未单独验证是哪个因素起作用，所以保持与成功写法一致）。
   - 发送前先清理自己创建的残留 outgoing message，不要触碰 用户已有的草稿窗口；测试邮件只发给白名单内的 用户自己。
   - 回读时用 Gmail MCP 或在 Mail 已发送箱检查：附件 `*.jpg` 存在、HTML 中有 `cid:` 引用、无 `**`/`#` 残留；仍无法确认时停止并向用户报告，不要发纯文本版。

### 3.5.3 临时文件与日志
- 渲染出的 HTML 与 JPEG 放 scratchpad，不入 vault。
- 在运行日志追加 `## Email` 小节：发送方式（Gmail MCP / Mail.app / 其他）、收件人与 Cc、主题、封面呈现方式（cid 内嵌 / 附件 / 外链）、回读结果、是否有重发、warnings。
- 邮件失败**不回滚日记**；如实报告失败原因，并给出 `--email-only` 续跑方式。

---

## Phase 4 — 严禁动作清单（防复发）

- ❌ **不要编造封面 CDN URL**：只允许使用 `13.10_image-pipeline` 实际回写、并经 `curl -sI` 验证为 `HTTP 200` 的托管链接，**绝不** fabricate `https://<image-host>/...`。inbox 没有图像文件不再意味着无封面——由 Phase 2.5 生成；若 Phase 2.5 被跳过或两条路由都失败，明确告知用户并保持日记无封面块
- ❌ **不要在非 502 失败时切换 VPN**；切换后必须立即恢复并核实 connected/protected，不得关闭 Kill Switch
- ❌ **不要在重试间改写冻结 prompt**，不要猜“最新生成图片”当作本次产物，不要把 `send` 成功或结束标记当作出图完成
- ❌ **不要覆盖** `### 💻 数字足迹 (Digital Footprint)` 和 `### 🎙️ 语音闪念 (Voice Insights)` 两个脚本块（§6.4）
- ✅ **Python 命令 OS 适配**：macOS/Linux 用 `python3`，Windows 用 `python`；执行前先 `python3 --version` 探测，失败立即切换 `python`（勿在 Bash 工具死磕，改用 PowerShell 工具）
- ❌ **不要在 wikilink 中保留 `.md` 后缀**（§6.5）
- ❌ **不要对整个 宿主 vault 做 `Get-ChildItem -Recurse`**（§6.1）；用 `find . -name "*YYYYMMDD*"` 或 `rg` 限定查找
- ❌ **不要把命令字符串混进自然语言**（§6.1）
- ❌ **不要把 Markdown 源码当纯文本邮件发出**；不要只依赖外链图片（可能被剥离）；不要发往白名单外地址；不要把“send 成功”当作投递完成（必须回读）
- ❌ **不要做超出 §6.4 允许范围的"语义改动"**：脚本生成的 Voice Insights 内容只允许做 wikilink 后缀清理这类"语义不变"修正

---

## Phase 5 — End Report（Mode A 技术汇报）

按宿主全局指令约定的技术汇报格式输出：

```
✅ Final Conclusion
🔧 Actual Changes（表格：文件 | 动作）
⚖️ Tradeoffs & Reasons
✔️ Verification Results
```

确保：
- Verification 包含三项验收：inbox 已清空 / transcripts 已落地 / 日记骨架已覆写
- 若执行了 Phase 2.5，另加封面验收：路由与尝试次数 / prompt hash / 本地 PNG 与 WebP / 唯一 H1 紧邻封面块 / 托管 URL HTTP 200 + image/webp / VPN 是否触发及已恢复
- 若执行了 Phase 3.5，另加邮件验收：发送方式 / 收件人与 Cc / HTML 渲染（无 Markdown 残留）/ 封面内嵌或附件 / 已发送回读结果 / 是否有重发
- Tradeoffs 解释关键选择（Free Mode vs Guided Mode 的判定、洞察取舍、未编造的封面图等）
- 如有 deviation 明确列出（如 python3 / 无封面 / 跨域文件稀薄等）

---

## 参考

- 协议权威源：`<journal-lib>/AGENTS.md`
- 风格指南：`<journal-lib>/50_tools/templates/STYLING_GUIDE.md`（如存在）
- 校准基准：`<journal-lib>/10_daily/YYYY/` 最近 1—2 篇 `status: active` 的日记
