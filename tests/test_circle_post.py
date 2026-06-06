from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "circle_post.py"


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_tiptap(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "title": "Dry Run Title",
                "tiptap_body": {
                    "body": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "hello",
                                        "circle_ios_fallback_text": "hello",
                                    }
                                ],
                            }
                        ],
                    },
                    "circle_ios_fallback_text": "hello",
                    "attachments": [],
                    "inline_attachments": [],
                    "sgids_to_object_map": {},
                    "format": "post",
                    "community_members": [],
                    "entities": [],
                    "group_mentions": [],
                    "polls": [],
                },
            }
        ),
        encoding="utf-8",
    )


def json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


def test_publish_dry_run_prints_payload_without_env(tmp_path: Path) -> None:
    tiptap = tmp_path / "post.tiptap.json"
    write_tiptap(tiptap)

    result = run_cli("publish", "-f", str(tiptap), "-s", "12345", "--skip-notifications", "--dry-run")
    data = json_stdout(result)

    assert data["success"] is True
    assert data["dry_run"] is True
    assert data["operation"] == "publish"
    payload = data["payload"]
    assert payload["space_id"] == 12345
    assert payload["name"] == "Dry Run Title"
    assert payload["skip_notifications"] is True
    assert payload["is_comments_enabled"] is True
    assert payload["is_liking_enabled"] is True


def test_post_dry_run_converts_markdown_without_env(tmp_path: Path) -> None:
    md = tmp_path / "post.md"
    md.write_text("# Markdown Title\n\nHello **Circle**.", encoding="utf-8")

    result = run_cli("post", "-f", str(md), "-s", "67890", "--dry-run")
    data = json_stdout(result)

    assert data["operation"] == "post"
    payload = data["payload"]
    assert payload["space_id"] == 67890
    assert payload["name"] == "Markdown Title"
    assert payload["tiptap_body"]["circle_ios_fallback_text"] == "Hello **Circle**."


def test_update_dry_run_prints_payload_without_env(tmp_path: Path) -> None:
    tiptap = tmp_path / "post.tiptap.json"
    write_tiptap(tiptap)

    result = run_cli("update", "-f", str(tiptap), "--post-id", "123", "--draft", "--dry-run")
    data = json_stdout(result)

    assert data["operation"] == "update"
    assert data["post_id"] == 123
    assert data["payload"]["status"] == "draft"
    assert "space_id" not in data["payload"]


def test_delete_dry_run_does_not_require_confirm_or_env() -> None:
    result = run_cli("delete", "--post-id", "456", "--dry-run")
    data = json_stdout(result)

    assert data["operation"] == "delete"
    assert data["payload"] == {"post_id": 456}


def test_delete_without_confirm_still_fails_when_not_dry_run() -> None:
    result = run_cli("delete", "--post-id", "456")

    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["success"] is False
    assert "--confirm" in data["error"]
