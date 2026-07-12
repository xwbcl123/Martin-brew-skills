# Life-OS routing

## Primary input

- `.automation/clip-ledger/*.jsonl`
- Window: `(last_success_at, run_at]` in `Europe/Brussels`.
- Read notes only from ledger `note_path` values that resolve beneath `LIFE_OS_ROOT`.

## Bounded enrichment

Read at most 20 active projects. A project qualifies only when its nearest `_meta.md` contains `kind: project` and `status: active`. Read `_meta.md` plus the first 8,000 characters of the nearest `README.md`; do not recursively scan project bodies.

## Output

```text
50-59_Knowledge-Writing/51.14_reading-clippings-lib/daily-briefs/YYYY/
└── YYYYMMDD_daily-knowledge-brief.md
```

Run manifests:

```text
.automation/daily-knowledge-brief/YYYY/MM/YYYYMMDD_run.json
```
