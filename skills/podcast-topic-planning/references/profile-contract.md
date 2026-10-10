# Podcast Brand Profile Contract & Extensibility Guide

> **规范版本**: v1.1.0  
> **所属 Skill**: `.agents/skills/podcast-topic-planning`  
> **权威 Schema**: `profiles/_schema.yaml`  
> **校验脚本**: `scripts/validate_profile.py`

---

## 1. 设计哲学：为什么采用 Profile-Driven 架构？

传统播客策划 Agent 往往采用单提示词（One-Prompt-Fits-All）的方式，导致生成的选题大纲千篇一律、语调悬浮。
Martin 旗下拥有多元播客生态：
- 《极客家庭》(Geek Family Podcast) 是有血有肉的三人家庭生活对谈；
- 《Cyber Martin's Podcast》是高密度的硬核架构师技术独白或 AI 探索对谈；
- 未来还将孵化《AI Security Forum (ASF)》等专业前沿智库访谈。

因此，`podcast-topic-planning` 采用 **Profile 解耦驱动架构**：
- **核心逻辑通用**：事实挖掘、网络查证、证据分层、张力构建、四幕式编译、本地 HTML 交互生成、Guarded R2 部署。
- **品牌特性外置**：通过 `profiles/<profile_id>.yaml` 定义具体品牌的人格特征、口头禅、冲突矩阵、受众定位、存储前缀与视觉主题。
- **高可扩展性**：新增任何播客品牌，仅需添加一份 YAML，无需修改任何代码或核心 Prompt！

---

## 2. 命令行与执行接口

```sh
# 列出系统当前所有可用的播客品牌 Profile (带严格字段校验)
python3 .agents/skills/podcast-topic-planning/scripts/validate_profile.py --list

# 校验特定 Profile 是否合法 (防路径穿越，仅支持小写字母与连字符)
python3 .agents/skills/podcast-topic-planning/scripts/validate_profile.py --profile geek-family

# Agent 启动策划时指定 Profile
# 例如：
# "帮我策划一期极客家庭新单集，关于周末露营" -> Agent 自动选用 --profile geek-family
# "针对刚刚读完的这篇文章，策划一期 Cyber Martin 播客" -> Agent 自动选用 --profile cyber-martin
# "策划一期关于大模型越狱的安全圆桌" -> Agent 自动选用 --profile asf
```

---

## 3. 如何新增一个播客品牌 Profile？

只需在 `.agents/skills/podcast-topic-planning/profiles/` 下新建 `<brand-id>.yaml`：

1. **指定基本信息**：`id`, `name`, `show_id`, `tagline`, `description`；
2. **选择录制形态** (`format.type`)：
   - `trio_dialogue`: 三人固定角色对谈（如 Geek Family）；
   - `solo_monologue`: 单人沉思独白（如 Cyber Martin）；
   - `ai_duo_discussion`: AI 辅助的双人辩论探索；
   - `interview_panel`: 主持人 + 特邀嘉宾圆桌（如 ASF）。
3. **注入角色矩阵 (`personas`)**：每个角色的唯一 ID、心智模型、表达特征与口头禅；
4. **配置冲突动力学 (`tension_matrix`)**：角色之间的典型冲突点与杀手提问（引用 ID 必须在 personas 中存在）；
5. **设置存储路由 (`routing`)**：Vault 单集目录前缀与 R2 发布路径（禁止绝对路径或包含 `..` 的路径遍历）；
6. **运行校验**：`python3 scripts/validate_profile.py --profile <brand-id>` 确保验证通过。
