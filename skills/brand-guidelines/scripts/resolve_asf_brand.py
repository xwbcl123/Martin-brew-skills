#!/usr/bin/env python3
"""Resolve and verify the read-only ASF brand dependency, with no network writes."""
import argparse, hashlib, json, os
from pathlib import Path

def resolve(root=None, register='paper'):
    skill = Path(__file__).resolve().parents[1]
    lock = json.loads((skill/'references/asf-brand-lock.json').read_text(encoding='utf-8'))
    selected = root or os.environ.get('ASF_BRAND_ROOT')
    source = Path(selected).expanduser().resolve() if selected else skill.parent/'artifact-template-asf-deck/assets/source/assets/asf-brand-v1.2.2'
    problems = [name for name, digest in lock['files'].items() if not (source/name).is_file() or hashlib.sha256((source/name).read_bytes()).hexdigest() != digest]
    if problems:
        raise ValueError('Missing or mismatched locked ASF brand assets: '+', '.join(problems)+'. Supply --root or ASF_BRAND_ROOT at v1.2.2.')
    tokens = json.loads((source/'tokens/tokens.json').read_text(encoding='utf-8'))
    return {'root': str(source), 'tag': lock['tag'], 'commit': lock['commit'], 'register': register,
            'verified_files': len(lock['files']), 'tokens': str(source/'tokens/tokens.json'),
            'logo': str(source/f'logo/asf-logo-{register}.svg'), 'version': tokens['version']}

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root'); parser.add_argument('--register', choices=['paper','ink'], default='paper')
    args=parser.parse_args()
    try: print(json.dumps(resolve(args.root,args.register),indent=2))
    except (ValueError,OSError,KeyError) as e: parser.exit(1,str(e)+'\n')
