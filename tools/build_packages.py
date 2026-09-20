#!/usr/bin/env python3
"""Build portable and Cursor packages from a single skill source. No network."""
import argparse
import hashlib
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'game-localization'


def write_archive(path, entries):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 20, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(entries)
        for name, data in entries.items():
            assert archive.read(name) == data, name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='0.2.0')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.version):
        parser.error('version must be MAJOR.MINOR.PATCH')
    # Installation instructions contain versioned archive names.
    guide = (ROOT / 'docs' / 'CURSOR.md').read_text(encoding='utf-8')
    guide = guide.replace('v0.2.0.zip', f'v{args.version}.zip')
    files = {}
    for path in sorted(SKILL.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.name != '.DS_Store' and path.suffix != '.pyc':
            if path.is_symlink():
                raise ValueError(f'Symlinks are not distributable: {path}')
            files[path.relative_to(SKILL).as_posix()] = path.read_bytes()
    assert 'SKILL.md' in files and 'LICENSE' in files
    args.output.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for flavor, prefix in [('portable', 'game-localization/'), ('cursor', '.cursor/skills/game-localization/')]:
        entries = {prefix + name: data for name, data in files.items()
                   if flavor == 'portable' or not name.startswith('agents/')}
        if flavor == 'cursor':
            entries['先看这里.md'] = guide.encode('utf-8')
        filename = f'game-localization{"-cursor" if flavor == "cursor" else ""}-v{args.version}.zip'
        destination = args.output / filename
        write_archive(destination, entries)
        artifacts.append(destination)
    sums = '\n'.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}' for p in artifacts) + '\n'
    (args.output / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
    print(sums, end='')


if __name__ == '__main__':
    main()
