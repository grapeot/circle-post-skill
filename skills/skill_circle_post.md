# Circle Post Skill

## When To Use

Use this skill when a user asks you to convert Markdown into a Circle post, publish a reviewed TipTap JSON file, update an existing Circle post, list spaces/posts, or safely delete a Circle post.

This public skill is generic. Private community names, real space IDs, production/test routing, notification policy, and local publishing runbooks belong in the user's private workspace overlay.

## Prerequisites

- Working directory: repository root, alongside `circle_post.py`
- Python environment: project `.venv/` created with `uv`
- Dependencies installed with `uv pip install --python .venv/bin/python -r requirements.txt`
- `.env` configured with `CIRCLE_V2_TOKEN` for real Circle API calls

Dry-run commands do not require `.env` or network access.

## Commands

All commands run from the project root.

```bash
.venv/bin/python circle_post.py convert -f article.md
.venv/bin/python circle_post.py convert -f article.md -o article.tiptap.json --title "Article Title"

.venv/bin/python circle_post.py publish -f article.md.tiptap.json -s YOUR_SPACE_ID --dry-run
.venv/bin/python circle_post.py publish -f article.md.tiptap.json -s YOUR_SPACE_ID

.venv/bin/python circle_post.py update -f article.md.tiptap.json --post-id YOUR_POST_ID --dry-run
.venv/bin/python circle_post.py update -f article.md.tiptap.json --post-id YOUR_POST_ID

.venv/bin/python circle_post.py post -f article.md -s YOUR_SPACE_ID --dry-run
.venv/bin/python circle_post.py spaces
.venv/bin/python circle_post.py list-posts -s YOUR_SPACE_ID
.venv/bin/python circle_post.py delete --post-id YOUR_POST_ID --dry-run
.venv/bin/python circle_post.py delete --post-id YOUR_POST_ID --confirm
```

## Workflow

Prefer the two-step workflow for production publishing: `convert`, human/agent review of the generated JSON, `publish --dry-run`, then live `publish`.

Use `post --dry-run` only as a quick smoke check. The one-step `post` command is kept for compatibility, but the intermediate JSON review is safer for real publishing.

## Dry-Run Contract

`--dry-run` validates the input and prints the outgoing Circle API payload. It does not load `.env`, upload images, or call Circle. Dry-run is a preflight; it is not a test post.

Use dry-run before every automated or scheduled Circle side effect. If a user asks for a visual preview, create a live post only in a user-designated test space and wait for confirmation before publishing to a production space.

## Safety Rules

- Never publish or update a live Circle post before reviewing the generated TipTap JSON.
- Always run `--dry-run` before live publish, update, or delete.
- Treat test posts as real external side effects.
- Delete only when the user explicitly confirms the exact post ID.
- Keep `.env`, generated TipTap JSON for private drafts, screenshots, and operational logs out of git.
- Do not put real space IDs, post IDs, private community names, or private article titles in this public repo.

## Output Contract

Dry-run returns JSON like:

```json
{
  "success": true,
  "dry_run": true,
  "operation": "publish",
  "message": "No Circle API request was sent.",
  "payload": {
    "space_id": 12345,
    "name": "Article Title",
    "status": "published",
    "skip_notifications": false,
    "is_comments_enabled": true,
    "is_liking_enabled": true,
    "tiptap_body": {}
  },
  "file": "article.md.tiptap.json"
}
```

Live publish/update returns Circle API success/failure JSON. On failure, the CLI includes the HTTP status code and response body when available.

## Acceptance Criteria

A Circle publishing task is complete when:

1. The Markdown was converted to TipTap JSON.
2. The generated JSON was reviewed for title, links, images, and obvious conversion errors.
3. `publish --dry-run` or `update --dry-run` succeeded and the payload matched the intended target.
4. A live publish/update/delete was performed only after explicit user intent.
5. The final post URL or dry-run payload was reported back to the user.
