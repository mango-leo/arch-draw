"""Install the shared architecture skills in the project for Codex and Claude Code."""

import argparse
import json
from pathlib import Path
import shutil
import sys


SOURCE = Path(__file__).resolve().parent / "skills"
HOSTS = {"codex": ".agents", "claude": ".claude"}


def files(folder):
    return {file.relative_to(folder): file.read_bytes() for file in folder.rglob("*")
            if file.is_file() and "__pycache__" not in file.parts}


def install(project, hosts):
    if not project.is_dir():
        raise ValueError(f"project directory does not exist: {project}")
    registry = json.loads((SOURCE / "architecture-svg" / "registry.json").read_text(encoding="utf-8"))
    names = ["architecture-svg", *(entry["skill"] for entry in registry["domains"].values())]
    pending = []
    for host in hosts:
        for name in names:
            source = SOURCE / name
            target = project / HOSTS[host] / "skills" / name
            if target.exists() or target.is_symlink():
                if not target.is_dir() or target.is_symlink() or files(source) != files(target):
                    raise ValueError(f"existing skill differs: {target}. Move that copy aside before reinstalling.")
            else:
                pending.append((source, target))
    for source, target in pending:
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    return len(pending)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--host", choices=[*HOSTS, "both"], default="both")
    args = parser.parse_args()
    try:
        count = install(args.project.resolve(), HOSTS if args.host == "both" else [args.host])
        print(f"Installed {count} new skill folder(s). Existing matching copies are ready to use.")
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
