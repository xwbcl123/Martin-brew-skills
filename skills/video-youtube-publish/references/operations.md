# Publishing operations

The channel map is local at `~/.config/video-skills/config.json`. Operator approvals and resolutions are in `~/.config/ytpub/operator/`. The episode registry is `~/.config/ytpub/publish-registry/`. State and receipts are in `~/.local/state/ytpub/publish/<episode-key digest>/`. The journal records durable intent, acknowledgement and independent verification. Keep all of these together for the lifetime of the run.

The controller uses a read-only owner query to verify the channel. The accepted operations are the private upload, custom thumbnail, timed captions, optional private playlist membership, and readback. The controller verifies the private video's media processing and metadata, downloads the thumbnail to check its distinctive QR marker, downloads each caption track to compare normalized cues, and checks exact playlist membership when applicable. It requires the full set of readback evidence before producing a complete receipt.

The sealed request always includes a JSON boolean for `containsSyntheticMedia`. An expected `true` requires an explicit owner readback of `true`. For expected `false`, an explicit `false` is recorded as `explicit_false`. An absent key is recorded as `api_omitted_false_default` with `expected: false`, `observed: null`, `key_present: false`, and `wire_request_sent: false`. Here `wire_request_sent` is the literal sealed request value. The classification describes the accepted response shape. A present JSON `null`, a mismatched boolean, or another type fails verification. Other disclosures still require exact owner readback.

An absent or ambiguous provider response can leave a durable unknown outcome. Use `--mode reconcile` for a zero-media probe of the existing upload session. The tool needs a registered resolution and matching journal attempt for additional claims, explicit abandonment, or continuation from an independently confirmed upload offset. `scripts/operator.py record-resolution --input LOCAL_RECORD.json` displays and records the operator's attestation to a proposed resolution. Store the proposed record outside Git and the vault with mode 0600. It contains the exact episode, package revision, seal, channel, journal sequence and digest, operation key, attempt ID, decision, and independently captured observation digests.

A completed run can use a trusted, expired authorization for fresh readback. A revoked authorization blocks provider access. For a live test, record the date interval and the sanitized JSON from a separate `ytpub analytics query` call over the latest seven complete YouTube reporting dates. Missing rows can demonstrate connectivity with a valid column schema.

## Production profiles and revisions

Pass the same `--profile` to operator approval, plan and apply. The approval displays the channel, parent revision and its current video ID, target privacy/schedule, exact notification setting and the ordered operation plan. The plan is bound to the sealed package and preview. Production `--yes` flags derive from that approval.

- `operator.py approve --mode update --package ROOT --profile PROFILE [--video-id VIDEO_ID]` requires bit-identical MP4 bytes and a higher revision. The controller verifies the current owner video and updates only the approved differing fields or assets. Captions can be removed when their IDs were proven by the parent receipt and their tracks are absent from the new seal. Playlist changes are additions.
- `operator.py approve --supersedes-revision N --package ROOT --profile PROFILE` confirms the current successful parent. The new MP4 must differ from all held uploads for the channel. Republish uses a new ID and writes a manual cleanup suggestion into its receipt.
- Each write is recorded by `INTENT`, `ACK` and independent `VERIFIED`. Reruns preserve an immutable execution plan. An ACK is followed by readback and an unresolved intent requires reconciliation. Re-encoded thumbnails without a provable matching rendition may require a `verified_thumbnail_rendition` operator resolution against the exact ACK and source/download hashes.

For a revision that cannot finish, inspect known effects using `publish.py --mode reconcile --inspect-effects`. This records evidence without business mutations. Have the operator explicitly attest the matching revision resolution and apply it through `--mode reconcile --resolution ID`. An abandoned revision stays in history. Previously dispatched or uncertain upload media remains reserved.

An old v1 registry with open jobs stays readable by its original pinned runtime. Drain those jobs there. For an irrecoverable open job with intact original evidence, record a `legacy_revision` resolution, then run `operator.py migrate-registry --legacy-resolution ID` with exactly one resolution per such job. The import updates only the registry and preserves all old job bytes.

## Operational pitfalls and multi-host notes

- Profile names must match `[a-z0-9][a-z0-9_-]{0,95}` (periods such as `my.channel` are rejected; use `my-channel`).
- Leaving `smoke-test` bound to a channel UC ID forces `effective_smoke: true` on any production alias for that channel via `is_smoke_channel()`. Remove the `smoke-test` mapping and clear old smoke bindings before upgrading a channel to production.
- Thumbnail marker verification runs both `cv2.QRCodeDetectorAruco()` and `cv2.QRCodeDetector()` because OpenCV's legacy detector alone intermittently misses valid Version 5 QR markers (~4–10% observed failure rate), while still rejecting multi-QR conflicts.
- `operator/`, `publish-registry/`, and `~/.local/state/ytpub/publish/` remain machine-local. Never run concurrent first uploads or updates for the same episode across multiple hosts; when handing off an already-uploaded video across hosts, run read-only `ytpub videos get VIDEO_ID --profile PROFILE` first and authorize `--mode update --video-id VIDEO_ID`.
