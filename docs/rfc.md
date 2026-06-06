# Circle Post CLI — RFC

## Design Summary

Circle Post is a small Python CLI for Markdown-to-Circle publishing. It intentionally keeps a reviewable TipTap JSON file between conversion and live publishing, because Markdown-to-TipTap conversion is imperfect and Circle rendering has platform-specific edge cases.

The current implementation is a single-file CLI (`circle_post.py`). That shape is acceptable for this repo's size and preserves compatibility for existing callers. A future package layout under `src/` can be introduced when the code grows beyond one file.

## CLI Surface

```bash
circle_post.py spaces
circle_post.py list-posts -s YOUR_SPACE_ID

circle_post.py convert -f article.md [-o article.tiptap.json] [--title "Title"]
circle_post.py publish -f article.tiptap.json -s YOUR_SPACE_ID [--title "Title"] [--draft] [--skip-notifications] [--dry-run]
circle_post.py update -f article.tiptap.json --post-id YOUR_POST_ID [--title "Title"] [--draft] [--skip-notifications] [--dry-run]
circle_post.py post -f article.md -s YOUR_SPACE_ID [--title "Title"] [--draft] [--skip-notifications] [--dry-run]
circle_post.py delete --post-id YOUR_POST_ID [--dry-run | --confirm]
```

`post` is a compatibility shortcut that converts Markdown and publishes in one command. Agents should prefer `convert` followed by JSON review and `publish`.

## Configuration

Circle Admin API V2 uses token authentication:

```text
Authorization: Token {CIRCLE_V2_TOKEN}
```

The CLI loads `CIRCLE_V2_TOKEN` from `.env` only for live API calls. Dry-run commands do not load `.env`.

`.env.example` contains a fake placeholder and is safe to commit.

## Intermediate JSON Format

`convert` writes:

```json
{
  "title": "Article Title",
  "tiptap_body": {
    "body": {
      "type": "doc",
      "content": []
    },
    "circle_ios_fallback_text": "Plain text fallback",
    "attachments": [],
    "inline_attachments": [],
    "sgids_to_object_map": {},
    "format": "post",
    "community_members": [],
    "entities": [],
    "group_mentions": [],
    "polls": []
  }
}
```

`publish` and `update` read this file. CLI `--title` overrides the JSON title.

## Payload Construction

Create-post payloads include:

```json
{
  "space_id": 12345,
  "name": "Article Title",
  "status": "published",
  "tiptap_body": {},
  "skip_notifications": false,
  "is_comments_enabled": true,
  "is_liking_enabled": true
}
```

Update payloads omit `space_id` and target the post ID in the URL.

## Dry-Run Design

Dry-run is implemented at the command-handler layer before credential loading and image processing. This ensures `--dry-run` can be used as a safe preflight in automated workflows.

Dry-run output includes:

```json
{
  "success": true,
  "dry_run": true,
  "operation": "publish",
  "message": "No Circle API request was sent.",
  "payload": {},
  "file": "article.tiptap.json"
}
```

This is deliberately different from a test post. A test post is a live API call that creates a real Circle post.

## Markdown Conversion

The converter is intentionally lightweight and regex-based. It supports common publishing structures:

| Markdown | TipTap output | Status |
|---|---|---|
| Headings | `heading` | Supported |
| Paragraphs | `paragraph` | Supported |
| Links | `text` + `link` mark | Supported |
| Images | `image` node | Supported |
| Bold / italic | marks | Supported |
| Blockquotes | `blockquote` | Supported |
| Horizontal rules | `horizontalRule` | Supported |
| Fenced code blocks | plain paragraph fallback | Supported as degraded output |
| Lists | list nodes | Not yet supported |

Circle rendering can be strict. Agents should inspect generated JSON and use a live test space only when visual rendering needs confirmation.

## Images

For live publish/update, image nodes are processed before calling Circle. Remote images are downloaded and uploaded through Circle direct uploads. Local relative image paths are resolved relative to the TipTap JSON file and then uploaded.

After upload, image nodes use Circle `signed_id` references and `inline_attachments`. Dry-run intentionally skips this step because uploads are external side effects.

## Safety Model

- Live publish/update/delete require explicit CLI commands.
- Delete requires `--confirm` unless `--dry-run` is used.
- Dry-run must be the default validation step before any automated side effect.
- Private space IDs and production/test routing stay outside the public repo.
