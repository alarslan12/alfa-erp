"""Scope guard for ALFACOPYCENTER Suite's four independent workstreams.

Used on pull requests. Standard-library-only so the scope check runs before
dependency installation. It deliberately rejects cross-component edits and
package/version edits in feature branches.

Usage:
    python tools/check_workstream.py --branch feature/banner-example \
        --base <base-sha> --head <head-sha>
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

AREAS = ("erp", "banner", "mobile", "print")
RELEASE_FILES = {
    "ALFACOPYCENTER_Suite.iss",
    "ALFA_BUILD_SUITE_WINDOWS.ps1",
    "ALFA_BUILD_WINDOWS.ps1",
    "README.md",
    "CHANGELOG.md",
    "surum_gecmisi.py",
    "firebase/database.rules.json",
    "firebase/firebase.json",
    "firebase/.firebaserc",
}
RELEASE_PREFIXES = (
    ".github/",
    "docs/ALFACOPYCENTER_SUITE_V",
    "docs/WORKSTREAM_",
    "docs/RELEASE_COORDINATION",
    "tools/check_workstream.py",
    "tools/check_release_consistency.py",
)
OWNER_DOCS = {area: f"docs/workstreams/{area.upper()}.md" for area in AREAS}


def _run(*args: str) -> str:
    result = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout


def changed_paths(base: str, head: str) -> list[str]:
    data = _run("git", "diff", "--name-only", "--diff-filter=ACDMR",
                f"{base}...{head}")
    return [line.strip().replace("\\", "/") for line in data.splitlines()
            if line.strip()]


def classify(path: str) -> str:
    """Classify only known component paths; unknown paths require integration."""
    if path in RELEASE_FILES or any(path.startswith(x) for x in RELEASE_PREFIXES):
        return "integration"
    if path == "firebase.json":
        return "mobile"
    if path.startswith("docs/workstreams/"):
        for area, exact in OWNER_DOCS.items():
            if path == exact:
                return area
        return "integration"
    if path.startswith("banner_studio/"):
        return "banner"
    if path.startswith("mobil_panel/") or path == "mobil_siparis_donusum.py":
        return "mobile"
    if path.startswith("tools/firebase_mobile_"):
        return "mobile"
    if path.startswith("alfa_print_") or path in (
        "ekran_yazdirma.py", "ekran_baski_plani.py",
        "tools/test_print_contract.py",
    ):
        return "print"
    if path.startswith("tests/"):
        name = Path(path).name.lower()
        if "banner" in name:
            return "banner"
        if "print" in name or "spool" in name:
            return "print"
        if "mobile" in name or "mobil" in name:
            return "mobile"
        return "erp"
    if path == "main.py" or path.startswith(("ekran_", "flexflow",
                                            "siparis", "analitik_", "muhasebe_",
                                            "katalog", "firebase_", "db")):
        return "erp"
    if path.startswith(("kart_", "editor_", "temali_", "alfa_rtdb")):
        return "erp"
    if path in (
        "tema.py", "takvim.py", "widgets.py", "utils.py",
        "urun_katalogu.py", "kargo_ucreti.py", "iade_nedeni.py",
        "alfa_guncelleme.py", "alfa_hatalar.py", "ayar_yonetimi.py",
    ):
        return "erp"
    return "integration"


def workstream(branch: str) -> str:
    for area in AREAS:
        if branch.startswith((f"feature/{area}-", f"fix/{area}-")):
            return area
    if branch.startswith("integration/release-"):
        return "release"
    if branch.startswith("integration/"):
        return "integration"
    if branch.startswith("chore/coordination-"):
        return "coordination"
    return ""


def _version_change_forbidden(base: str, head: str, paths: list[str]) -> list[str]:
    targets = {
        "main.py": r"^[-+](?![-+]).*?\bVERSION\s*=",
        "banner_studio/studio_server.py":
            r"^[-+](?![-+]).*?\bSUITE_VERSION\s*=",
    }
    problems = []
    for path in targets:
        if path not in paths:
            continue
        diff = _run("git", "diff", "--unified=0", base, head, "--", path)
        if re.search(targets[path], diff, re.MULTILINE):
            problems.append(f"{path}: Suite version constant is release-only")
    return problems


def validate(branch: str, base: str, head: str) -> list[str]:
    area = workstream(branch)
    if not area:
        return ["Branch name must start with feature/{erp,banner,mobile,print}-,"
                " fix/{erp,banner,mobile,print}-, integration/, or"
                " chore/coordination-."]
    paths = changed_paths(base, head)
    if not paths:
        return ["No changed files in pull request."]
    if area in ("integration", "release"):
        if area == "release" and "ALFACOPYCENTER_Suite.iss" not in paths:
            return ["Release PR must update ALFACOPYCENTER_Suite.iss once."]
        return []
    if area == "coordination":
        allowed = [
            p for p in paths
            if not (p.startswith(("docs/", "tools/check_", ".github/workflows/")))
        ]
        return [f"Coordination branch cannot modify application file: {p}"
                for p in allowed]
    issues = [f"Out-of-scope for {area}: {p} (owner: {classify(p)})"
              for p in paths if classify(p) != area]
    if OWNER_DOCS[area] not in paths or not Path(OWNER_DOCS[area]).is_file():
        issues.append("Workstream PR must keep and update its own status file: "
                      + OWNER_DOCS[area])
    issues.extend(_version_change_forbidden(base, head, paths))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    try:
        errors = validate(args.branch, args.base, args.head)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Cannot inspect git diff: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("WORKSTREAM SCOPE FAILED:")
        for error in errors:
            print(" - " + error)
        return 1
    print("WORKSTREAM SCOPE OK:", args.branch, "(", args.base[:8],
          "→", args.head[:8], ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
