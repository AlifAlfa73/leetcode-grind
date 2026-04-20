#!/usr/bin/env python3
"""Query LeetCode submission list via GraphQL using requests. Requires: pip install requests python-dotenv"""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql/"

# Everything except the GraphQL document is fixed here; edit as needed.
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
    """Read COOKIE via python-dotenv from .env next to this script (e.g. COOKIE=LEETCODE_SESSION=...)."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        raise SystemExit(f"Missing {env_path}: add COOKIE=...")
    load_dotenv(env_path)
    cookie = (os.getenv("COOKIE") or "").strip()
    if not cookie:
        raise SystemExit("COOKIE is missing or empty after loading .env.")
    return cookie


def graphql_post(query: str, variables: dict, headers: dict) -> dict:
    response = requests.post(
        LEETCODE_GRAPHQL_URL,
        json={"query": query, "variables": variables},
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


def main() -> None:
    cookie = load_cookie_from_dotenv()
    headers = {
        "Content-Type": "application/json",
        "Cookie": cookie,
    }
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
    code = (
        details_payload.get("data", {})
        .get("submissionDetails", {})
        .get("code")
    )
    if code is None:
        raise SystemExit("Submission details response does not include code.")

    details = details_payload.get("data", {}).get("submissionDetails", {})
    question = details.get("question") or {}
    question_id = str(question.get("questionId") or "").strip()
    title_slug = str(question.get("titleSlug") or "").strip()
    if not question_id or not title_slug:
        raise SystemExit("Submission details response does not include questionId/titleSlug.")

    lang = details.get("lang") or {}
    language_name = str(lang.get("name") or "").strip()
    language_folder, _ = language_folder_and_extension(language_name)

    base_dir = Path(__file__).resolve().parent
    question_dir = base_dir / f"{question_id}. {title_slug}"
    solution_dir = question_dir / language_folder
    solution_dir.mkdir(parents=True, exist_ok=True)

    solution_file = solution_dir / "solution.txt"
    solution_file.write_text(code, encoding="utf-8")
    print(f"Saved: {solution_file}")


if __name__ == "__main__":
    main()
