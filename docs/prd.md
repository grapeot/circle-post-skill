# Circle Post CLI — PRD

## Problem

Circle communities often need content published from Markdown sources. Manual copy/paste through the Circle editor is slow and unreliable for AI-assisted workflows because formatting, links, images, and titles can drift between the Markdown source and the final post.

Circle Post provides a local CLI that converts Markdown to Circle-compatible TipTap JSON, lets a human or AI agent review that intermediate JSON, and then publishes or updates posts through Circle Admin API V2.

## Goals

- Convert Markdown articles into TipTap JSON files that Circle can accept.
- Keep a reviewable intermediate `.tiptap.json` file between conversion and live publishing.
- Publish a reviewed TipTap JSON file to a caller-provided Circle space ID.
- Update existing posts by caller-provided post ID.
- Delete posts only behind an explicit confirmation flag.
- Provide `--dry-run` for no-network payload validation before live side effects.
- Keep credentials in local `.env` and out of git.
- Provide a public canonical agent skill with generic instructions.

## Non-Goals

- This is not a full Circle admin dashboard.
- It does not manage members, courses, automations, spaces, permissions, or analytics.
- It does not provide scheduling. Use an external scheduler to invoke the CLI if needed.
- It does not define private production/test space IDs. Those belong in a private workspace overlay.
- It does not guarantee perfect Markdown rendering. The intermediate JSON review step is part of the product contract.

## Users

- Content authors who draft in Markdown and publish to Circle.
- AI agents that need a predictable local tool for Circle publishing workflows.
- Developers maintaining community publishing automation.

## Core Workflow

The preferred workflow is:

1. Convert Markdown to TipTap JSON.
2. Review and, if necessary, edit the generated JSON.
3. Run `publish --dry-run` to inspect the outgoing payload.
4. Run live `publish` only after the payload and target space are correct.

This split is intentional. Markdown to TipTap conversion is lossy for some structures, so the tool should expose the intermediate representation instead of hiding it behind a one-shot publish path.

## Dry-Run Requirements

Dry-run must be safe to run without credentials or network access. For `publish`, `post`, `update`, and `delete`, `--dry-run` must:

- validate required inputs;
- build the outgoing payload;
- print JSON containing `dry_run: true`;
- avoid loading `.env`;
- avoid uploading images;
- avoid calling Circle.

Dry-run is not a preview post. A test/preview post is still a live Circle side effect and should only happen in a user-designated test space.

## Success Criteria

- `convert` extracts the intended title and writes a valid TipTap JSON file.
- `publish --dry-run` prints a create-post payload without requiring `CIRCLE_V2_TOKEN`.
- `post --dry-run`, `update --dry-run`, and `delete --dry-run` are offline-safe.
- Live publish/update/delete paths report Circle API failures with enough status/body detail to debug.
- Offline tests cover dry-run behavior and delete safety.
- Public docs and examples contain only fake space IDs, fake tokens, and generic community names.
