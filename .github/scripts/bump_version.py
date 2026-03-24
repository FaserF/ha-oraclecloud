import json
import re
import subprocess
import sys


def get_latest_tag():
    try:
        result = subprocess.run(
            ["git", "tag", "--list", "--sort=-v:refname"],
            capture_output=True,
            text=True,
            check=True,
        )
        tags = result.stdout.strip().split("\n")
        return tags[0] if tags and tags[0] else None
    except Exception:
        return None


def parse_version(v_str):
    core = v_str.split("-")[0]
    parts = list(map(int, core.split(".")))
    while len(parts) < 3:
        parts.append(0)
    is_beta = "-" in v_str and "beta" in v_str
    beta_num = -1
    if is_beta:
        match = re.search(r"beta\.(\d+)", v_str)
        if match:
            beta_num = int(match.group(1))
    return parts[0], parts[1], parts[2], is_beta, beta_num


def bump_version(current, bump_type, release_status):
    is_target_beta = release_status == "beta"
    if not current:
        return "1.0.0-beta.0" if is_target_beta else "1.0.0"

    major, minor, patch, is_curr_beta, curr_beta_num = parse_version(current)

    if bump_type == "major":
        next_core = (major + 1, 0, 0)
    elif bump_type == "minor":
        next_core = (major, minor + 1, 0)
    else:
        next_core = (major, minor, patch + 1)

    core_str = f"{next_core[0]}.{next_core[1]}.{next_core[2]}"
    if is_target_beta:
        if (major, minor, patch) == next_core and is_curr_beta:
            return f"{core_str}-beta.{curr_beta_num + 1}"
        return f"{core_str}-beta.0"
    return core_str


def update_files(new_version):
    # pyproject.toml
    with open("pyproject.toml") as f:
        content = f.read()
    content = re.sub(
        r'version\s*=\s*"[^"]+"', f'version = "{new_version}"', content, count=1
    )
    with open("pyproject.toml", "w") as f:
        f.write(content)

    # manifest.json
    manifest_path = "custom_components/oraclecloud/manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    manifest["version"] = new_version
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    b_type = sys.argv[1]
    r_status = sys.argv[2]
    latest = get_latest_tag()
    current = latest.lstrip("v") if latest else None
    new_v = bump_version(current, b_type, r_status)
    update_files(new_v)
    with open("VERSION.txt", "w") as f:
        f.write(new_v)
