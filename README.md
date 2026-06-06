# Circle Post

Circle Post is a local-first CLI and agent skill for publishing Markdown articles to Circle. It converts Markdown to Circle-compatible TipTap JSON, lets a human or AI agent review the intermediate JSON, and then publishes or updates posts through Circle Admin API V2.

This repository is designed to be publishable with only fake examples. Keep real tokens, community-specific space IDs, post IDs, private domains, private article drafts, and operational runbooks outside this repo.

## Install

```bash
git clone <repo-url> circle_post
cd circle_post
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python pytest
cp .env.example .env
```

Edit `.env`:

```text
CIRCLE_V2_TOKEN=replace-with-your-circle-admin-api-token
```

## Workflow

Convert Markdown to TipTap JSON:

```bash
.venv/bin/python circle_post.py convert -f article.md
```

Review `article.md.tiptap.json`, then run a no-network dry-run:

```bash
.venv/bin/python circle_post.py publish -f article.md.tiptap.json -s YOUR_SPACE_ID --dry-run
```

Publish after review:

```bash
.venv/bin/python circle_post.py publish -f article.md.tiptap.json -s YOUR_SPACE_ID
```

Update an existing post:

```bash
.venv/bin/python circle_post.py update -f article.md.tiptap.json --post-id YOUR_POST_ID --dry-run
.venv/bin/python circle_post.py update -f article.md.tiptap.json --post-id YOUR_POST_ID
```

Delete requires explicit confirmation:

```bash
.venv/bin/python circle_post.py delete --post-id YOUR_POST_ID --dry-run
.venv/bin/python circle_post.py delete --post-id YOUR_POST_ID --confirm
```

## Dry-Run Semantics

`--dry-run` validates inputs and prints the Circle API payload. It does not load `.env`, upload images, or call Circle. It is a preflight, not a preview post. A preview/test post is still a real Circle post and should only be created in a user-controlled test space.

## Agent Skill

The canonical public skill is:

```text
skills/skill_circle_post.md
```

To install this skill into a workspace, hand this repository URL to an AI coding agent and ask it to add `skills/skill_circle_post.md` to the workspace's skill discovery chain. The installing agent should first read the target workspace's `AGENTS.md`, `CLAUDE.md`, or equivalent routing instructions.

Private defaults such as production space IDs, test space IDs, notification policy, community naming, and content routing should live in a private workspace overlay rather than this public repo.

## Test

```bash
.venv/bin/python -m pytest -q
```

The default test suite is offline and does not require `CIRCLE_V2_TOKEN`.
