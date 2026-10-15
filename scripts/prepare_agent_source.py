"""Export a pinned, tracked AgInTi SDK build context, never a live workspace."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aginti-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "agent/aginti.lock.json").read_text())
    if args.output.exists():
        raise SystemExit("Use a new empty build context; existing snapshots are preserved")
    archive = subprocess.check_output(["git", "-C", str(args.aginti_repo), "archive",
        "--format=tar", lock["commit"], "src", "package.json", "package-lock.json", "LICENSE"])
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        members = tar.getmembers()
        for item in members:
            path = Path(item.name)
            if path.is_absolute() or ".." in path.parts or not (item.isfile() or item.isdir()):
                raise SystemExit("Unexpected AgInTi archive member")
        entry = tar.extractfile(lock["entry"])
        if not entry or hashlib.sha256(entry.read()).hexdigest() != lock["sha256"]:
            raise SystemExit("AgInTi entry digest differs from reviewed source")
        args.output.mkdir(parents=True, mode=0o700)
        tar.extractall(args.output, members=members, filter="data")
    (args.output / "source.json").write_text(json.dumps(lock, indent=2) + "\n")
    print(json.dumps({"commit": lock["commit"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
