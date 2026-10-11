#!/usr/bin/env python3
"""Validate an external profile and freeze local artwork prompt plans. No network."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(base, value):
    p = (base / value).resolve()
    if not p.is_relative_to(base.resolve()) or not p.is_file():
        raise ValueError(f'missing or escaping profile file: {value}')
    return p


def discover_registry():
    import os
    configured = os.environ.get('PODCAST_ARTWORK_PROFILE_REGISTRY')
    if configured:
        return Path(configured).resolve(strict=True)
    roots = [Path.cwd(), Path(__file__).resolve().parents[4]]
    candidates = {p.resolve() for root in roots for p in root.glob('*/*/notes/brand/artwork-profiles.json')}
    if len(candidates) > 1:
        raise ValueError('multiple artwork registries; specify --profile-registry')
    return next(iter(candidates), None)


def resolve_profile(brief, explicit=None, registry_path=None):
    metadata_ref = brief.get('metadata', {}).get('artwork', {}).get('profile_ref')
    if explicit is not None:
        if metadata_ref and Path(metadata_ref).resolve() != Path(explicit).resolve():
            raise ValueError('explicit profile conflicts with metadata.artwork.profile_ref')
        return explicit, 'explicit-profile'
    if metadata_ref:
        return metadata_ref, 'metadata-profile'
    registry_path = registry_path or discover_registry()
    if registry_path:
        registry = Path(registry_path).resolve(strict=True)
        records = json.loads(registry.read_text())
        if records.get('schema_version') != '1.0':
            raise ValueError('unsupported artwork registry schema')
        matches = [r for r in records.get('profiles', []) if r['show_id'] == brief['show_id']]
        if len(matches) > 1:
            raise ValueError('ambiguous profiles for show_id')
        if matches:
            return (registry.parent / matches[0]['profile_ref']).resolve(strict=True), 'registry-profile'
    return None, None


def plan(brief, profile_path=None, registry_path=None):
    for key in ('show_id', 'show_name', 'asset_type', 'composition'):
        if not isinstance(brief.get(key), str) or not brief[key].strip():
            raise ValueError(f'brief requires {key}')
    kind = brief['asset_type']
    if kind not in ('show', 'episode'):
        raise ValueError('asset_type must be show or episode')
    for key in ('source_refs', 'copy'):
        if not isinstance(brief.get(key), list) or not brief[key] or not all(isinstance(x, str) and x.strip() for x in brief[key]):
            raise ValueError(f'brief requires nonempty {key}')
    if kind == 'episode' and (type(brief.get('episode_number')) is not int or brief['episode_number'] < 1):
        raise ValueError('episode brief requires a positive episode_number')
    profile_path, resolved_by = resolve_profile(brief, profile_path, registry_path)
    if profile_path is not None:
        path = Path(profile_path).resolve(strict=True)
        if path.suffix.lower() == '.json':
            profile = json.loads(path.read_text())
        else:
            import yaml
            try:
                profile = yaml.safe_load(path.read_text())
            except yaml.YAMLError as error:
                raise ValueError("malformed profile YAML") from error
        if not isinstance(profile, dict) or profile.get('schema_version') != '1.0':
            raise ValueError('unsupported profile schema')
        for key in ('profile_id', 'revision', 'show_id', 'brand'):
            if not isinstance(profile.get(key), str) or not profile[key].strip() or 'REPLACE' in profile[key]:
                raise ValueError(f'profile requires completed {key}')
        if profile['show_id'] != brief['show_id']:
            raise ValueError('profile show_id differs from brief')
        for key in ('shared', 'styles', 'asset_rules'):
            if not isinstance(profile.get(key), dict) or not profile[key]:
                raise ValueError(f'profile requires {key} mapping')
        if kind not in profile['asset_rules'] or not isinstance(profile['asset_rules'][kind], dict):
            raise ValueError(f'profile has no {kind} asset rules')
        base = path.parent
        manifest = {}
        if profile.get('reference_manifest'):
            records = json.loads(contained(base, profile['reference_manifest']).read_text())
            if not isinstance(records, list):
                raise ValueError('reference_manifest must be an array')
            for record in records:
                if record['path'] in manifest:
                    raise ValueError('duplicate reference path')
                file = contained(base, record['path'])
                actual = digest(file)
                if actual != record['sha256']:
                    raise ValueError(f'reference hash mismatch: {record["path"]}')
                manifest[record['path']] = {'path': str(file), 'sha256': actual}
        for style in profile['styles'].values():
            if not isinstance(style, dict) or not all(isinstance(style.get(k), str) and style[k].strip() for k in ('id', 'name', 'medium', 'composition_rule')):
                raise ValueError('incomplete style entry')
            for key in ('primary_reference', 'secondary_reference'):
                if style.get(key) and style[key] not in manifest:
                    raise ValueError(f'reference absent from manifest: {style[key]}')
        if len({s['id'] for s in profile['styles'].values()}) != len(profile['styles']):
            raise ValueError('duplicate style id')
        composition_template = contained(base, profile['composition_prompt']).read_text() if profile.get('composition_prompt') else ''
        resolution = resolved_by
        identity = {'profile_ref': str(path), 'profile_sha256': digest(path)}
    else:
        profile = {'brand': brief['show_name'], 'shared': {'canvas': {'aspect_ratio': '1:1', 'text_safe_margin_percent': 8}, 'palette': {'paper': '#fff8ef', 'ink': '#252525'}, 'prohibitions': ['invented people, claims, attribution or logos']}, 'styles': {'neutral': {'id': 'neutral-editorial', 'name': 'Neutral editorial', 'medium': 'matte editorial illustration', 'composition_rule': 'one content-grounded focal subject, generous negative space'}}, 'asset_rules': {kind: {'hierarchy': 'clear show name and supplied copy'}}}
        manifest = {}; composition_template = ''; resolution = 'neutral-fallback'; identity = {'profile_ref': None, 'profile_sha256': None}
        design = brief.get('design_system')
        if design is not None:
            if not isinstance(design, dict) or not isinstance(design.get('shared'), dict) or not design['shared']:
                raise ValueError('design_system requires shared rules')
            if not brief.get('design_system_source_refs'):
                raise ValueError('design_system requires source references')
            profile['shared'].update(design['shared'])
            if design.get('styles'):
                for entry in design['styles'].values():
                    if not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ('id', 'name', 'medium', 'composition_rule')):
                        raise ValueError('incomplete temporary design-system style')
                    if entry.get('primary_reference') or entry.get('secondary_reference'):
                        raise ValueError('temporary image references require a validated external profile')
                profile['styles'] = design['styles']
            if design.get('asset_rules', {}).get(kind):
                profile['asset_rules'][kind] = design['asset_rules'][kind]
            resolution = 'design-system-fallback'
        profile.update(schema_version='1.0', profile_id='temporary-'+brief['show_id'], revision='temporary', show_id=brief['show_id'])

    keys = brief.get('style_keys', list(profile['styles']))
    if not isinstance(keys, list) or not keys or any(k not in profile['styles'] for k in keys):
        raise ValueError('unknown or empty style_keys')
    candidates = []
    for key in keys:
        style = profile['styles'][key]
        images = [manifest[style[k]] for k in ('primary_reference', 'secondary_reference') if style.get(k)]
        prompt = '\n'.join(['Create a square podcast '+kind+' artwork.', 'Profile locks: '+json.dumps({'brand': profile['brand'], 'brand_en': profile.get('brand_en'), 'shared': profile['shared'], 'asset_rules': profile['asset_rules'][kind]}, ensure_ascii=False), 'Style: '+json.dumps(style, ensure_ascii=False), 'Composition guide: '+composition_template, 'Source-grounded brief: '+json.dumps(brief, ensure_ascii=False), 'Render only the exact strings in brief.copy. References govern style, not previous episode facts.'])
        candidates.append({'style_key': key, 'style_id': style['id'], 'reference_images': images, 'prompt': prompt, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()})
    return {'schema_version': '1.0', 'profile_resolution': resolution, **identity, 'brief': brief, 'candidates': candidates, 'selection_required': True, 'publication_authorized': False, 'temporary_profile': profile if profile_path is None else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--brief', required=True)
    parser.add_argument('--profile')
    parser.add_argument('--profile-registry', help='optional show-ID to canonical-profile registry')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        result = plan(json.loads(Path(args.brief).read_text()), args.profile, args.profile_registry)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(output)


if __name__ == '__main__':
    main()
