#!/usr/bin/env python3
"""
validate_profile.py - Podcast Brand Profile Validator & Inspector
Usage:
    python3 validate_profile.py --list
    python3 validate_profile.py --profile geek-family
    python3 validate_profile.py --file /path/to/profile.yaml
"""

import argparse
import math
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("❌ Missing dependency: PyYAML. Please install pyyaml or run in an environment with PyYAML.", file=sys.stderr)
    sys.exit(1)

PROFILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profiles")

ALLOWED_FORMAT_TYPES = {
    "trio_dialogue",
    "solo_monologue",
    "ai_duo_discussion",
    "interview_panel"
}

REQUIRED_ROOT_KEYS = [
    "schema_version",
    "profile",
    "format",
    "tone_and_style",
    "personas",
    "tension_matrix",
    "narrative_structure",
    "routing"
]

def load_yaml(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Profile not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
        if content is None:
            raise ValueError("YAML file is empty or null")
        return content

def validate_profile_dict(data, filepath="<memory>"):
    errors = []
    if not isinstance(data, dict):
        return ["Profile root must be a mapping (YAML dictionary)"]

    # 1. Root keys check
    for k in REQUIRED_ROOT_KEYS:
        if k not in data:
            errors.append(f"Missing root key: '{k}'")

    # 2. Schema version: strictly 1.0.0
    schema_ver = data.get("schema_version")
    if schema_ver != "1.0.0":
        errors.append(f"Invalid schema_version '{schema_ver}': must be exactly '1.0.0'")

    # 3. Profile block
    p = data.get("profile")
    if not isinstance(p, dict):
        errors.append("'profile' section must be a dictionary")
    else:
        for field in ["id", "name", "show_id", "tagline", "description"]:
            val = p.get(field)
            if not isinstance(val, str) or not val.strip():
                errors.append(f"Missing or non-string field in 'profile': '{field}'")
        pid = p.get("id")
        if isinstance(pid, str):
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", pid):
                errors.append(f"Invalid profile.id format '{pid}': must be lowercase alphanumeric with hyphens")
        elif pid is not None:
            errors.append(f"profile.id must be a string, got {type(pid).__name__}")

    # 4. Format block
    fmt = data.get("format")
    ftype = None
    if not isinstance(fmt, dict):
        errors.append("'format' section must be a dictionary")
    else:
        ftype = fmt.get("type")
        if not isinstance(ftype, str) or ftype not in ALLOWED_FORMAT_TYPES:
            errors.append(f"Invalid 'format.type': '{ftype}'. Allowed canonical formats: {sorted(list(ALLOWED_FORMAT_TYPES))}")

        dur = fmt.get("target_duration_minutes")
        if isinstance(dur, bool) or not isinstance(dur, (int, float)) or not math.isfinite(dur) or dur <= 0:
            errors.append(f"'format.target_duration_minutes' must be a finite positive number, got: {dur}")

        ratio = fmt.get("unscripted_safe_harbor_ratio")
        if ratio is None:
            errors.append("Missing required field 'format.unscripted_safe_harbor_ratio'")
        elif isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or ratio < 0.05 or ratio > 0.50:
            errors.append(f"'format.unscripted_safe_harbor_ratio' must be a finite float between 0.05 and 0.50 (5%–50%), got: {ratio}")

    # 5. Tone and style block
    tone = data.get("tone_and_style")
    if not isinstance(tone, dict):
        errors.append("'tone_and_style' section must be a dictionary")
    else:
        keywords = tone.get("keywords")
        if not isinstance(keywords, list) or len(keywords) == 0 or not all(isinstance(x, str) and x.strip() for x in keywords):
            errors.append("'tone_and_style.keywords' must be a non-empty list of non-empty strings")
        prohibitions = tone.get("discussion_prohibitions")
        if not isinstance(prohibitions, list) or len(prohibitions) == 0 or not all(isinstance(x, str) and x.strip() for x in prohibitions):
            errors.append("'tone_and_style.discussion_prohibitions' must be a non-empty list of non-empty strings")

    # 6. Personas block
    personas = data.get("personas")
    persona_ids = set()
    if not isinstance(personas, list) or len(personas) == 0:
        errors.append("'personas' must be a non-empty list")
    else:
        for idx, persona in enumerate(personas):
            if not isinstance(persona, dict):
                errors.append(f"Persona #{idx+1} must be a dictionary")
                continue
            pers_id = persona.get("id")
            if not isinstance(pers_id, str) or not pers_id.strip():
                errors.append(f"Persona #{idx+1} missing valid string 'id'")
            elif pers_id in persona_ids:
                errors.append(f"Duplicate persona id detected: '{pers_id}'")
            else:
                persona_ids.add(pers_id)

            for pf in ["name", "role", "perspective"]:
                pval = persona.get(pf)
                if not isinstance(pval, str) or not pval.strip():
                    errors.append(f"Persona #{idx+1} ('{pers_id}') missing required string '{pf}'")

            # Check optional voice traits and signature phrases
            v_traits = persona.get("voice_traits")
            if v_traits is not None and (not isinstance(v_traits, list) or not all(isinstance(x, str) and x.strip() for x in v_traits)):
                errors.append(f"Persona '{pers_id}' voice_traits must be a list of non-empty strings")
            s_phrases = persona.get("signature_phrases")
            if s_phrases is not None and (not isinstance(s_phrases, list) or not all(isinstance(x, str) and x.strip() for x in s_phrases)):
                errors.append(f"Persona '{pers_id}' signature_phrases must be a list of non-empty strings")

        # Format-specific participant count check
        if ftype == "trio_dialogue" and len(persona_ids) < 3:
            errors.append(f"Format 'trio_dialogue' requires at least 3 personas, got {len(persona_ids)}")
        elif ftype == "ai_duo_discussion" and len(persona_ids) < 2:
            errors.append(f"Format 'ai_duo_discussion' requires at least 2 personas, got {len(persona_ids)}")
        elif ftype == "interview_panel" and len(persona_ids) < 2:
            errors.append(f"Format 'interview_panel' requires at least 2 personas (host + guest), got {len(persona_ids)}")
        elif ftype == "solo_monologue" and len(persona_ids) < 1:
            errors.append(f"Format 'solo_monologue' requires at least 1 persona (the host)")

    # 7. Tension matrix block
    tension = data.get("tension_matrix")
    pairs = None
    if isinstance(tension, list):
        pairs = tension
    elif isinstance(tension, dict):
        pairs_val = tension.get("pairs")
        if isinstance(pairs_val, list):
            pairs = pairs_val
        else:
            errors.append("'tension_matrix.pairs' must be a list of dictionaries")
    else:
        errors.append("'tension_matrix' must be a list of pairs or a dictionary with 'pairs'")

    if isinstance(pairs, list):
        for pidx, pair in enumerate(pairs):
            if not isinstance(pair, dict):
                errors.append(f"Tension pair #{pidx+1} must be a dictionary")
                continue
            between = pair.get("between")
            if not isinstance(between, list) or len(between) != 2:
                errors.append(f"Tension pair #{pidx+1} 'between' must be a list of exactly 2 persona IDs")
            elif not all(isinstance(x, str) for x in between):
                errors.append(f"Tension pair #{pidx+1} 'between' elements must be strings")
            else:
                for b_id in between:
                    if b_id not in persona_ids:
                        errors.append(f"Tension pair #{pidx+1} references unknown persona ID: '{b_id}'")
            dyn = pair.get("dynamic")
            if not isinstance(dyn, str) or not dyn.strip():
                errors.append(f"Tension pair #{pidx+1} missing required string 'dynamic'")

            app_modes = pair.get("applicable_modes")
            if app_modes is not None:
                if not isinstance(app_modes, list) or not all(isinstance(m, str) and m in ALLOWED_FORMAT_TYPES for m in app_modes):
                    errors.append(f"Tension pair #{pidx+1} 'applicable_modes' must be a list of valid canonical format types: {sorted(list(ALLOWED_FORMAT_TYPES))}")

    # 8. Narrative structure block: strictly 4 acts with act numbers {1, 2, 3, 4}
    narrative = data.get("narrative_structure")
    if not isinstance(narrative, dict):
        errors.append("'narrative_structure' section must be a dictionary")
    else:
        acts = narrative.get("acts")
        if not isinstance(acts, list):
            errors.append("'narrative_structure.acts' must be a list")
        elif len(acts) != 4:
            errors.append(f"'narrative_structure.acts' must contain exactly 4 acts for a 4-act narrative arc, got {len(acts)}")
        else:
            seen_acts = set()
            for aidx, act in enumerate(acts):
                if not isinstance(act, dict):
                    errors.append(f"Act #{aidx+1} must be a dictionary")
                    continue
                act_num = act.get("act")
                if isinstance(act_num, bool) or not isinstance(act_num, int):
                    errors.append(f"Act #{aidx+1} 'act' number must be an integer, got: {act_num}")
                elif act_num in seen_acts:
                    errors.append(f"Duplicate act number: {act_num}")
                else:
                    seen_acts.add(act_num)

                for af in ["name", "purpose"]:
                    val = act.get(af)
                    if not isinstance(val, str) or not val.strip():
                        errors.append(f"Act #{aidx+1} missing required string '{af}'")

            if seen_acts and seen_acts != {1, 2, 3, 4}:
                errors.append(f"Act numbers must be exactly {{1, 2, 3, 4}}, got {sorted(list(seen_acts))}")

    # 9. Routing block: strict path safety
    routing = data.get("routing")
    if not isinstance(routing, dict):
        errors.append("'routing' section must be a dictionary")
    else:
        required_routing_fields = [
            "vault_episodes_root",
            "vault_episodes_prefix",
            "notes_brand_path",
            "r2_object_prefix",
            "lavish_theme"
        ]
        for rf in required_routing_fields:
            rval = routing.get(rf)
            if not isinstance(rval, str) or not rval.strip():
                errors.append(f"Missing required routing field '{rf}'")
            elif ".." in rval or rval.startswith("/"):
                errors.append(f"Routing field '{rf}' contains unsafe path traversal or leading slash: '{rval}'")

        # Prefix must be clean basename prefix without slashes
        prefix = routing.get("vault_episodes_prefix")
        if isinstance(prefix, str) and ("/" in prefix or "\\" in prefix):
            errors.append(f"vault_episodes_prefix must be a clean basename prefix without slashes, got: '{prefix}'")

    return errors

def list_profiles():
    profiles = []
    has_errors = False
    if not os.path.exists(PROFILES_DIR):
        print(f"Directory not found: {PROFILES_DIR}", file=sys.stderr)
        return False

    for fname in sorted(os.listdir(PROFILES_DIR)):
        if fname.endswith(".yaml") and not fname.startswith("_"):
            path = os.path.join(PROFILES_DIR, fname)
            try:
                data = load_yaml(path)
                val_errs = validate_profile_dict(data, path)
                prof = data.get("profile", {}) if isinstance(data, dict) else {}
                fmt = data.get("format", {}) if isinstance(data, dict) else {}
                personas = data.get("personas", []) if isinstance(data, dict) else []
                persona_names = [p.get("name", "Unknown").split()[0] for p in personas if isinstance(p, dict)]
                
                status_note = ""
                if val_errs:
                    has_errors = True
                    status_note = f" (ERR: {len(val_errs)})"

                profiles.append({
                    "id": prof.get("id", fname[:-5]) + status_note,
                    "name": prof.get("name", "Unknown"),
                    "show_id": prof.get("show_id", "N/A"),
                    "type": fmt.get("type", "Unknown"),
                    "duration": f"{fmt.get('target_duration_minutes', 0)}m",
                    "personas": ", ".join(persona_names) or "None",
                    "file": fname
                })
            except Exception as e:
                has_errors = True
                profiles.append({
                    "id": fname[:-5] + " (FAIL)",
                    "name": f"ERROR: {e}",
                    "show_id": "N/A",
                    "type": "INVALID",
                    "duration": "N/A",
                    "personas": "N/A",
                    "file": fname
                })

    print(f"\n{'ID':<20} {'NAME':<32} {'TYPE':<25} {'DURATION':<10} {'PERSONAS'}")
    print("-" * 110)
    for p in profiles:
        print(f"{p['id']:<20} {p['name']:<32} {p['type']:<25} {p.get('duration','N/A'):<10} {p.get('personas','N/A')}")
    print("-" * 110)
    print(f"Total available profiles: {len(profiles)}\n")
    return not has_errors

def main():
    parser = argparse.ArgumentParser(description="Podcast Brand Profile Validator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all available profiles")
    group.add_argument("--profile", type=str, help="Validate profile by ID in profiles/ (alphanumeric and hyphens only)")
    group.add_argument("--file", type=str, help="Validate profile by explicit YAML file path")

    args = parser.parse_args()

    if args.list:
        success = list_profiles()
        sys.exit(0 if success else 1)

    target_file = None
    if args.profile:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.profile):
            print(f"❌ Invalid profile ID format '{args.profile}'. Must be lowercase alphanumeric with hyphens (e.g. 'geek-family').", file=sys.stderr)
            sys.exit(1)
        target_file = os.path.join(PROFILES_DIR, f"{args.profile}.yaml")
    elif args.file:
        target_file = args.file

    print(f"Inspecting profile: {target_file}")
    try:
        data = load_yaml(target_file)
        errors = validate_profile_dict(data, target_file)
        if errors:
            print("\n❌ Validation FAILED with errors:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            p = data.get("profile", {})
            fmt = data.get("format", {})
            personas = data.get("personas", [])
            print(f"\n✅ Profile '{p.get('id')}' is VALID!")
            print(f"  • Name:        {p.get('name')}")
            print(f"  • Show ID:     {p.get('show_id')}")
            print(f"  • Format Type: {fmt.get('type')} ({fmt.get('target_duration_minutes')} mins)")
            print(f"  • Personas:    {len(personas)} ({', '.join([x.get('name') for x in personas if isinstance(x, dict)])})")
            print(f"  • Vault Root:  {data.get('routing', {}).get('vault_episodes_root')}")
            print(f"  • R2 Prefix:   {data.get('routing', {}).get('r2_object_prefix')}")
            sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error loading profile: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
