"""Maintain the wheel template mirror without deleting unrecognized files."""
from pathlib import Path
import argparse
import shutil


def sync(source: Path, mirror: Path, *, check: bool = False) -> bool:
    source_files = {p.relative_to(source) for p in source.rglob('*') if p.is_file()}
    mirror_files = {p.relative_to(mirror) for p in mirror.rglob('*') if p.is_file()}
    extras = sorted(mirror_files - source_files)
    for path in extras:
        print(f'Unexpected packaged template (preserved): {path}')
    changed = []
    for path in sorted(source_files):
        src, dst = source / path, mirror / path
        if not dst.is_file() or src.read_bytes() != dst.read_bytes():
            changed.append(path)
            print(f'{"Drift" if check else "Sync"}: {path}')
            if not check:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    return not extras and (not changed or not check)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    raise SystemExit(0 if sync(root / 'templates', root / 'protocolcity/templates',
                              check=args.check) else 1)
