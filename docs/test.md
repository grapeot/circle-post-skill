# Circle Post CLI — Test Plan

## Test Layers

Default tests are offline. They must not require `CIRCLE_V2_TOKEN`, network access, or a real Circle community.

Live Circle validation is manual by default because it creates or updates real community posts. When live validation is necessary, use a user-controlled test space, pass `--skip-notifications` when appropriate, and record only generic lessons in public docs.

## Commands

```bash
.venv/bin/python -m pytest -q
.venv/bin/python circle_post.py publish -f sample.tiptap.json -s YOUR_SPACE_ID --dry-run
```

## Coverage Areas

- `publish --dry-run` reads TipTap JSON and prints the create-post payload without reading `.env` or sending a request.
- `post --dry-run` converts Markdown and prints the create-post payload without sending a request.
- `update --dry-run` prints the update payload without sending a request.
- `delete --dry-run` prints the target post ID without requiring `--confirm` or sending a request.
- Non-dry-run `delete` still requires `--confirm`.
- Image upload remains live-only; dry-run intentionally does not upload local or remote images.

## Safety Notes

Dry-run is a preflight, not a preview post. It should be the default validation step before automated Circle operations. Preview/test posts remain a separate live workflow and require explicit user intent.
