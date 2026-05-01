#!/usr/bin/env python3
"""Notify Discord about newly added solution.txt files (used by GitHub Actions on push to main)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

# Paths: "{id}. {slug}/{lang}/solution.txt"
SOLUTION_PATH = re.compile(
    r"^(?P<id>\d+)\.\s+(?P<slug>[^/]+)/(?P<lang>[^/]+)/solution\.txt$"
)

GIT_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

LANG_DISPLAY: dict[str, str] = {
    "go": "Go",
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "rust": "Rust",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "ruby": "Ruby",
    "scala": "Scala",
    "php": "PHP",
    "c": "C",
    "csharp": "C#",
    "cpp": "C++",
    "java": "Java",
    "elixir": "Elixir",
    "erlang": "Erlang",
    "dart": "Dart",
    "racket": "Racket",
    "sql": "SQL",
    "shell": "Shell",
}


def slug_to_title(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part)


def language_display(folder: str) -> str:
    key = folder.strip().lower()
    return LANG_DISPLAY.get(key, folder[:1].upper() + folder[1:] if folder else folder)


def github_blob_url(repo: str, sha: str, path: str) -> str:
    encoded = "/".join(urllib.parse.quote(segment, safe="") for segment in path.split("/"))
    return f"https://github.com/{repo}/blob/{sha}/{encoded}"


def leetcode_problem_url(slug: str) -> str:
    return f"https://leetcode.com/problems/{urllib.parse.quote(slug, safe='-')}/"


def git_added_files(before: str, after: str) -> list[str]:
    before = (before or "").strip()
    after = (after or "").strip()
    if not after:
        return []
    if not before or (len(before) == 40 and all(c == "0" for c in before)):
        before = GIT_EMPTY_TREE
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=A", before, after],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines


def discord_execute_url(webhook_base: str, thread_id: str | None) -> str:
    base = webhook_base.rstrip("/")
    if thread_id and thread_id.strip():
        join = "&" if "?" in base else "?"
        return f"{base}{join}thread_id={urllib.parse.quote(thread_id.strip(), safe='')}"
    return base


def submission_embed(
    *,
    actor: str,
    qid: str,
    title_human: str,
    lang_label: str,
    lc_url: str,
    gh_url: str,
    repo: str,
) -> dict:
    """Single Discord embed for one new solution (Execute Webhook API)."""
    return {
        "title": f"Problem {qid}: {title_human}",
        "url": lc_url,
        "description": f"**{actor}** submitted a solution in **{lang_label}**.",
        "color": 0xFFA116,
        "fields": [
            {
                "name": "LeetCode",
                "value": f"[Open problem]({lc_url})",
                "inline": True,
            },
            {
                "name": "Solution",
                "value": f"[View on GitHub]({gh_url})",
                "inline": True,
            },
        ],
        "footer": {"text": repo},
    }


def post_discord(webhook_url: str, payload: dict) -> None:
    # Cloudflare returns 403 error code: 1010 if User-Agent is missing or looks like a bare urllib client.
    repo = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
    user_agent = (
        f"DiscordBot (https://github.com/{repo}, 1.0)"
        if repo
        else "DiscordBot (https://github.com/octocat/hello-world, 1.0)"
    )
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 204):
                raise SystemExit(f"Discord returned HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Discord HTTP {e.code}: {detail}") from e


def main() -> None:
    before = os.environ.get("GIT_BEFORE", "")
    after = os.environ.get("GIT_AFTER", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    sha = os.environ.get("GITHUB_SHA", "").strip()
    actor = os.environ.get("GITHUB_ACTOR", "").strip() or "someone"
    webhook = (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip()
    thread_id = (os.environ.get("DISCORD_THREAD_ID") or "").strip() or None

    if not webhook:
        print("DISCORD_WEBHOOK_URL is not set; skipping.", file=sys.stderr)
        return
    if not repo or not sha:
        raise SystemExit("GITHUB_REPOSITORY and GITHUB_SHA must be set.")

    added = git_added_files(before, after)
    matches: list[tuple[str, str, str, str]] = []
    for path in added:
        m = SOLUTION_PATH.match(path)
        if not m:
            continue
        matches.append((path, m.group("id"), m.group("slug"), m.group("lang")))

    if not matches:
        print("No newly added solution.txt under problem folders; nothing to notify.")
        return

    webhook_url = discord_execute_url(webhook, thread_id)
    for path, qid, slug, lang_folder in matches:
        title = slug_to_title(slug)
        lang_label = language_display(lang_folder)
        gh_url = github_blob_url(repo, sha, path)
        lc_url = leetcode_problem_url(slug)
        embed = submission_embed(
            actor=actor,
            qid=qid,
            title_human=title,
            lang_label=lang_label,
            lc_url=lc_url,
            gh_url=gh_url,
            repo=repo,
        )
        post_discord(webhook_url, {"embeds": [embed]})
        print(f"Posted Discord notification for {path}")


if __name__ == "__main__":
    main()
