"""Command line entry point.

Design goal: the whole review pipeline must be runnable offline with
`--provider mock`, so tests and contributors never need an API key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from . import __version__
from .config import Config, load_config
from .diff import parse_unified_diff
from .github import GitHubClient, GitHubError
from .models import ReviewResult
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .providers import MockProvider, OpenAICompatProvider, Provider, ProviderError
from .publish import publish
from .render import render_markdown
from .rules import load_rules, match_rules, validate_rules
from .validate import apply_guardrails


def _ensure_utf8() -> None:
    """Windows consoles default to GBK; findings contain emoji and CJK."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # pragma: no cover - platform specific
            pass


def _read_diff(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def _parse_model_json(text: str) -> dict:
    return json.loads(_strip_fence(text))


def _resolve_provider(args: argparse.Namespace, config: Config) -> Provider:
    name = args.provider or config.review.provider or "mock"

    if name == "mock":
        if not args.mock_response:
            raise ProviderError("mock provider 需要 --mock-response")
        return MockProvider.from_file(args.mock_response)

    api_key = args.api_key or os.environ.get("CODEREV_API_KEY", "")
    model = args.model or config.review.model
    base_url = args.base_url or config.review.base_url or "https://api.openai.com/v1"
    return OpenAICompatProvider(api_key=api_key, model=model, base_url=base_url)


def _run_review(
    args: argparse.Namespace,
    diff_text: str,
    config: Config,
) -> tuple[ReviewResult, list, bool, list[str]] | int:
    files = parse_unified_diff(diff_text)
    if not files:
        print("没有解析到新增行，跳过审查。", file=sys.stderr)
        return 0

    rules_path = args.rules or config.review.rules
    rules = []
    if rules_path:
        rules = match_rules(load_rules(Path(rules_path)), list(files))

    provider = _resolve_provider(args, config)
    prompt = build_user_prompt(diff_text, files, rules)

    try:
        raw = provider.complete(SYSTEM_PROMPT, prompt)
    except ProviderError as exc:
        print(f"模型调用失败：{exc}", file=sys.stderr)
        return 3

    try:
        payload = _parse_model_json(raw)
    except json.JSONDecodeError as exc:
        print(f"模型输出不是合法 JSON：{exc}", file=sys.stderr)
        print(raw[:500], file=sys.stderr)
        return 2

    result = ReviewResult.from_dict(payload)
    filtered, dropped, truncated = apply_guardrails(
        result,
        files,
        min_confidence=args.min_confidence
        if args.min_confidence is not None
        else config.review.min_confidence,
        max_findings=args.max_findings
        if args.max_findings is not None
        else config.review.max_findings,
    )
    return filtered, dropped, truncated, sorted(files)


def cmd_review(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    outcome = _run_review(args, _read_diff(args.diff), config)
    if isinstance(outcome, int):
        return outcome

    result, dropped, truncated, reviewed = outcome
    run_id = uuid.uuid4().hex[:12]

    if args.markdown:
        output = render_markdown(result, run_id=run_id, dropped=len(dropped), truncated=truncated)
    else:
        output = json.dumps(
            {
                "run_id": run_id,
                "reviewed_files": reviewed,
                "result": result.to_dict(),
                "dropped": dropped,
                "truncated": truncated,
            },
            ensure_ascii=False,
            indent=2,
        )

    if args.out:
        Path(args.out).write_text(output + ("\n" if not output.endswith("\n") else ""), encoding="utf-8")
        print(f"已写入 {args.out}", file=sys.stderr)
    else:
        print(output)

    return 0


def cmd_pr(args: argparse.Namespace) -> int:
    token = args.token or os.environ.get("GITHUB_TOKEN", "")
    config = load_config(args.config)

    try:
        client = GitHubClient(repo=args.repo, token=token)
        diff_text = client.get_diff(args.pr)
    except (ValueError, GitHubError) as exc:
        print(f"拉取 PR 失败：{exc}", file=sys.stderr)
        return 4

    outcome = _run_review(args, diff_text, config)
    if isinstance(outcome, int):
        return outcome

    result, dropped, truncated, _ = outcome
    run_id = uuid.uuid4().hex[:12]

    if not (args.post or config.review.post):
        print(render_markdown(result, run_id=run_id, dropped=len(dropped), truncated=truncated))
        return 0

    published = publish(
        client,
        args.pr,
        result,
        dropped=len(dropped),
        truncated=truncated,
        run_id=run_id,
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "summary": published.summary_action,
                "inline_created": published.inline_created,
                "inline_deleted": published.inline_deleted,
                "dropped": len(dropped),
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .server import serve

    serve(args.host, args.port)
    return 0


def cmd_rules(args: argparse.Namespace) -> int:
    if args.rules_command != "validate":
        print("用法：coderev rules validate --path <dir>", file=sys.stderr)
        return 1

    rules = load_rules(Path(args.path))
    problems = validate_rules(rules)
    if problems:
        print(f"发现 {len(problems)} 个问题：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"OK：{len(rules)} 条规则通过校验")
    return 0


def _add_review_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help=".coderev.yml 路径（默认自动查找）")
    parser.add_argument("--rules", help="规则文件或目录（覆盖配置）")
    parser.add_argument("--provider", choices=["mock", "openai"], default=None)
    parser.add_argument("--mock-response", help="mock provider 的响应 JSON")
    parser.add_argument("--model", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--min-confidence", type=float, default=None)
    parser.add_argument("--max-findings", type=int, default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coderev", description="Open-source PR review")
    parser.add_argument("--version", action="version", version=f"coderev {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="审查一个本地 diff")
    review.add_argument("--diff", required=True, help="diff 文件路径，- 表示 stdin")
    _add_review_flags(review)
    review.add_argument("--markdown", action="store_true", help="输出 Markdown 评论")
    review.add_argument("--out", help="写入文件而不是 stdout")
    review.set_defaults(func=cmd_review)

    pr = sub.add_parser("pr", help="审查 GitHub PR 并回写评论")
    pr.add_argument("--repo", required=True, help="owner/name")
    pr.add_argument("--pr", type=int, required=True, help="PR 编号")
    pr.add_argument("--token", default="", help="GitHub token（默认读 GITHUB_TOKEN）")
    pr.add_argument("--post", action="store_true", help="回写评论（默认只打印）")
    _add_review_flags(pr)
    pr.set_defaults(func=cmd_pr)

    rules = sub.add_parser("rules", help="规则相关命令")
    rules_sub = rules.add_subparsers(dest="rules_command", required=True)
    validate = rules_sub.add_parser("validate", help="校验规则包")
    validate.add_argument("--path", required=True)
    validate.set_defaults(func=cmd_rules)

    serve_parser = sub.add_parser("serve", help="启动常驻服务（健康检查）")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8080)
    serve_parser.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
