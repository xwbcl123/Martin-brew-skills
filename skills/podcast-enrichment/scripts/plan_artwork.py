#!/usr/bin/env python3
"""Validate an external profile and freeze local artwork prompt plans. No network."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# BEGIN podcast-config (byte-identical in every consumer; guarded by podcast-release-package/scripts/test_config_copies.py)
def _podcast_cfg(_cache={}):
    """Personal defaults from $PODCAST_CONFIG or ~/.config/podcast-skills/config.json. Read lazily, once; never grants approval/authorization."""
    import json, os, re
    from pathlib import Path
    keys = {'workspace', 'whisper_cli', 'whisper_model', 'transistor_cli', 'transistor_cli_repo',
            'language', 'approver', 'artwork_registry', 'planning_profiles_dir'}
    plain = {'language', 'approver'}
    explicit = os.environ.get('PODCAST_CONFIG')
    if explicit is not None:
        if not explicit.strip() or not Path(explicit).expanduser().is_absolute():
            raise SystemExit('PODCAST_CONFIG must be a non-empty absolute path (unset it to use ~/.config/podcast-skills/config.json)')
        path = Path(explicit).expanduser()
    else:
        path = Path.home() / '.config' / 'podcast-skills' / 'config.json'
    if str(path) in _cache:
        return _cache[str(path)]
    if explicit is not None and not path.is_file():
        raise SystemExit(f'PODCAST_CONFIG points to a missing file: {path}')
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except ValueError as exc:
            raise SystemExit(f'invalid JSON in {path}: {exc}')
    if not isinstance(data, dict):
        raise SystemExit(f'{path}: top level must be an object')
    extra = sorted(set(data) - keys - {'shows'})
    if extra:
        raise SystemExit(f'{path}: unknown keys {extra}')
    for key in keys & set(data):
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f'{path}: {key} must be a non-empty string')
        if key not in plain and not Path(value).expanduser().is_absolute():
            raise SystemExit(f'{path}: {key} must be an absolute path')
    shows = data.setdefault('shows', {})
    if not isinstance(shows, dict):
        raise SystemExit(f'{path}: shows must be an object keyed by show id')
    for sid, entry in shows.items():
        if not re.fullmatch(r'[0-9]+', str(sid)) or not isinstance(entry, dict) or set(entry) - {'author', 'brand_name', 'brand_tagline'}:
            raise SystemExit(f'{path}: shows[{sid!r}] must be an object with only author/brand_name/brand_tagline')
        for field in ('author', 'brand_name'):
            if field in entry and (not isinstance(entry[field], str) or not entry[field].strip()):
                raise SystemExit(f'{path}: shows[{sid!r}].{field} must be a non-empty string')
        if 'brand_tagline' in entry and not isinstance(entry['brand_tagline'], str):
            raise SystemExit(f'{path}: shows[{sid!r}].brand_tagline must be a string')
    _cache[str(path)] = data
    return data


def _podcast_pick(cli, env_name, key):
    """Provided CLI value > provided environment variable > config file > None. A provided-but-blank value is an error, never "unset"."""
    import os
    for source, value in (('command line', cli), (f'${env_name}', os.environ.get(env_name) if env_name else None)):
        if value is not None:
            if not str(value).strip():
                raise SystemExit(f'{key}: empty value from the {source}; omit it to use the default')
            return value
    return _podcast_cfg().get(key)


def _podcast_tool(cli, env_name, key, command):
    """A provided tool path must be an absolute executable file and is used as-is (never re-resolved through PATH); `command` is only looked up when nothing was provided."""
    import os, shutil
    value = _podcast_pick(cli, env_name, key)
    if value is not None:
        value = os.path.expanduser(str(value))
        if not os.path.isabs(value):
            raise SystemExit(f'{key}: {value} must be an absolute path (relative values are never searched on PATH)')
        if not (os.path.isfile(value) and os.access(value, os.X_OK)):
            raise SystemExit(f'{key}: {value} is not an executable file (fix --{key.replace("_", "-")}, ${env_name or "PODCAST_CONFIG"} or the podcast-skills config)')
        return value
    found = shutil.which(command)
    if not found:
        raise SystemExit(f'{command} not found: pass --{key.replace("_", "-")}, set ${env_name or "PODCAST_CONFIG"} or add "{key}" to ~/.config/podcast-skills/config.json')
    return os.path.abspath(found)


def _podcast_model(cli):
    """Whisper model: CLI > $WHISPER_MODEL > config whisper_model > <workspace>/models/ggml-large-v3-q5_0.bin."""
    import os
    value = _podcast_pick(cli, 'WHISPER_MODEL', 'whisper_model')
    if value is None:
        workspace = _podcast_pick(None, 'PODCAST_WORKSPACE', 'workspace')
        if workspace is None:
            raise SystemExit('no Whisper model: pass --model, set $WHISPER_MODEL, or add whisper_model/workspace to ~/.config/podcast-skills/config.json')
        workspace = os.path.expanduser(str(workspace))
        if not os.path.isabs(workspace):
            raise SystemExit(f'workspace: {workspace} must be an absolute path')
        value = os.path.join(workspace, 'models', 'ggml-large-v3-q5_0.bin')
    value = os.path.expanduser(str(value))
    if not os.path.isabs(value):
        raise SystemExit(f'whisper_model: {value} must be an absolute path')
    if not os.path.isfile(value):
        raise SystemExit(f'Whisper model does not exist: {value}')
    return value
# END podcast-config


def contained(base, value):
    p = (base / value).resolve()
    if not p.is_relative_to(base.resolve()) or not p.is_file():
        raise ValueError(f'missing or escaping profile file: {value}')
    return p


def discover_registry():
    """Explicit registry only: $PODCAST_ARTWORK_PROFILE_REGISTRY or config artwork_registry (absolute). No cwd/vault scanning."""
    configured = _podcast_pick(None, 'PODCAST_ARTWORK_PROFILE_REGISTRY', 'artwork_registry')
    if configured is None:
        return None
    path = Path(str(configured)).expanduser()
    if not path.is_absolute():
        raise ValueError('artwork registry must be an absolute path')
    return path.resolve(strict=True)


def resolve_profile(brief, explicit=None, registry_path=None, seen=None):
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
        if seen is not None: seen.append(registry)
        records = json.loads(registry.read_text())
        if records.get('schema_version') != '1.0':
            raise ValueError('unsupported artwork registry schema')
        matches = [r for r in records.get('profiles', []) if r['show_id'] == brief['show_id']]
        if len(matches) > 1:
            raise ValueError('ambiguous profiles for show_id')
        if matches:
            return (registry.parent / matches[0]['profile_ref']).resolve(strict=True), 'registry-profile'
    return None, None


def plan(brief, profile_path=None, registry_path=None, inputs=None):
    """`inputs`, when given, receives every file that was read (profile, manifest, composition guide, references)."""
    seen = inputs if inputs is not None else []
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
    profile_path, resolved_by = resolve_profile(brief, profile_path, registry_path, seen)
    if profile_path is not None:
        path = Path(profile_path).resolve(strict=True)
        seen.append(path)
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
            manifest_file = contained(base, profile['reference_manifest']); seen.append(manifest_file)
            records = json.loads(manifest_file.read_text())
            if not isinstance(records, list):
                raise ValueError('reference_manifest must be an array')
            for record in records:
                if record['path'] in manifest:
                    raise ValueError('duplicate reference path')
                file = contained(base, record['path']); seen.append(file)
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
        composition_file = contained(base, profile['composition_prompt']) if profile.get('composition_prompt') else None
        if composition_file: seen.append(composition_file)
        composition_template = composition_file.read_text() if composition_file else ''
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
    parser.add_argument('--profile-registry', help='optional show-ID to canonical-profile registry (default: $PODCAST_ARTWORK_PROFILE_REGISTRY, then config artwork_registry)')
    parser.add_argument('--output', required=True)
    parser.add_argument('--overwrite', action='store_true', help='replace an existing plan file (never an input file)')
    args = parser.parse_args()
    inputs = []
    try:
        result = plan(json.loads(Path(args.brief).read_text()), args.profile, args.profile_registry, inputs)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    import os, tempfile
    protected = [Path(args.brief), *inputs]
    output = Path(args.output)
    if output.is_symlink() or output.parent.is_symlink():
        parser.error('output and its directory must not be symlinks')
    target = Path(os.path.realpath(output.parent)) / output.name
    for source in protected:
        source = Path(os.path.realpath(source))
        if source == target or (target.exists() and source.exists() and os.path.samefile(source, target)):
            parser.error(f'output would overwrite an input file: {source.name}')
    if target.exists() and not args.overwrite:
        parser.error('output exists; pass --overwrite to replace an existing plan')
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.plan.', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as out:
            out.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        os.replace(temporary, target)
    except BaseException:
        if os.path.exists(temporary): os.unlink(temporary)
        raise
    print(target)


if __name__ == '__main__':
    main()
