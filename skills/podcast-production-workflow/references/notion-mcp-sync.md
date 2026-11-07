# Notion MCP lifecycle projection

Version: 1.1 · Reference-only, agent-executed · No background synchronizer

## Entry, authority and private binding

Read this reference at the lifecycle boundaries below when the host has native OAuth Notion MCP and an explicit target binding. Notion is the collaboration projection (fourth plane). Workshop production records / `episode.json`, accepted Library assets and Knowledge Plane notes retain their existing authority. A Notion checkbox, comment or status never grants publication, human acceptance, cleanup or rights authority. Existing v1/v2 gates remain in force.

Resolve the binding from the task's explicit private binding reference or the host podcast Knowledge dashboard; never choose by a globally searched title. The binding must supply expected workspace/account identity, database and data-source identity, show/profile mapping and any stable episode-code aliases. Keep personal IDs, URLs and source pointers outside portable skills (private host note or excluded `references-private/`); never add them to the ten-key runtime config. No new credentials, REST client or reauthentication of another harness.

Fetch the connected self, bound database and actual data-source schema before writes. Compare expected identity and database ancestry. Missing binding, identity mismatch, no structured query capability, unavailable MCP/auth/permissions or unreadable schema stops only the projection branch. Missing siblings/references are deployment gaps, not permission to copy a second writable contract.

## Lookup, diff and reconciliation

One episode owner serializes Notion writes. Use a host-local projection lock/write-ahead receipt outside any immutable sealed package; retain an interrupted attempt for reconciliation. This is single-owner coordination, not an atomic remote uniqueness guarantee across uncoordinated hosts.

1. Resolve stable `Episode Code` and `Show` from actual source identity and the private binding. A directory slug/date discrepancy needs an explicit alias; never silently generate a new code. Prefer code + show. If unavailable, use exact `Season & EP` + show. If both keys exist, query both and compare page identities, including an unscoped code-collision check; conflicting keys or another show's reused code fail closed. Global search may discover a candidate database but proves neither absence nor uniqueness.
2. Query **within the bound data source**, using fetched column/property types. MCP SQL: parameterized equality predicates with `params`, or a native typed filter. A saved view is sufficient only if its filters cover the entire identity domain; exhaust pagination. Never treat one page of results, a title match or a truncated response as absence. Preserve rich text with rows/fetch before editing text; SQL may flatten formatting and links.
3. Zero matches: create only under existing episode-projection authority, with complete keys and no prior ambiguous attempt; record intent before create, then fetch the returned page and requery. One: verify parent/source/show/episode identity and diff only evidenced fields. More than one, conflict, incomplete query or unknown identity: record `error/ambiguous_identity`, no mutation. The reference grants no database/schema/view/ACL changes or historical bulk backfill.
4. Re-read relevant current properties immediately before an update. Send only a nonempty allowed diff; equality is `noop`, never a fake mutation test. Preserve human-edited fields unless local evidence plus the current field policy authorizes their replacement. Missing/unverified evidence is omitted and recorded, never converted to false or cleared automatically. Do not regress a later stage when replaying an older hook; divergent manual state requires reconciliation. Correcting a previously true gate also needs current contradictory evidence and an explicit, reviewable diff.
5. Timeout/lost receipt/503 after create, update or append: status `pending`, fetch the exact page/returned committed IDs and requery both keys before deciding whether anything remains. Never blindly retry create/append. Retry a known remaining idempotent diff only after current revision/source evidence is revalidated. Respect tool retry guidance, use bounded read retries; an unresolved write remains pending.

Example logical query (substitute only the fetched table identifier; values remain parameters):

```sql
SELECT url, "Episode Code", "Season & EP", "Show"
FROM "<bound collection URL>"
WHERE "Show" = ? AND ("Episode Code" = ? OR "Season & EP" = ?)
```

Run the exact-code collision query separately if a code exists. Tool names differ by harness: inspect current MCP definitions rather than inventing a universal `query-database` call. If rows/filter/SQL cannot establish full uniqueness, skip mutation.

## Four lifecycle hooks and six modules

The stages below are semantic labels: resolve their **exact existing enum names**, including any translated suffix, from the live schema. Never create enum options as an implicit side effect. Unknown option/type means that field is skipped with a schema error; preserve verified independent fields when safe and mark the hook partial.

| Hook / actual completed event | Property projection | Body modules | Required evidence |
|---|---|---|---|
| H1 topic plan delivered (`podcast-topic-planning`) | `02_Topic Planned`; Episode Title, Episode Code, Show, Season & EP, Hosts & Guests, Topic Tags; KB pointer | M1 topic + four acts; M2 ThoughtForge briefing, critique/creator reflection, verbatim summary + pointers | Existing local plan/brief with revision/hash, profile identity; proposed dialogue/quotes remain labeled proposed |
| H2 rough-cut Intake accepted (`podcast-production-workflow`) | `04_Audio Post & Mastering`; Record Date; Gate 1 only when proven | M4 recording handoff / role-to-stream/channel map | Read `_meta.md`, actual saved WFP and original-media mapping, source hashes, accepted intake report/decision; correlation cannot identify speakers |
| H3 enrichment **and** package acceptance completed | `06_Package & Gate Review`; Duration, LUFS / Audio QC, Artwork Style, Local Preview URL; Gate 2 only when proven | M3 artwork brief + selected image pointer; M5 Show Notes, chapters, actual quotes; reading summary + pointers | Final audio/QC/duration, current enrichment and local preview; all three v2 content/experience/implementation receipts approved, independent and bound to current manifest/audio/artwork/preview/payload/review-context/runtime; successful rendering alone is insufficient |
| H4a publication verified | `07_Published & Verified`; Publish Date, Public Episode URL, Audio Stream URL; Gate 3 only when proven | M6 publication receipt summary | Existing hash-bound publication authority and actual controller API/media/share/RSS/transcript readback for exact show/remote episode/revision; use actual published date, never a scheduled date |
| H4b storage governance completed, a separate later event | `08_Archived & Cleaned`; Gate 4 only when proven | M6 append/update a separate cleanup receipt submodule | Exact approved cleanup manifest + matching execution and preservation verification, tied to this episode; H4a alone never satisfies H4b; complete stage requires publication and cleanup evidence |

Finished-audio entry may skip rough-cut Intake; omit Gate 1 with an applicability reason. A source plan's proposed record date/duration/LUFS is not an observed recording or QC result. Stale/missing receipts leave the relevant gate unasserted, even if a phase label is available. Manual checked gates are not upstream authorization or proof. No media rendering, upload, publish or cleanup is initiated by this reference.

### Schema/type adaptation

| Logical fields | Expected live types | Encoding / constraints |
|---|---|---|
| Episode Title | title | Source-backed string; distinguish draft title from published title |
| Episode Code, Season & EP, Knowledge Note | text / rich_text | Exact stable key; KB path explicitly labeled local-only when applicable |
| Show, Artwork Style | select | Existing option only; resolve show against private profile/provider identity |
| Pipeline Stage | status | Exact live option; no implicit regression on hook replay |
| Hosts & Guests, Topic Tags | multi_select | Existing, evidenced names/tags only; preserve collaborators' additions or reconcile conflict |
| Gate 1–4 (use full live property names) | checkbox | Use current MCP encoding, not inferred Boolean coercion; this connector exposes `__YES__` / `__NO__` |
| Record Date, Publish Date | date | Use the connector's actual date syntax; some expose `date:<name>:start/end/is_datetime`; date-only versus datetime remains explicit |
| Duration, LUFS / Audio QC | text | Include units; measured value and QC evidence pointer, not a target presented as measurement |
| Local Preview URL, Public Episode URL, Audio Stream URL | url | Existing verified URL for this exact artifact/episode; no fabricated Drive/Transistor links or new public hosting |
| Cover Artwork (optional existing field) | file/files | Leave unchanged unless the task separately authorizes upload; never persist expiring signed URLs as durable pointers |

`Knowledge Note` is a portable logical label; the private binding maps it to the actual fetched text property name. The private binding records observed property names and enum mappings. Re-fetch schema on drift. Do not put local filesystem paths in URL properties, or label localhost as remotely accessible. A repo/Vault-relative KB path is text with a local-access qualification. Existing verified public preview URLs may be reused without uploading anything; a show homepage is not a verified episode URL. New metadata does not repair unrelated historical fields implicitly.

## Body ownership, native MCP adapters and comments

Six logical modules are independent. Select a supported adapter by actual tool capabilities, **not by the mere absence of low-level block APIs**. Native Markdown operations can project body text without exposing block IDs. A heading match alone never grants ownership of existing human text. Keep source revision/hash, exact before snapshot, module key, remote content hash and locator in the owning session receipt. Record real block IDs when exposed; otherwise `block_ids: null`, `locator_kind: native_markdown_region`, reason and the exact visible markers. Never invent IDs or claim block-identity preservation from text equality.

### A. Native Markdown adapter

Inspect current `fetch`, `update_page`, `get_comments` and Markdown resource definitions. The present native interface supports `insert_content` with `position.type=end` and `update_content` with `content_updates[{old_str,new_str}]`. These are different capabilities from low-level block mutation; no REST bridge is needed.

**New owned projection / additive snapshot** (safe fallback when comment/suggestion discovery is incomplete):

1. Confirm the existing data-source/page identity and episode authority; acquire the existing episode owner's local projection lock. Fetch the current page with `include_discussions=true`. Persist source-bound intent and the entire returned before body before the write. Inspect warnings, unknown/truncated blocks and transport output. Separate complete **expected-region** readback from completeness of all underlying native subtrees: absent `truncated` / `unknown_block_count` / `unknown_block_ids` fields are unknown, not false/zero, and a closing content tag proves only that the wrapper closed. A newly generated, never-used attempt namespace may be inserted without touching unobservable existing subtrees; marker absence in incomplete output cannot reconcile or authorize retry of an earlier attempt. If the intended target/expected region itself is incomplete, stop that operation.
2. Choose a visible namespace for each logical module and source revision, such as `podcast-sync:H1:M1:source-sha256=...`. Bind it to this owner/page/source in the receipt. It is a locator and dedup key, **not permission to edit any matching user text**. A pre-existing marker without the owner's matching intent/receipt requires reconciliation, never adoption by name. Search the existing receipt/evidence directory across **all source revisions and hooks** for the same binding/page/stable module identity, and check the entire returned body for all corresponding markers/attempts. Keep stable module identity separate from a revision-specific attempt key; source-hash changes never bypass an older pending attempt. A missing local receipt does not authorize appending another copy. Store the exact intended Markdown, operation, source digest, page ID, unique persisted attempt marker and before snapshot before calling MCP.
3. No remote marker and no uncertain prior attempt: `insert_content` at page end to add only the newly generated projection, leaving every pre-existing module and commented/suggested span untouched. Label it as an automatic source-backed supplement, not a new human-authored episode module or a publication receipt. Existing six modules need not be adopted/recreated. Use supported native toggles for the supplement. Do not replace an existing tail/heading merely to simulate insertion.
4. Read back the complete new region and entire page. Require the original body to remain an exact contiguous prefix (apart from a recorded boundary newline) and the new owned paragraphs/markers to match in full and order, with correct counts/hashes. Compare properties/identity and any available discussions; unreported discussion data is unknown, not zero. Record this as verified **additive body projection**, not verified replacement or preservation of invisible comment anchors. The insertion operation must not target existing blocks.
5. Recovery: exactly one intent-bound attempt marker and complete matching payload → record committed and fill the receipt without writing; multiple markers, wrong content or incomplete expected region → pending/conflict. No marker in an incomplete or not demonstrably current response → pending, never infer that the insert failed. Without a reliable definitive absence/commit result, do not retry. Same current source/owner markers + matching full remote region: no-op, no insertion; an old source revision alone is not a no-op for a new desired revision. A changed source may produce a separately revision-labeled immutable snapshot only when that revision is genuinely needed, the previous snapshot/receipt still matches and the request permits additive history. Clearly identify its module/source revision; do not fabricate a revision just to exercise writes, update old snapshot text, or accumulate the same revision twice. Limit unmerged snapshot history to two per module by default; further consolidation needs safe replacement capability or explicit review, otherwise `pending/consolidation_required`.

**Replace an already-owned native region** (an additional, stricter capability):

- Read `fetch(include_discussions=true)` and `get_comments(include_resolved=true)`. Compare XML `shown-count` with `total-count`; follow every `omitted-discussion` by its discussion URL. If `omitted-truncated=true`, use fetch discussion indicators to recover the remaining URLs, or keep discovery unknown. For each discussion, follow `next-cursor` with its `discussion_id` until exhausted; compare comment-count/total-comment-count and preserve anchor association. Unresolvable count discrepancies or omitted anchor regions are incomplete. Inspect `suggested_edits_status` separately and inspect affected pending suggestions only when supported; an absent status is unknown. Keep `comments_status`, `suggestions_status` and `target_association_status` separately in the receipt. `suggested_edits_status=upgrade_required`, omitted/incomplete discussion results, unknown status, or a discussion whose affected region cannot be established must **not** be interpreted as “no comments/suggestions”. Without sufficient visibility, leave existing text unchanged and use the additive route when independently permitted; no account/plan upgrade or alternate credentials are implied.
- The region must have explicit owner/source provenance and exact stable start/end markers, each uniquely present. Current region hash must match the last verified receipt; human additions or marker collisions fail closed. Any comment/suggestion touching the target or its boundary requires reconciliation, not deletion/recreation. If block IDs are available, use them as corroboration; their absence alone is not a veto when native targeting and discussion safety are established.
- Immediately refetch/recheck the target and discussion state, then use the smallest uniquely matching `old_str`, with `replace_all_matches=false`, replacing only the owned region. Never use global headings, whole-page `replace_content`, `allow_deleting_content`, or a replacement that includes unrelated blocks. Compare the **whole** before/after outside-region text and full desired region. An acknowledged write without complete readback remains pending.
- Native tools do not expose a compare-and-swap/ETag contract here. A local lock and exact-string recheck reduce ordinary races but cannot guarantee atomic protection against concurrent human edits or another host. Conflicting edits, changed discussions or uncertain results require read-only reconciliation; do not describe the adapter as a transaction engine or comment-identity guarantee.

### B. Low-level block adapter (when actually exposed)

A harness exposing complete block-ID reads and scoped updates may record parent/root/child IDs and update only its owned blocks after the same source/hash/discussion checks. Preserve commented blocks and human text; never delete/recreate them to simplify a diff. Absence of this adapter affects ID-specific editing, **not all native body operations**.

### Failure and verification scope

Unknown create/insert/update outcome: mark pending and re-fetch/reconcile the entire known page/markers before any retry; never treat a single negative search or incomplete readback as absence. Return property and each module's status separately, with adapter/mode, available capability, exact skipped operation and reason. Missing `update_content` blocks replacement, not insertion if independently supported; missing comment/suggestion visibility blocks editing existing spans, not appending isolated owned snapshots. If neither path is safe, retain local text/pointers and report the concrete gap.

## Payload tiering and completeness

Read the current MCP Markdown/resource specification before body writes. `/briefing`, `/critique`, four-act outline, Show Notes, chapter timestamps, selected quotes and receipt summaries may be direct text when reasonably sized. Split at semantic paragraph boundaries; each textual block/`text.content` fragment must fit 2,000 **characters**, not words or bytes. Use Unicode-aware counts, conservatively also check UTF-16 length for emoji; do not split grapheme sequences or escape syntax. An entire Markdown request is not one rich-text fragment. Native supported toggles group long sections; do not invent unsupported HTML.

Long verbatim / full Reading Transcript: only a faithful 300–500-character synopsis, actual discovered terminology and authoritative source pointers; never stream the complete transcript through MCP. Preserve full texts locally. If briefing/critique is also unusually long, keep its full authoritative local version and disclose summary/pointer projection rather than silently truncate. Never invent an online reading page or Drive sharing URL; label a local path as accessible only with the appropriate Vault/host mounted.

The public API documents 2,000 characters per rich-text `text.content`, 1,000 block elements and 500 KB per payload; these are **not** a guarantee of identical native MCP capacity. Source: [Notion request limits](https://developers.notion.com/reference/request-limits) (checked 2026-11-07). Inspect actual host limits; use the lower bound. Operational target for this Reference: at most 20 textual blocks / 16 KiB serialized UTF-8 per batch, smaller if the tool requires; this is a conservative policy, not a measured MCP ceiling. Do not promise seconds, zero truncation or 100% reliability.

For **every** body batch (including medium text), store expected module/paragraph count, character/UTF-8 byte counts, order and normalized content hash; fetch remote content and compare the entire intended region, not first/last lines. Expected-region completeness and whole-page native-subtree visibility are separate results; missing truncation/unknown-block metadata remains unknown. A complete expected-region match and unchanged returned before-content do not prove invisible subtrees or comment-anchor identity. Record only documented or observed transport normalization, including exact returned marker spelling and code-fence language aliases. Dedup/recovery must use that persisted observed representation; do not strip arbitrary escapes or silently broad-normalize user text. Missing/truncated/unknown blocks or a mismatch leaves the module pending; never report done from an accepted write alone. If the tool cannot prove completeness within its output limits, retain the local text/pointers and report the gap.

## Receipt, failure and recovery

Keep a projection receipt in the existing owning session's evidence area, or the host's existing mutable control directory for direct runs, never inside a sealed package. One receipt per `binding + show + episode key + hook/subevent + source revision/digest`. Record:

```text
contract_revision; owner/run_key; hook/subevent; source_refs/revisions/SHA256;
workspace/account match; database/data_source; show/key; page_id;
before properties; intended patch; actual tool/operation/time/result;
modules: adapter/mode, owned block IDs (nullable), native markers/locator, source hash, before/after remote hash,
         paragraph/order/character/byte completeness and discussion check;
properties_status; body_status; overall_status; omissions/reasons;
after readback; retry/reconciliation_required; local access limits.
```

No credentials, cookies, expiring signed URLs or private binding copies in portable skills/public artifacts. Overall states: `done` (all applicable requested projection verified), `noop` (all already verified equal), `partial` (some fields/modules verified), `skipped` (no capability/binding/auth), `error` (known failure/conflict), `pending` (unknown write result or unresolved readback). A local receipt never confers production-stage acceptance. Do not modify existing `episode.json`, seal or old receipts merely to log Notion sync.

On failure, finish already authorized local production/publication under its own contract. Final report includes `⚠️ Notion MCP sync skipped (reason)` when skipped, or the honest partial/error/pending state and evidence pointer. Recovery first verifies current local stage/revision/hash, fresh remote state and earlier attempt; superseded source work must not replay an old hook over a newer stage. Lack of Notion auth in one harness never warrants changing another harness's login.

## Routing and deployment scope

`podcast-topic-planning/SKILL.md` routes H1 here using its sibling path. `podcast-production-workflow/SKILL.md` routes H2, H3, H4a and H4b at their actual completed events, including when it calls downstream skills. Both must resolve this **single** canonical file relative to their installed directories; deploy the two sibling skills together. Missing companion means projection skipped; local planning remains usable. No absolute developer-machine paths or duplicate writable contract copies.

Direct invocation of enrichment/release-package/publish **without the production orchestrator** does not execute these new routes automatically; neither do raw Python entrypoints. The caller must explicitly request lifecycle reconciliation through the production entry (projection only, no production rerun), read this Reference and verify the already-completed event's evidence. Do not claim all family entrypoints are instrumented. This minimal two-entry integration is agent instruction, not an enforced daemon or deterministic transaction engine.
