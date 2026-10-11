"""Stage a content-addressed backend/web snapshot without changing live services."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    files = sorted((source / "server").glob("*.py")) + sorted(
        p for p in (source / "dist").rglob("*") if p.is_file()
    )
    if not (source / "dist/catalog.json").is_file():
        raise RuntimeError("Build the web catalog before staging")
    hashes = {}
    for path in files:
        if path.is_symlink():
            raise RuntimeError("Snapshot inputs must be regular files")
        hashes[str(path.relative_to(source))] = hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    release = args.output.resolve() / digest[:16]
    release.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in files:
        relative = path.relative_to(source)
        target = release / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if target.exists():
            if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() != hashes[str(relative)]:
                raise RuntimeError("Existing snapshot differs")
        else:
            shutil.copy2(path, target)
    # API catalog/download validation needs the same catalog as the static site.
    public = release / "public"
    public.mkdir(exist_ok=True, mode=0o700)
    shutil.copy2(release / "dist/catalog.json", public / "catalog.json")
    (release / "manifest.json").write_text(json.dumps({"sha256": digest, "files": hashes}, indent=2) + "\n")
    print(release)


if __name__ == "__main__":
    main()
