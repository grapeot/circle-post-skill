#!/usr/bin/env python3
"""
circle_post.py — CLI tool for posting Markdown articles to Circle.so

Two-step workflow (recommended):
    python circle_post.py convert -f <file>                  # MD → .tiptap.json
    python circle_post.py publish -f <file.tiptap.json> -s <space_id>  # JSON → Circle post

One-step shortcuts (legacy):
    python circle_post.py spaces
    python circle_post.py post -f <file> -s <space_id> [--title <title>] [--draft] [--skip-notifications]
    python circle_post.py preview -f <file>
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

BASE_URL = "https://app.circle.so/api/admin/v2"
SCRIPT_DIR = Path(__file__).parent


def load_env():
    """Load .env from project directory."""
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


def get_token():
    """Get CIRCLE_V2_TOKEN from env."""
    token = os.environ.get("CIRCLE_V2_TOKEN")
    if not token:
        print(json.dumps({"success": False, "error": "CIRCLE_V2_TOKEN not set in .env"}))
        sys.exit(1)
    return token


def get_headers(token):
    """Return auth headers for Circle API."""
    return {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }


def list_spaces(token):
    """GET /api/admin/v2/spaces and print table of id/name/slug."""
    import requests

    url = f"{BASE_URL}/spaces"
    resp = requests.get(url, headers=get_headers(token))
    if resp.status_code != 200:
        print(json.dumps({"success": False, "error": resp.text, "status_code": resp.status_code}))
        sys.exit(1)

    data = resp.json()
    records = data.get("records", [])
    if not records:
        print("No spaces found.")
        return

    # Print table
    print(f"{'ID':<12} {'Name':<40} {'Slug'}")
    print("-" * 80)
    for space in records:
        sid = space.get("id", "")
        name = space.get("name", "")
        slug = space.get("slug", "")
        print(f"{sid:<12} {name:<40} {slug}")


def list_posts(token, space_id, per_page=50):
    """GET /api/admin/v2/posts?space_id=<id> and print table of posts."""
    import requests

    url = f"{BASE_URL}/posts"
    all_posts = []
    page = 1

    while True:
        resp = requests.get(url, headers=get_headers(token), params={
            "space_id": space_id,
            "per_page": per_page,
            "page": page,
        })
        if resp.status_code != 200:
            print(json.dumps({"success": False, "error": resp.text, "status_code": resp.status_code}))
            sys.exit(1)

        data = resp.json()
        records = data.get("records", [])
        all_posts.extend(records)

        if len(records) < per_page:
            break
        page += 1

    if not all_posts:
        print(f"No posts found in space {space_id}.")
        return

    print(f"{'ID':<12} {'Published At':<22} {'Title'}")
    print("-" * 100)
    for post in all_posts:
        pid = post.get("id", "")
        name = post.get("name", "(untitled)")
        published = post.get("published_at", "")[:19]
        print(f"{pid:<12} {published:<22} {name}")

    print(f"\nTotal: {len(all_posts)} posts")


def parse_inline(text):
    """Parse inline markdown (bold, italic, links) into TipTap inline nodes."""
    nodes = []
    # We'll process the text left to right, matching inline patterns
    # Order matters: images first, then links, then bold, then italic
    patterns = [
        ("image", re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")),
        ("link", re.compile(r"\[([^\]]+)\]\(([^)]+)\)")),
        ("bold", re.compile(r"\*\*(.+?)\*\*")),
        ("bold_underscore", re.compile(r"__(.+?)__")),
        ("italic", re.compile(r"\*(.+?)\*")),
        ("italic_underscore", re.compile(r"_(.+?)_")),
    ]

    pos = 0
    while pos < len(text):
        # Find the earliest match among all patterns
        earliest_match = None
        earliest_type = None
        earliest_pos = len(text)

        for ptype, pattern in patterns:
            m = pattern.search(text, pos)
            if m and m.start() < earliest_pos:
                earliest_pos = m.start()
                earliest_match = m
                earliest_type = ptype

        if earliest_match is None:
            # No more inline patterns, rest is plain text
            remaining = text[pos:]
            if remaining:
                nodes.append({
                    "type": "text",
                    "text": remaining,
                    "circle_ios_fallback_text": remaining,
                })
            break

        # Add plain text before this match
        if earliest_pos > pos:
            plain = text[pos:earliest_pos]
            nodes.append({
                "type": "text",
                "text": plain,
                "circle_ios_fallback_text": plain,
            })

        if earliest_type == "image":
            alt = earliest_match.group(1)
            src = earliest_match.group(2)
            nodes.append({
                "type": "image",
                "attrs": {"src": src, "alt": alt, "title": alt},
            })
        elif earliest_type == "link":
            link_text = earliest_match.group(1)
            href = earliest_match.group(2)
            nodes.append({
                "type": "text",
                "text": link_text,
                "circle_ios_fallback_text": link_text,
                "marks": [{"type": "link", "attrs": {"href": href, "target": "_blank"}}],
            })
        elif earliest_type in {"bold", "bold_underscore"}:
            bold_text = earliest_match.group(1)
            nodes.append({
                "type": "text",
                "text": bold_text,
                "circle_ios_fallback_text": bold_text,
                "marks": [{"type": "bold"}],
            })
        elif earliest_type in {"italic", "italic_underscore"}:
            italic_text = earliest_match.group(1)
            nodes.append({
                "type": "text",
                "text": italic_text,
                "circle_ios_fallback_text": italic_text,
                "marks": [{"type": "italic"}],
            })

        pos = earliest_match.end()

    return nodes


def markdown_to_tiptap(content):
    """Convert markdown text to TipTap JSON structure."""
    lines = content.split("\n")
    doc_content = []
    plain_text_parts = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Headings
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            inline_nodes = parse_inline(text)
            doc_content.append({
                "type": "heading",
                "attrs": {"level": level},
                "content": inline_nodes,
            })
            plain_text_parts.append(text)
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            quote_text = line[2:].strip()
            inline_nodes = parse_inline(quote_text)
            doc_content.append({
                "type": "blockquote",
                "content": [{
                    "type": "paragraph",
                    "content": inline_nodes,
                }],
            })
            plain_text_parts.append(quote_text)
            i += 1
            continue

        if re.match(r"^\s*([-*_])\1\1+\s*$", line):
            doc_content.append({
                "type": "horizontalRule",
            })
            plain_text_parts.append(line.strip())
            i += 1
            continue

        # Fenced code blocks — Circle frontend has no CSS for <pre><code>,
        # so codeBlock nodes are invisible. Strip fence markers and emit
        # code content as plain text so readers at least see the code
        # instead of raw ``` markers.
        fence_match = re.match(r"^(`{3,}|~{3,})(\w*)\s*$", line)
        if fence_match:
            code_lines = []
            i += 1
            while i < len(lines):
                closing = re.match(r"^(`{3,}|~{3,})\s*$", lines[i])
                if closing:
                    break
                code_lines.append(lines[i])
                i += 1
            code_text = "\n".join(code_lines).strip()
            if code_text:
                # Preserve single newlines as line breaks for readability.
                # Circle renders \n in text nodes as line breaks.
                inline_nodes = parse_inline(code_text)
                if inline_nodes:
                    doc_content.append({
                        "type": "paragraph",
                        "content": inline_nodes,
                    })
                    plain_text_parts.append(code_text)
            i += 1
            continue

        # Regular paragraph
        inline_nodes = parse_inline(line.strip())
        if inline_nodes:
            doc_content.append({
                "type": "paragraph",
                "content": inline_nodes,
            })
            plain_text_parts.append(line.strip())
        i += 1

    fallback_text = "\n".join(plain_text_parts)

    return {
        "body": {
            "type": "doc",
            "content": doc_content,
        },
        "circle_ios_fallback_text": fallback_text,
        "attachments": [],
        "inline_attachments": [],
        "sgids_to_object_map": {},
        "format": "post",
        "community_members": [],
        "entities": [],
        "group_mentions": [],
        "polls": [],
    }


def extract_frontmatter(content):
    """Extract YAML frontmatter from content. Returns (frontmatter_dict, body_content)."""
    if not content.startswith("---"):
        return {}, content

    end = content.find("---", 3)
    if end == -1:
        return {}, content

    fm_text = content[3:end].strip()
    body = content[end + 3:].lstrip("\n")

    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()

    return fm, body


def extract_title(content, filepath, cli_title=None):
    """
    Extract title from CLI arg > frontmatter > first # heading > filename.
    Returns (title, body_without_title).
    """
    if cli_title:
        # Even when title is provided via CLI, strip leading H1 from body
        # to avoid duplicate title in Circle (which renders title as H1 separately).
        first_line = content.split("\n", 1)[0] if content else ""
        if re.match(r"^#\s+.+$", first_line.strip()):
            content = content.split("\n", 1)[1] if "\n" in content else ""
        return cli_title, content

    # Check frontmatter
    fm, body = extract_frontmatter(content)
    if fm.get("title"):
        return fm["title"], body

    # Check first # heading
    lines = content.split("\n")
    for idx, line in enumerate(lines):
        m = re.match(r"^#\s+(.+)$", line)
        if m:
            title = m.group(1).strip()
            # Remove this line from body
            remaining = "\n".join(lines[idx + 1:])
            return title, remaining

    # Fallback: filename
    title = Path(filepath).stem
    return title, content


def _upload_local_file(token, local_path):
    import requests
    import base64
    import hashlib
    import mimetypes

    if not os.path.exists(local_path):
        return None

    file_size = os.path.getsize(local_path)
    file_name = os.path.basename(local_path)
    content_type = mimetypes.guess_type(local_path)[0] or "image/png"

    with open(local_path, "rb") as f:
        file_content = f.read()
        checksum = base64.b64encode(hashlib.md5(file_content).digest()).decode("utf-8")

    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    upload_resp = requests.post(
        f"{BASE_URL}/direct_uploads",
        headers=headers,
        json={"blob": {
            "filename": file_name,
            "byte_size": file_size,
            "checksum": checksum,
            "content_type": content_type,
            "metadata": {"identified": True},
        }},
    )
    if upload_resp.status_code != 200:
        print(f"  [warn] direct_upload create failed ({upload_resp.status_code}): {upload_resp.text[:200]}")
        return None

    upload_data = upload_resp.json()

    with open(local_path, "rb") as f:
        put_resp = requests.put(
            upload_data["direct_upload"]["url"],
            headers=upload_data["direct_upload"]["headers"],
            data=f,
        )
    if put_resp.status_code not in (200, 204):
        print(f"  [warn] storage PUT failed ({put_resp.status_code})")
        return None

    return {
        "signed_id": upload_data["signed_id"],
        "url": upload_data["url"],
        "filename": file_name,
        "content_type": content_type,
        "byte_size": file_size,
    }


def upload_image_to_circle(token, image_url):
    import requests
    import tempfile

    resp = requests.get(image_url, timeout=30)
    if resp.status_code != 200:
        return None

    ext = os.path.splitext(image_url.split("?")[0])[1] or ".png"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    try:
        return _upload_local_file(token, tmp_path)
    finally:
        os.unlink(tmp_path)


def _resolve_local_image(src, json_file_path):
    if src.startswith("http") or src.startswith("/"):
        return None
    base_dir = os.path.dirname(json_file_path) if json_file_path else "."
    candidate = os.path.join(base_dir, src)
    if os.path.exists(candidate):
        return candidate
    assets_candidate = os.path.join(base_dir, "assets", os.path.basename(src))
    if os.path.exists(assets_candidate):
        return assets_candidate
    return None


def _process_nodes(token, nodes, inline_attachments, json_file_path=None):
    for node in nodes:
        if node.get("type") == "image":
            src = node.get("attrs", {}).get("src", "")
            result = None
            if src.startswith("http"):
                result = upload_image_to_circle(token, src)
            elif src:
                local_path = _resolve_local_image(src, json_file_path)
                if local_path:
                    result = _upload_local_file(token, local_path)
                else:
                    print(f"  [warn] Local image not found: {src}")
            if result:
                if result:
                    signed_id = result.get("signed_id")
                    if not isinstance(signed_id, str):
                        print(f"  [warn] Missing signed_id after upload: {src[:80]}")
                        continue
                    node["attrs"] = {
                        "url": None,
                        "href": None,
                        "width": None,
                        "alignment": "center",
                        "signed_id": signed_id,
                    }
                    inline_attachments.append({
                        "filename": result["filename"],
                        "content_type": result["content_type"],
                        "metadata": {"identified": True, "analyzed": True},
                        "byte_size": result["byte_size"],
                        "signed_id": signed_id,
                        "type": "file",
                        "url": result["url"],
                    })
                    print(f"  Uploaded: {src[:60]}... → signed_id: {signed_id[:30]}...")
                else:
                    print(f"  [warn] Failed to upload: {src[:80]}")
        if "content" in node:
            _process_nodes(token, node["content"], inline_attachments, json_file_path)


def process_images_in_tiptap(token, tiptap_body, json_file_path=None):
    inline_attachments = []
    top_nodes = tiptap_body.get("body", {}).get("content", [])
    _process_nodes(token, top_nodes, inline_attachments, json_file_path)
    if inline_attachments:
        tiptap_body["inline_attachments"] = inline_attachments
    return tiptap_body


def create_post(token, space_id, title, tiptap_body, status="published", skip_notifications=False):
    """POST /api/admin/v2/posts and return result dict."""
    import requests

    url = f"{BASE_URL}/posts"
    payload = build_post_payload(space_id, title, tiptap_body, status=status, skip_notifications=skip_notifications)

    resp = requests.post(url, headers=get_headers(token), json=payload)
    if resp.status_code not in (200, 201):
        return {
            "success": False,
            "error": resp.text,
            "status_code": resp.status_code,
        }

    data = resp.json()
    post = data.get("post", data)  # some APIs nest under "post"
    return {
        "success": True,
        "post_id": post.get("id"),
        "title": post.get("name", title),
        "url": post.get("url"),
        "space_id": space_id,
        "status": post.get("status", status),
    }


def update_post(token, post_id, title, tiptap_body, status="published", skip_notifications=False):
    import requests

    url = f"{BASE_URL}/posts/{post_id}"
    payload = build_update_payload(title, tiptap_body, status=status, skip_notifications=skip_notifications)

    resp = requests.put(url, headers=get_headers(token), json=payload)
    if resp.status_code not in (200, 201):
        return {
            "success": False,
            "error": resp.text,
            "status_code": resp.status_code,
        }

    data = resp.json()
    post = data.get("post", data)
    return {
        "success": True,
        "post_id": post.get("id", post_id),
        "title": post.get("name", title),
        "url": post.get("url"),
        "space_id": post.get("space_id"),
        "status": post.get("status", status),
    }


def build_post_payload(space_id, title, tiptap_body, status="published", skip_notifications=False):
    return {
        "space_id": int(space_id),
        "name": title,
        "status": status,
        "tiptap_body": tiptap_body,
        "skip_notifications": skip_notifications,
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }


def build_update_payload(title, tiptap_body, status="published", skip_notifications=False):
    return {
        "name": title,
        "status": status,
        "tiptap_body": tiptap_body,
        "skip_notifications": skip_notifications,
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }


def dry_run_result(operation, payload, **extra):
    return {
        "success": True,
        "dry_run": True,
        "operation": operation,
        "message": "No Circle API request was sent.",
        "payload": payload,
        **extra,
    }


def preview_post(filepath):
    """Parse MD file and print TipTap JSON (dry run)."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    title, body = extract_title(content, filepath)
    tiptap = markdown_to_tiptap(body)

    print(f"Title: {title}\n")
    print("TipTap JSON:")
    print(json.dumps(tiptap, ensure_ascii=False, indent=2))


# ── Command handlers ──────────────────────────────────────────────────────────

def cmd_spaces(args):
    load_env()
    token = get_token()
    list_spaces(token)


def cmd_list_posts(args):
    load_env()
    token = get_token()
    list_posts(token, args.space_id, per_page=args.per_page)


def strip_title_heading_from_body(tiptap_body, title):
    """Remove the first heading node from body if its text matches the title.
    
    Circle renders the title field as H1 separately. If the body's first
    node is a heading with identical text, it creates a visual duplicate.
    This function strips that first heading regardless of its level.
    """
    content = tiptap_body.get("body", {}).get("content", [])
    if not content or not title:
        return tiptap_body

    first = content[0]
    if first.get("type") != "heading":
        return tiptap_body

    heading_text = ""
    for node in first.get("content", []):
        if node.get("type") == "text":
            heading_text += node.get("text", "")

    if heading_text.strip() == title.strip():
        content.pop(0)

    return tiptap_body


def cmd_convert(args):
    """Convert a Markdown file to .tiptap.json."""
    filepath = args.file
    if not os.path.exists(filepath):
        print(json.dumps({"success": False, "error": f"File not found: {filepath}"}))
        sys.exit(1)

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    title, body = extract_title(content, filepath, cli_title=args.title)
    tiptap = markdown_to_tiptap(body)
    strip_title_heading_from_body(tiptap, title)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = str(filepath) + ".tiptap.json"

    output_data = {
        "title": title,
        "tiptap_body": tiptap,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Converted: {filepath} → {output_path}")
    print(f"Title: {title}")


def cmd_publish(args):
    """Publish a .tiptap.json file to a Circle space."""
    filepath = args.file
    if not os.path.exists(filepath):
        print(json.dumps({"success": False, "error": f"File not found: {filepath}"}))
        sys.exit(1)

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    title = args.title if args.title else data.get("title")
    tiptap_body = data.get("tiptap_body")

    if not title:
        print(json.dumps({"success": False, "error": "No title found in JSON or CLI args"}))
        sys.exit(1)
    if not tiptap_body:
        print(json.dumps({"success": False, "error": "No tiptap_body found in JSON file"}))
        sys.exit(1)

    status = "draft" if args.draft else "published"
    skip_notifs = args.skip_notifications

    if args.dry_run:
        payload = build_post_payload(args.space_id, title, tiptap_body, status=status, skip_notifications=skip_notifs)
        print(json.dumps(dry_run_result("publish", payload, file=filepath), ensure_ascii=False, indent=2))
        return

    load_env()
    token = get_token()

    print("Processing images...")
    tiptap_body = process_images_in_tiptap(token, tiptap_body, json_file_path=filepath)

    result = create_post(token, args.space_id, title, tiptap_body, status=status, skip_notifications=skip_notifs)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("success") and result.get("url"):
        print(f"\nPost URL: {result['url']}")

    if not result.get("success"):
        sys.exit(1)


def cmd_update(args):
    filepath = args.file
    if not os.path.exists(filepath):
        print(json.dumps({"success": False, "error": f"File not found: {filepath}"}))
        sys.exit(1)

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    title = args.title if args.title else data.get("title")
    tiptap_body = data.get("tiptap_body")

    if not title:
        print(json.dumps({"success": False, "error": "No title found in JSON or CLI args"}))
        sys.exit(1)
    if not tiptap_body:
        print(json.dumps({"success": False, "error": "No tiptap_body found in JSON file"}))
        sys.exit(1)

    status = "draft" if args.draft else "published"
    skip_notifs = args.skip_notifications

    if args.dry_run:
        payload = build_update_payload(title, tiptap_body, status=status, skip_notifications=skip_notifs)
        print(json.dumps(dry_run_result("update", payload, file=filepath, post_id=args.post_id), ensure_ascii=False, indent=2))
        return

    load_env()
    token = get_token()

    print("Processing images...")
    tiptap_body = process_images_in_tiptap(token, tiptap_body, json_file_path=filepath)

    result = update_post(token, args.post_id, title, tiptap_body, status=status, skip_notifications=skip_notifs)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("success") and result.get("url"):
        print(f"\nPost URL: {result['url']}")

    if not result.get("success"):
        sys.exit(1)


def cmd_post(args):
    """Legacy one-step: convert MD + publish in one command."""
    filepath = args.file
    if not os.path.exists(filepath):
        print(json.dumps({"success": False, "error": f"File not found: {filepath}"}))
        sys.exit(1)

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    title, body = extract_title(content, filepath, cli_title=args.title)
    tiptap = markdown_to_tiptap(body)

    status = "draft" if args.draft else "published"
    skip_notifs = args.skip_notifications

    if args.dry_run:
        payload = build_post_payload(args.space_id, title, tiptap, status=status, skip_notifications=skip_notifs)
        print(json.dumps(dry_run_result("post", payload, file=filepath), ensure_ascii=False, indent=2))
        return

    load_env()
    token = get_token()

    result = create_post(token, args.space_id, title, tiptap, status=status, skip_notifications=skip_notifs)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("success") and result.get("url"):
        print(f"\nPost URL: {result['url']}")

    if not result.get("success"):
        sys.exit(1)


def delete_post(token, post_id):
    """DELETE /api/admin/v2/posts/{post_id} and return result dict."""
    import requests

    url = f"{BASE_URL}/posts/{post_id}"
    resp = requests.delete(url, headers=get_headers(token))
    if resp.status_code not in (200, 204):
        return {
            "success": False,
            "error": resp.text,
            "status_code": resp.status_code,
        }
    return {
        "success": True,
        "post_id": post_id,
        "message": f"Post {post_id} deleted",
    }


def cmd_delete(args):
    """Delete a post by ID. Requires --confirm flag for safety."""
    if args.dry_run:
        print(json.dumps(dry_run_result("delete", {"post_id": args.post_id}), ensure_ascii=False, indent=2))
        return

    if not args.confirm:
        print(json.dumps({
            "success": False,
            "error": "Deletion requires --confirm flag. Usage: python circle_post.py delete --post-id <id> --confirm"
        }))
        sys.exit(1)

    load_env()
    token = get_token()
    result = delete_post(token, args.post_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("success"):
        sys.exit(1)


def cmd_preview(args):
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)
    preview_post(filepath)


def main():
    parser = argparse.ArgumentParser(
        description="CLI tool for posting Markdown articles to Circle.so"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # spaces
    subparsers.add_parser("spaces", help="List all spaces")

    # list-posts
    list_posts_parser = subparsers.add_parser(
        "list-posts", help="List posts in a space"
    )
    list_posts_parser.add_argument("-s", "--space-id", required=True, type=int, help="Space ID")
    list_posts_parser.add_argument("-n", "--per-page", type=int, default=50, help="Posts per page (default: 50)")

    # convert
    convert_parser = subparsers.add_parser(
        "convert", help="Convert a Markdown file to .tiptap.json (step 1)"
    )
    convert_parser.add_argument("-f", "--file", required=True, help="Markdown file path")
    convert_parser.add_argument(
        "-o", "--output", default=None,
        help="Output JSON file path (default: <input>.tiptap.json)"
    )
    convert_parser.add_argument("-t", "--title", default=None, help="Override post title")

    # publish
    publish_parser = subparsers.add_parser(
        "publish", help="Publish a .tiptap.json file to Circle (step 2)"
    )
    publish_parser.add_argument("-f", "--file", required=True, help=".tiptap.json file path")
    publish_parser.add_argument("-s", "--space-id", required=True, type=int, help="Target space ID")
    publish_parser.add_argument("-t", "--title", default=None, help="Override title from JSON")
    publish_parser.add_argument("--draft", action="store_true", help="Create as draft")
    publish_parser.add_argument(
        "--skip-notifications", action="store_true", help="Skip notifications"
    )
    publish_parser.add_argument("--dry-run", action="store_true", help="Validate input and print Circle API payload without sending")

    update_parser = subparsers.add_parser(
        "update", help="Update an existing Circle post from a .tiptap.json file"
    )
    update_parser.add_argument("-f", "--file", required=True, help=".tiptap.json file path")
    update_parser.add_argument("--post-id", required=True, type=int, help="Existing Circle post ID")
    update_parser.add_argument("-t", "--title", default=None, help="Override title from JSON")
    update_parser.add_argument("--draft", action="store_true", help="Update as draft")
    update_parser.add_argument(
        "--skip-notifications", action="store_true", help="Skip notifications"
    )
    update_parser.add_argument("--dry-run", action="store_true", help="Validate input and print Circle API payload without sending")

    # post (legacy one-step)
    post_parser = subparsers.add_parser(
        "post", help="[Legacy] Convert + publish in one step"
    )
    post_parser.add_argument("-f", "--file", required=True, help="Markdown file path")
    post_parser.add_argument("-s", "--space-id", required=True, type=int, help="Target space ID")
    post_parser.add_argument("-t", "--title", default=None, help="Override post title")
    post_parser.add_argument("--draft", action="store_true", help="Create as draft")
    post_parser.add_argument(
        "--skip-notifications", action="store_true", help="Skip notifications"
    )
    post_parser.add_argument("--dry-run", action="store_true", help="Convert input and print Circle API payload without sending")

    # preview (legacy dry run)
    preview_parser = subparsers.add_parser("preview", help="Preview TipTap JSON (dry run)")
    preview_parser.add_argument("-f", "--file", required=True, help="Markdown file path")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a post by ID")
    delete_parser.add_argument("--post-id", required=True, type=int, help="Post ID to delete")
    delete_parser.add_argument(
        "--confirm", action="store_true",
        help="Required safety flag to confirm deletion"
    )
    delete_parser.add_argument("--dry-run", action="store_true", help="Print the delete target without sending a DELETE request")

    args = parser.parse_args()

    if args.command == "spaces":
        cmd_spaces(args)
    elif args.command == "list-posts":
        cmd_list_posts(args)
    elif args.command == "convert":
        cmd_convert(args)
    elif args.command == "publish":
        cmd_publish(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "post":
        cmd_post(args)
    elif args.command == "preview":
        cmd_preview(args)
    elif args.command == "delete":
        cmd_delete(args)


if __name__ == "__main__":
    main()
