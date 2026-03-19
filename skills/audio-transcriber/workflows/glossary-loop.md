# Glossary Learning Loop

闭环术语学习系统，覆盖所有三个 ASR 场景。

## 流程

1. **Step 1 (API)**: Gemini API 只做 raw ASR，不做术语发现。
2. **Step 2 (Claude)**: Claude 在后处理阶段负责术语发现，产出 `{stem}_new_terms.md`。
3. **用户审阅**: 在 Obsidian 中勾选确认的术语（`- [ ]` → `- [x]`）。
4. **回写 glossary**:

```bash
# Preview (safe, no changes)
python scripts/transcribe_audio_gemini.py --update-glossary path/to/_new_terms.md

# Confirm and write
python scripts/transcribe_audio_gemini.py --update-glossary path/to/_new_terms.md --apply
```

## `_new_terms.md` 格式契约

与 `--update-glossary` 写回流程兼容，**必须使用 ASCII `->` 箭头**：

```markdown
# 候选新术语 (待确认)
> 来源: {source_file}
> 日期: YYYY-MM-DD

- [ ] term -> 标准形式 (上下文说明)
```

**重要**: 必须使用 ASCII `->` 而非 Unicode `→`。现有 `--update-glossary` 的 regex（`r"->\s*`?([^`\(]+)`?"`）仅匹配 ASCII 箭头。

### 格式要求

- 标题行必须为 `# 候选新术语 (待确认)`
- 每条术语必须为 `- [ ] ...` 格式（unchecked checkbox）
- 用户在 Obsidian 中勾选为 `- [x] ...` 后，`--update-glossary` 才会提取

## Glossary 维护

- Glossary 位于 `prompts/glossary.md`（相对于 skill root）
- Auto-discovered terms 追加到 `## 📝 新增术语 (Auto-discovered)` section
- 重复术语自动跳过
- **最佳实践**: 定期审查 `📝 新增术语` section 的准确性，并将确认的术语重新分类到主要分类中
