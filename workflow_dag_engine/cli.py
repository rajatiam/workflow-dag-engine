import argparse, asyncio, json
from pathlib import Path
from .core import execute, validate, write_journal


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run allowlisted local workflows with dependency ordering"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("workflow")
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--journal")
    check = commands.add_parser("validate")
    check.add_argument("workflow")
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.workflow).read_text(encoding="utf-8"))
    if args.command == "validate":
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
