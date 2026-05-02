#!/usr/bin/env python3
"""LeetCode submission fetcher: default = recent AC batch import; --manual = slug-based single save.
Requires: pip install requests python-dotenv"""

import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql/"
RECENT_AC_LIMIT = 20

# Manual flow only: defaults for questionSubmissionList (edit as needed).
VARIABLES = {
    "questionSlug": "longest-common-prefix",
    "offset": 0,
    "limit": 20,
    "lastKey": None,
}

SUBMISSION_LIST_QUERY = """
query submissionList($offset: Int!, $limit: Int!, $lastKey: String, $questionSlug: String!, $lang: Int, $status: Int) {
  questionSubmissionList(
    offset: $offset
    limit: $limit
    lastKey: $lastKey
    questionSlug: $questionSlug
    lang: $lang
    status: $status
  ) {
    lastKey
    hasNext
    submissions {
      id
      title
      titleSlug
      status
      statusDisplay
      lang
      langName
    }
  }
}
"""

RECENT_AC_QUERY = """
query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
  }
}
"""

SUBMISSION_DETAILS_QUERY = """
query submissionDetails($submissionId: Int!) {
  submissionDetails(submissionId: $submissionId) {
    runtime
    runtimeDisplay
    runtimePercentile
    runtimeDistribution
    memory
    memoryDisplay
    memoryPercentile
    memoryDistribution
    code
    timestamp
    statusCode
    user {
      username
      profile {
        realName
        userAvatar
      }
    }
    lang {
      name
      verboseName
    }
    question {
      questionId
      titleSlug
      hasFrontendPreview
    }
    notes
    flagType
    topicTags {
      tagId
      slug
      name
    }
  }
}
"""


def load_cookie_from_dotenv() -> str:
    """Load .env next to this script; require COOKIE (e.g. LEETCODE_SESSION=...)."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        raise SystemExit(f"Missing {env_path}: add COOKIE=...")
    load_dotenv(env_path)
    cookie = (os.getenv("COOKIE") or "").strip()
    if not cookie:
        raise SystemExit("COOKIE is missing or empty after loading .env.")
    return cookie


def build_request_headers(cookie: str) -> dict:
    """Minimal headers for LeetCode GraphQL (session via Cookie only)."""
    return {
        "Content-Type": "application/json",
        "Cookie": cookie,
    }


def graphql_post(
    query: str,
    variables: dict,
    headers: dict,
    operation_name: str | None = None,
) -> dict:
    body: dict = {"query": query, "variables": variables}
    if operation_name:
        body["operationName"] = operation_name
    response = requests.post(
        LEETCODE_GRAPHQL_URL,
        json=body,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise SystemExit(json.dumps(payload["errors"], indent=2, default=str))
    return payload


def find_latest_accepted_submission_id(payload: dict) -> int:
    submissions = (
        payload.get("data", {})
        .get("questionSubmissionList", {})
        .get("submissions")
        or []
    )
    for submission in submissions:
        if submission.get("status") == 10:
            return int(submission["id"])
    raise SystemExit("No accepted submission (status=10) found in the current page.")


def language_folder_and_extension(language_name: str) -> tuple[str, str]:
    normalized = (language_name or "").strip().lower()
    if normalized in {"go", "golang"}:
        return "go", ".go"
    if normalized in {"python", "python3"}:
        return "python", ".py"
    if normalized in {"javascript", "js"}:
        return "javascript", ".js"
    if normalized in {"typescript", "ts"}:
        return "typescript", ".ts"
    if normalized in {"rust"}:
        return "rust", ".rs"
    if normalized in {"kotlin"}:
        return "kotlin", ".kt"
    if normalized in {"swift"}:
        return "swift", ".swift"
    if normalized in {"ruby"}:
        return "ruby", ".rb"
    if normalized in {"scala"}:
        return "scala", ".scala"
    if normalized in {"php"}:
        return "php", ".php"
    if normalized in {"c"}:
        return "c", ".c"
    if normalized in {"c#"}:
        return "csharp", ".cs"
    if normalized in {"cpp", "c++"}:
        return "cpp", ".cpp"
    if normalized in {"java"}:
        return "java", ".java"
    if normalized in {"elixir"}:
        return "elixir", ".ex"
    if normalized in {"erlang"}:
        return "erlang", ".erl"
    if normalized in {"dart"}:
        return "dart", ".dart"
    if normalized in {"racket"}:
        return "racket", ".rkt"
    if normalized in {"mysql", "mssql", "oraclesql", "postgresql"}:
        return "sql", ".sql"
    if normalized in {"bash", "shell", "sh"}:
        return "shell", ".sh"
    return (normalized or "unknown"), ".txt"


def solution_path_and_code_from_details(
    details_payload: dict, base_dir: Path
) -> tuple[Path, str, str]:
    """Return (solution_file_path, problem_label, code) from a submissionDetails response."""
    details = details_payload.get("data", {}).get("submissionDetails") or {}
    code = details.get("code")
    if code is None:
        raise SystemExit("Submission details response does not include code.")

    question = details.get("question") or {}
    question_id = str(question.get("questionId") or "").strip()
    title_slug = str(question.get("titleSlug") or "").strip()
    if not question_id or not title_slug:
        raise SystemExit("Submission details response does not include questionId/titleSlug.")

    lang = details.get("lang") or {}
    language_name = str(lang.get("name") or "").strip()
    language_folder, _ = language_folder_and_extension(language_name)

    solution_file = base_dir / f"{question_id}. {title_slug}" / language_folder / "solution.txt"
    label = f"{question_id}. {title_slug}"
    return solution_file, label, code


def run_manual_flow(headers: dict, base_dir: Path) -> None:
    question_slug = input(f"questionSlug [{VARIABLES['questionSlug']}]: ").strip()
    variables = dict(VARIABLES)
    if question_slug:
        variables["questionSlug"] = question_slug

    submission_list_payload = graphql_post(SUBMISSION_LIST_QUERY, variables, headers)
    latest_accepted_submission_id = find_latest_accepted_submission_id(
        submission_list_payload
    )

    details_payload = graphql_post(
        SUBMISSION_DETAILS_QUERY,
        {"submissionId": latest_accepted_submission_id},
        headers,
    )
    solution_file, _, code = solution_path_and_code_from_details(details_payload, base_dir)
    solution_file.parent.mkdir(parents=True, exist_ok=True)
    solution_file.write_text(code, encoding="utf-8")
    print(f"Saved: {solution_file}")


def run_recent_flow(headers: dict, base_dir: Path) -> None:
    username = (os.getenv("LEETCODE_USERNAME") or "").strip()
    if not username:
        raise SystemExit(
            "LEETCODE_USERNAME is required for the default (recent AC) flow. "
            "Add it to .env (e.g. LEETCODE_USERNAME=YourHandle) or use --manual."
        )

    recent_payload = graphql_post(
        RECENT_AC_QUERY,
        {"username": username, "limit": RECENT_AC_LIMIT},
        headers,
        operation_name="recentAcSubmissions",
    )
    recent_list = (
        recent_payload.get("data", {}).get("recentAcSubmissionList") or []
    )
    if not recent_list:
        print("No recent AC submissions returned.")
        return

    inserted: list[str] = []
    # API order is newest-first; stop when target solution.txt already exists.
    for entry in recent_list:
        submission_id = int(entry["id"])
        details_payload = graphql_post(
            SUBMISSION_DETAILS_QUERY,
            {"submissionId": submission_id},
            headers,
        )
        solution_file, label, code = solution_path_and_code_from_details(
            details_payload, base_dir
        )
        if solution_file.exists():
            break
        solution_file.parent.mkdir(parents=True, exist_ok=True)
        solution_file.write_text(code, encoding="utf-8")
        inserted.append(label)

    if inserted:
        print("Newly inserted problems:")
        for item in inserted:
            print(f"  - {item}")
    else:
        print("No new problems inserted (first candidate already on disk or empty list).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import LeetCode solutions: default = recent AC batch; --manual = one slug."
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Prompt for questionSlug and import one accepted solution via questionSubmissionList.",
    )
    args = parser.parse_args()

    cookie = load_cookie_from_dotenv()
    headers = build_request_headers(cookie)
    base_dir = Path(__file__).resolve().parent

    if args.manual:
        run_manual_flow(headers, base_dir)
    else:
        run_recent_flow(headers, base_dir)


if __name__ == "__main__":
    main()
