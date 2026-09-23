#!/usr/bin/env python3
"""Validate tracked canonical source without generating an export checkout.

Print locations and rule names only; never echo possible credentials.
Historical vocabulary rules remain in check_export_scrub for old exports.
"""
from pathlib import Path
import re
import subprocess
import sys
from check_export_scrub import SCRUB_PATTERNS


def main():
    root=Path(__file__).resolve().parent.parent
    patterns=[]
    for label,pattern,ignore_case in SCRUB_PATTERNS:
        if label not in ('personal path/handle','sibling POS customer identity','secret material','private configured rule'):continue
        if label == 'personal path/handle':
            pattern = pattern.replace('|~/Developer', '')
        patterns.append((label,re.compile(pattern,re.I if ignore_case else 0)))
    files=subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0')
    failures=[]
    for name in files:
        if not name or name in ('scripts/check_export_scrub.py',):continue
        path=root/name
        if not path.exists():continue
        if path.is_symlink():
            if not path.resolve().is_relative_to(root):failures.append((name,0,'external source symlink'))
            continue
        fixture=name.startswith('overview/v1/tests/fixtures/')
        if path.suffix.lower() in ('.key','.p12') or path.name=='.env' or (not fixture and (path.suffix.lower() in ('.db','.sqlite','.sqlite3') or '/local/' in '/'+name)):
            failures.append((name,0,'runtime or secret file in source'))
            continue
        try:text=path.read_text()
        except (UnicodeError,OSError):continue
        for number,line in enumerate(text.splitlines(),1):
            for label,pattern in patterns:
                if pattern.search(line):failures.append((name,number,label))
    for name,number,label in failures:print('{}:{}: {}'.format(name,number,label))
    print('Canonical source privacy check: {} finding(s)'.format(len(failures)))
    return int(bool(failures))


if __name__=='__main__':sys.exit(main())
