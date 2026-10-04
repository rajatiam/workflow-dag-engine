import argparse, json
import asyncio
from pathlib import Path
from .core import execute, validate, write_journal, plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect and run dependency workflows")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["run", "validate", "plan"]:
        sub = commands.add_parser(name)
        sub.add_argument("workflow")
        if name == "run":
            sub.add_argument("--workers", type=int, default=4)
            sub.add_argument("--journal")
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.workflow).read_text(encoding="utf-8"))
    if args.command == "plan":
        result = plan(spec)
    elif args.command == "validate":
        result = {"valid": True, "tasks": len(validate(spec))}
    else:
        if (
            args.journal
            and Path(args.journal).resolve() == Path(args.workflow).resolve()
        ):
            raise ValueError("Journal must differ from workflow input")
        result = asyncio.run(execute(spec, args.workers))
        if args.journal:
            write_journal(args.journal, result)
    print(json.dumps(result, indent=2, allow_nan=False))
    if args.command == "run" and not result["success"]:
        raise SystemExit(1)
