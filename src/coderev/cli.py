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
from .diff import parse_unified_diff
from .models import ReviewResult
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .providers import MockProvider, OpenAICompatProvider, Provider, ProviderError
from .render import render_markdown
from .rules import load_rules, match_rules, validate_rules
from .validate import apply_guardrails


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


def _make_provider(args: argparse.Namespace) -> Provider:
    if args.provider == "mock":
        if not args.mock_response:
            raise ProviderError("--provider mock 需要同时提供 --mock-response")
        return MockProvider.from_file(args.mock_response)

    return OpenAICompatProvider(
        api_key=args.api_key or os.environ.get("CODEREV_API_KEY", ""),
        model=args.model or os.environ.get("CODEREV_MODEL", ""),
        base_url=args.base_url or os.environ.get("CODEREV_BASE_URL", "https://api.openai.com/v1"),
    )


def cmd_review(args: argparse.Namespace) -> int:
    diff_text = _read_diff(args.diff)
    files = parse_unified_diff(diff_text)
    if not files:
        print("没有解析到新增行，跳过审查。", file=sys.stderr)
        return 0

    rules = []
    if args.rules:
        rules = match_rules(load_rules(Path(args.rules)), list(files))

    provider = _make_provider(args)
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
        min_confidence=args.min_confidence,
        max_findings=args.max_findings,
    )

    run_id = uuid.uuid4().hex[:12]

    if args.markdown:
        output = render_markdown(
            filtered,
            run_id=run_id,
            dropped=len(dropped),
            truncated=truncated,
        )
    else:
        output = json.dumps(
            {
                "run_id": run_id,
                "reviewed_files": sorted(files),
                "result": filtered.to_dict(),
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coderev", description="Open-source PR review")
    parser.add_argument("--version", action="version", version=f"coderev {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="审查一个 diff")
    review.add_argument("--diff", required=True, help="diff 文件路径，- 表示 stdin")
    review.add_argument("--rules", help="规则文件或目录")
    review.add_argument("--provider", choices=["mock", "openai"], default="mock")
    review.add_argument("--mock-response", help="mock provider 的响应 JSON")
    review.add_argument("--model", default="")
    review.add_argument("--base-url", default="")
    review.add_argument("--api-key", default="")
    review.add_argument("--min-confidence", type=float, default=0.6)
    review.add_argument("--max-findings", type=int, default=8)
    review.add_argument("--markdown", action="store_true", help="输出 Markdown 评论")
    review.add_argument("--out", help="写入文件而不是 stdout")
    review.set_defaults(func=cmd_review)

    rules = sub.add_parser("rules", help="规则相关命令")
    rules_sub = rules.add_subparsers(dest="rules_command", required=True)
    validate = rules_sub.add_parser("validate", help="校验规则包")
    validate.add_argument("--path", required=True)
    validate.set_defaults(func=cmd_rules)

    return parser


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


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
