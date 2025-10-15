from __future__ import annotations

import argparse
import asyncio
import json
import sys

from ai.exceptions import ChatPipelineError, GeminiClientError
from ai.pipelines import ChatPipeline
from ai.schemas import ChatRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a single message to the Gemini-powered chat pipeline."
    )
    parser.add_argument("message", help="User message to send to the LLM.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the response as JSON (default: pretty text).",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    try:
        pipeline = ChatPipeline.from_env()
        response = await pipeline.run(ChatRequest(content=args.message))
    except (ValueError, GeminiClientError, ChatPipelineError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(response.__dict__, ensure_ascii=False, indent=2))
    else:
        print(response.content)
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
