---
name: sea-ad-s3
description: >
  Use when routing SEA-AD data or analysis to an S3 bucket; constructing or
  interpreting a SEA-AD S3 URI; understanding bucket, prefix, naming, or
  tagging conventions; listing or inspecting objects with read-only AWS
  commands; or determining whether data may cross a sensitivity boundary.
  Triggers on: "where should this SEA-AD dataset live?", "which bucket holds
  production/working-group/site/sensitive data?", "what is the prefix for X?",
  "can I move this to standard storage?", "generate/interpret a SEA-AD S3 URI".
---

## Routing workflow

1. **Classify sensitivity** — determine PII presence and DUA restrictions
   *before* suggesting a bucket. If either is unclear, stop and ask; never guess.
2. **Choose bucket class** — `prod` for frozen/completed outputs; `wg` for
   active analysis; `site-data` for external-site deposits. Then pick standard
   vs. highly sensitive based on sensitivity classification.
3. **Load the reference** — open `references/buckets-and-routing.md` for the
   full bucket table, sensitivity rules, and routing examples.
4. **Propose a URI** — construct the path using the prefix schema in
   `references/paths-and-tags.md`. State explicitly that you have not verified
   the path exists.
5. **Verify read-only** — if AWS access is available, suggest `aws s3 ls` or
   `aws s3api head-object` to confirm. All SEA-AD buckets are private and
   require ambient AWS credentials; never suggest `--no-sign-request`.

## Guardrails

- **Never** generate or execute commands for uploads, moves, deletes, or
  permission changes without explicit per-operation authorization from the user.
- **Never** copy data across a sensitivity boundary (standard ↔ highly
  sensitive) without explicit authorization.
- **Never** expose, log, store, or include in a response: AWS credentials,
  access keys, secret keys, session tokens, pre-signed URLs, user rosters,
  or any secrets.
- Do not recommend legacy buckets as new destinations.
- Do not infer that de-identification permits moving data to standard storage.
- When you encounter a known naming or tagging inconsistency (see
  `references/paths-and-tags.md`), preserve any existing observed convention
  or ask the user to confirm — never silently pick one variant.
