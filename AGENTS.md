# Circle Post

## What This Repo Is

This repository contains a publishable local-first CLI and agent skill for converting Markdown into Circle-compatible TipTap JSON and publishing it through Circle Admin API V2.

The public repo owns generic mechanics: conversion, dry-run payload validation, publish, update, delete, tests, and the canonical agent skill. Private community names, production space IDs, notification policy, content routing, and operational runbooks belong in a private workspace overlay.

## Working Environment

Use the project `.venv` managed by `uv`.

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python pytest
.venv/bin/python -m pytest -q
```

Do not commit `.env`, converted article JSON, generated content, logs, local data, screenshots, or real Circle post exports. Use `.env.example` for fake configuration examples.

## Public Repo Privacy

This repository is intended to be public. Keep examples synthetic and generic. Do not add real Circle tokens, real community names, real space IDs, real post IDs, private local paths, private domains, private article titles, operational logs, or workspace-specific publishing defaults.

The public canonical skill is `skills/skill_circle_post.md`. Workspace-specific defaults should live in the user's private skill/config layer.

## Testing And Docs

After CLI behavior changes, run the offline pytest suite and update `docs/prd.md`, `docs/rfc.md`, `docs/test.md`, `docs/working.md`, and `skills/skill_circle_post.md` when their contracts change.
