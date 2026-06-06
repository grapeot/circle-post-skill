# Circle Post — Working Log

## Changelog

### 2026-06-05

- Prepared the repository for public release: added README, AGENTS, `.env.example`, GitHub Actions, and a repo-local canonical skill.
- Split public skill responsibilities from private workspace defaults.
- Rewrote PRD, RFC, and test docs with fake examples and generic Circle terminology.
- Added `--dry-run` to `publish`, `post`, `update`, and `delete`.
- Added offline pytest coverage for dry-run payloads and delete safety behavior.

## Lessons Learned

- Circle Admin API V2 uses `Authorization: Token ...`, not Bearer authentication.
- API-created posts may need explicit `is_comments_enabled` and `is_liking_enabled` fields when the caller expects those interactions to be enabled.
- Circle TipTap image nodes need uploaded asset references. Direct-upload results should be represented with `signed_id` and `inline_attachments` rather than raw external `src` URLs.
- Local image paths should be relative to the generated TipTap JSON file. Absolute local paths are not portable and should not appear in public examples.
- Some TipTap code formatting structures are accepted by the API but render poorly or inconsistently in Circle clients. Degrading fenced code blocks to readable plain text is often safer than emitting invisible or unstyled code blocks.
- Dry-run and test posts are different. Dry-run constructs payloads and does not call Circle; test posts are real external side effects.
