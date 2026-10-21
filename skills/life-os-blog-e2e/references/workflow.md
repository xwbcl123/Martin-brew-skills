# Workflow reference

## Stage inputs (loaded by `stage-context`, hashed into a manifest)

The loader reads the Blogs `AGENTS.md` read-first list, `00-admin/rules/rules-registry.yaml`
(stage rules by priority), `00-admin/commands/README.md`, the chosen
`00-admin/templates/pipelines/pipeline-*.md`, the draft/enhance/visual Skill files,
cognition, conventions and glossary. Required files that are missing refuse the stage.
The bundle written under the run directory contains each file verbatim with its SHA-256.
Records keep the `context_id`; `record-stage` rejects unknown context ids.

## Stage output paths

| Stage | File |
| --- | --- |
| research | `05-research/<slug>-research.md` |
| draft | `10-drafts/<date>-<slug>-draft.md` |
| enhance, visuals | `15-enhance/<date>-<slug>.md` (+ referenced `50-assets/img/posts/<slug>/*`) |
| publish-ready | `20-published/<year>/<date>-<slug>.md` (controller copy) |

Every record is one exact Git commit (pathspec-limited, with Run/Revision/Stage/hash trailers);
identical content makes no commit.

## Closed list of rule adaptations

A1 TODO count, A2 source count, A3 image count, A4 Socratic rounds, A5 machine paths,
A6 legacy approve flag. Meanings are in `ADAPTATIONS` in the controller; anything else is
rejected. Voice, categories, front matter, formatting, fact checking and Anti-AI rules stay.

## Publish phases and resume

Journal `<state_dir>/runs/<run>/publish.json` is the single record of publish intent and result:
it is written before the approval is marked used, every phase result (commit SHA, url path,
baseline parent) lives only inside its phase entry and is written in one atomic step, and
completion stores the whole result so a lost `run.json` projection can be repaired without
republishing the same approved digest. A historical `done` record is not evidence that the live
article exists, and must not authorize publishing changed bytes under an old approval.

`place` (Blogs commit) -> `baseline` (target identity, fetch, ff-only, no staged changes, records
parent SHA) -> `copy` (refuses dirty targets, byte-verifies) -> `build` (known side-effect files
restored) -> `commit` (HEAD must equal the baseline parent; a commit found by trailer is trusted only
after ancestry, parent, exact file set and blob hashes match the frozen sources) -> `push`
(commit tree re-verified, then `<exact sha>:refs/heads/<recorded branch>`, plain fast-forward;
timeout leaves `unknown` and origin is checked before any retry; success needs remote ancestry).

The digest binds site, repo root, origin (credentials stripped) and branch with article and asset
hashes, so drift refuses resume (`resume_digest_changed`). Before every external phase the approval
is re-checked (`approval_revoked_or_invalid`, actor still allowed); edits invalidate used approvals;
`revoke` is coordinator-only. Approval ids derive from the gateway event or manifest nonce+digest,
so replays return the original approval.

## Publication readiness and incident triage

1. Parse the actual final source front matter with a real YAML parser. Keep `published: false` for drafts, but set explicit `published: true` in the publication candidate before committing, freezing and requesting approval. Do not silently transform an already approved source while copying it to the publish repository: the digest binds those metadata bytes too.
2. Exercise the exact candidate, not a preview copy whose publication flag was overridden. Use an isolated Hexo workspace with the existing theme, configuration, dependencies, one target post and its referenced assets; run `node "$BUILD_ROOT/node_modules/hexo/bin/hexo" generate` from that workspace. Do not delete shared production output or expose other drafts merely to test one post. If diagnosing the publication flag, run clean isolated before/after builds: an exit-zero result with the false flag can omit the page, while the true flag must produce the expected article.
3. Require concrete generated-page evidence before push: a non-null located URL, an HTML file for the target article, matching title and distinctive body text, resolved image references and matching local asset bytes. Reject missing, stale same-slug, placeholder or unrelated pages. Neither process exit zero nor an asset directory with the article slug proves that the article HTML was generated.
4. After deployment, read the exact production URL and verify the article content and assets; separately confirm that the deployment corresponds to the pushed commit. If an HTTP client is blocked, use a real browser to distinguish an access interstitial from the actual page status. Do not use an archived copy or a success deployment badge as evidence that the current article is live.
5. If acceptance fails after a push, record the real partial outcome: pushed commit, deployment result, generated-page evidence and live response. Preserve the prior source, journal, approvals and relevant hashes before correcting anything. A generated URL of null or a live 404 must remain an explicit failure, not be smoothed into successful publication.
6. Obtain authorization for a controller repair when needed. Reproduce the failure and test draft rejection, exit-zero/missing output, stale output and approval-preserving recovery in temporary repositories before adopting a fix. For a changed candidate, require a fresh frozen digest and a new unused approval; keep prior journals and used approvals immutable. If the installed controller lacks a tested correction path, stop at that blocker rather than deleting its completed journal, clearing approval usage, manufacturing an authorization manifest or issuing an ad hoc push. Do not describe an unfinished recovery implementation as a proven workflow.

## Enrichment and runtime verification

- Run controller validation with an existing Python environment that has the article validator's dependencies (especially PyYAML). When the system interpreter reports empty `categories` for valid multiline YAML, inspect `common.parse_frontmatter` and rerun using the already provisioned profile venv; do not flatten valid metadata, install packages unattended, alter checks, or change approval policy to hide a parser fallback failure. Keep the real failure and successful rerun in the QA record.
- Choose visual form by semantic job. For an explanatory essay, a text-integrated infographic can combine the section's exact keywords/relationships with a consistent cartoon author guide; do not replace the text's argument with an unrelated scenic story. When the author specifies his cartoon anchor, preserve Asian adult male appearance and glasses consistently. Use scene-based editorial art only when it supports the brief, not as the blanket default for every abstract L2. Generate one style/character/text anchor and inspect it before the remaining set. Inspect all Chinese labels at full resolution and mobile size, not merely a contact sheet. Preserve correct names, qualifiers and source context; add no metrics or achievements. If native text needs correction, use bounded native edits, or transparent typography-only compositing onto genuinely generated reserved regions; never misrepresent the production method. Review anatomy, logo-like marks, cropping and repetition. Record native dimensions and any crop separately; do not upscale to disguise a shortfall or present manually authored SVGs as native image generation.
- Before freezing, parse the final Markdown in Python, enumerate actual `##` sections and classify each real Markdown/Hexo image reference as a lead illustration or supporting diagram. For one-image-per-L2 requests, assert one distinct lead per meaningful section; count intentionally retained secondary/folded diagrams separately rather than rejecting the enrichment for having additional explanatory images. Exclude cover/banner and commented source links from body coverage. Resolve every referenced file, verify hashes, and decode raster outputs. A plain source-note paragraph need not become an artificial image-requiring section; do not remove meaningful sections to lower coverage requirements.
- Bind source SVGs and the visual provenance manifest with explicit local `/img/posts/<slug>/...` references in article comments when those bytes must be committed, frozen and backed up with the WebP outputs. Inspect every asset via a contact sheet and key diagrams at larger size.
- Preserve natural-language finalization instructions verbatim and distinguish them from preceding editorial feedback. A request to publish after edits may authorize finalization, never a digest-bound publish approval.

## Photo-first travel and family refresh

1. **Bind and preserve.** Resolve the named article to its explicit run, base revision and source hash; preserve the current article before preparing candidates. Keep the original date, slug and production permalink unless a migration is requested. In an isolated Hexo build, preserve the production post's filename as well as its front matter: the configured permalink can include the dated filename. A refresh is not a new article or a reusable historical publish grant.
2. **Read both kinds of source.** Read the complete source clip and the matching day's personal journal/voice transcript. Use photos and captions for visible scene details, and the personal account for the author's lived experience, reactions and reflection. Distinguish raw speech from an organized transcript and AI-written reference passages; do not turn edited prose into direct quotations. Record source-backed additions and unresolved contradictions in a private evidence sidecar. New diary evidence may establish meals, departure, return or reactions absent from the earlier clip; do not inherit an old exclusion without checking its reason. A photographed menu still does not establish an order, restaurant or expenditure.
3. **Inventory before editing.** Parse all image references in the source and candidate, resolve local files, and save a deduplicated manifest with source identifier/hash, output path/hash, dimensions and intended scene. Report total references separately from unique photos and distinguish body images from cover reuse. Compare the sets programmatically; restore each requested unique photo or explicitly explain an agreed exclusion. Do not count one photograph twice to imply complete coverage. Inspect a labeled contact sheet and ambiguous originals before assigning captions; do not infer exact species or show names from an uncertain image.
4. **Produce genuine photo assets.** Use real source photographs, not generated substitutes. Save versioned WebP derivatives without overwriting prior assets, apply EXIF orientation and omit metadata including GPS. Record actual conversion parameters and any resizing; do not upscale to conceal a resolution shortfall. Keep public provenance manifests limited to needed source identifiers and transformations, not absolute private paths or full diary contents. A journal may describe a moment for which no photo was supplied: retain the sourced prose without inventing its image.
5. **Rewrite around experience.** Connect selected scenes with what the author noticed, felt and later thought; use approximate times only when they help orientation. Prefer a few concrete, source-backed human details over repeated declarations that the day was wonderful. Handle family friction gently, without assigning blame, inventing dialogue or claiming others' feelings. Place restored photos adjacent to their relevant prose with accurate ALT/captions; do not hide supposedly restored content behind a collapsed block. Keep maps and menus as useful supporting material rather than turning the essay back into a schedule or price list.
6. **Verify distinct acceptance lanes.** Decode every derivative, assert the source-to-body photo set, then build the exact candidate in an isolated workspace with existing Hexo dependencies. Require the correct generated article, diary-derived text probes, all expected body image references and matching output image bytes. In a real mobile browser, scroll the whole article and inspect actual image sources rather than counting decoded loading placeholders; use the visibility/lazy-loading checks in `references/tunnel-preview.md`. Compare `.markdown-body img` title values with `.markdown-body figcaption.image-caption` text in document order, asserting one caption per intended photo; do not assume a `<figure>` ancestor, because Fluid can render an image link and figcaption inside a `<p>`. Inspect image enlargement and overflow separately. After parent review, apply the base-bound revision, freeze/validate, preserve exact commits and verify additive backup readback. Deliver the revised Markdown and a useful contact sheet; expose a public tunnel or publish only under the corresponding current authorization. Do not describe a candidate-generation handoff as an integrated or published refresh.

## Background Codex illustration upgrade

1. Bind the job to an explicit run, base revision and verified article hash. Claim `visuals`, obtain its `stage-context`, and instruct the worker to read the entire bundle plus the enrichment/visualizer rules before generating. Pass the user's actual visual feedback, not merely an image count.
2. Write a durable task file under the run directory and launch one tracked native background process:

   ```bash
   codex exec -C "$BLOGS_ROOT" --sandbox workspace-write --json \
     --output-last-message "$JOB_DIR/result.md" - \
     < "$JOB_DIR/task.md" > "$JOB_DIR/events.jsonl" 2> "$JOB_DIR/stderr.log"
   ```

   Use the terminal tool's background/completion notification support; retain its process handle in the run ledger. Keep the usual sandbox and approval baseline. Do not launch a second worker for the same asset set.
3. Have the worker call its native `image_gen` directly, checkpoint each real output, and write only candidate Markdown, new versioned asset filenames, per-image provenance, a visual manifest, contact sheet and machine-readable QA. Keep the official article and prior assets unchanged during generation. Preserve successful images if a later call fails; resume from checkpoints rather than regenerating the set.
4. Treat process exit zero as a handoff, not acceptance. A nonzero exit can also occur after assets, candidate and QA have been saved (for example, model capacity during final handoff); inspect checkpoints before retrying or discarding the set. Preserve the exact failure and have the parent finish acceptance when the actual deliverables are sufficient, rather than regenerating paid/subscription outputs. Do not conflate unrelated MCP OAuth or websocket fallback warnings with image-generation failure. Read the result and QA, inspect the actual contact sheet, decode files, verify original/derivative hashes and count distinct leads. Compare normalized candidate prose against the bound base; image-only work may change paths, ALT, captions and image front matter, not the author's arguments. Remove robotic audit disclaimers from captions before integration.
5. Have the parent integrate at the controller's exact expected article path using `revise --run R --stage visuals --base-revision N --context-id C` and the exact verified user feedback event. Re-freeze and validate; asset changes invalidate the previous approval digest even if prose is unchanged.
6. Let the controller make its exact article/referenced-asset commit. Preserve source originals, edit predecessors and QA sidecars with a separate explicit-path audit commit when they are not included in that stage commit. Never use broad `git add .`; tools may leave unrelated local state files beside the writing work.
7. Run `backup --run R --extra <path>` for audit artifacts and source originals omitted by the referenced-asset set, then read back every returned destination. Keep unexplained Drive-side conflicts intact. Distinguish a verified mounted-directory mirror from remote cloud synchronization.
8. Rebuild and update the already authorized isolated preview via `references/tunnel-preview.md`; return a cache-busting revision URL and contact sheet only after public/mobile readback. Separate content illustrations/infographics from cover roles: when the author asks for new covers, independently generate a full-bleed, comfortable hero background and a small-card-readable, eye-catching index image, rather than cropping/pasting a character out of an accepted body infographic. Text-free covers are appropriate; preserve all approved body assets and check hero title contrast, real desktop/mobile cropping, and an actual Fluid index card. Measure the actual rendered image rectangle and object-fit at desktop and phone widths; a theme's fixed-height mobile card can be much wider than the simulated 3:2/320×200 thumbnail, so verify face, glasses and focal objects under the real CSS crop rather than claiming zero cropping from an asset-only mockup. Check phone-size key labels separately from detail readability. Prefer the theme's native image-click/Fancybox enlargement; verify it by clicking an image before omitting redundant text links. Do not add repeated “查看清晰大图” links when the image itself already enlarges. Report remaining detail-size or margin shortfalls honestly. Do not publish or reuse an old digest approval.

## Gaps by design

Cloudflare deployment readback runs only if `cf_deploy_readback_cmd` is configured; otherwise
reported as `unsupported_unconfigured` and the public URL readback is the evidence.

## Preview and release acceptance

Build a disposable Hexo site using the configured site's installed dependencies and the exact
current candidate in `source/_posts/<published filename>`. Do not run builds against the production
checkout for editorial preview. Before delivery run:

```sh
python scripts/blog_e2e.py render-check --run RUN --site-dir /path/to/disposable-site
python scripts/blog_e2e.py preview start --run RUN --site-dir /path/to/disposable-site
```

The checker compares source bytes to the current recorded article, rejects unpublishable metadata,
and checks unique generated HTML, all substantial body paragraphs, actual image references and
image bytes. It grants no approval and changes no run state. The local preview serves only the
checked article and image assets. Draft overrides require an explicitly labelled editorial preview;
they cannot count as production parity. Record configuration/HTML-only preview adaptations and
perform browser checks of title overlay, card, zoom, captions, lazy loading and mobile cropping.

The final freeze must bind the publishable candidate. After a release `verify-online` requires all
substantial visible article paragraphs, visible asset references, image MIME/bytes and the configured
deployment reader. A missing/failing reader is partial even if public content matches. HTTP200 of a
placeholder, hidden text, a title-only page, old paragraphs or a commented-out image is not success.
A WAF challenge from one client is not proof of availability or outage: retain the response, retry
with a normal user agent or browser, and verify distinctive live body content and asset hashes.

Preserve the original journal on corrective releases; never reset used approvals. Each changed
candidate must have its own freeze and fresh exact gateway approval. User feedback about future
visual style does not authorize editing already accepted current assets.
