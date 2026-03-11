"""CLI entrypoint for the Architect engine."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .assembler import Assembler
from .common import PROJECT_ROOT
from .conductor import Conductor
from .forge import Forge
from .interviewer import Interviewer
from .llm_client import OpenAICompatibleLLMClient


async def run(args: argparse.Namespace) -> int:
    llm = OpenAICompatibleLLMClient.from_env()
    interviewer = Interviewer(llm)

    opening = await interviewer.start()
    print(opening.message)

    final_artifacts = None
    while final_artifacts is None:
        try:
            user_message = input("> ").strip()
        except EOFError:
            return 1
        if not user_message:
            continue
        step = await interviewer.process_user_message(user_message)
        if step.message:
            print(step.message)
        if step.artifacts:
            final_artifacts = step.artifacts

    conductor = Conductor()
    manifest = conductor.process_interview_results(
        final_artifacts.routing_tags,
        final_artifacts.narrative_briefing,
        final_artifacts.player_profile,
    )
    forged_results = await Forge(llm).execute(manifest)
    final_prompt = await Assembler(llm).assemble(forged_results, manifest)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(final_prompt, encoding="utf-8")
        print(f"Final prompt written to {output_path}")
    else:
        print("\n===== FINAL SYSTEM PROMPT =====\n")
        print(final_prompt)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the OSeria Architect Engine interview pipeline.")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "architect_system_prompt.txt"),
        help="Where to write the final assembled system prompt.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())

