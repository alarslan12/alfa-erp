"""Validate that the four-application Windows Suite publishes ONE version.

Run in PR CI and before constructing an installer. No external packages,
network access, or writes. Prevents a stale release tag from being silently
reused after multiple chats edit the same production branch.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def extract(path: str, expression: str) -> str:
    match = re.search(expression, text(path), re.MULTILINE)
    if match is None:
        raise ValueError(f"{path}: missing expected version field")
    return match.group(1)


def verify() -> list[str]:
    main_version = extract("main.py", r"^VERSION\s*=\s*['\"](\d+\.\d+\.\d+)['\"]")
    dotted = re.escape(main_version)
    underscored = main_version.replace(".", "_")
    compact = main_version.replace(".", "")
    expected_setup = f"ALFACOPYCENTER_Suite_Setup_V{underscored}.exe"
    errors = []

    rules = [
        ("banner_studio/studio_server.py",
         r"^SUITE_VERSION\s*=\s*['\"](\d+\.\d+\.\d+)['\"]",
         main_version),
        ("ALFACOPYCENTER_Suite.iss",
         r'^#define SuiteVersion\s+"(\d+\.\d+\.\d+)"',
         main_version),
        ("ALFACOPYCENTER_Suite.iss",
         r"^VersionInfoVersion=(\d+\.\d+\.\d+)\.0",
         main_version),
        ("ALFACOPYCENTER_Suite.iss",
         r"^OutputBaseFilename=(ALFACOPYCENTER_Suite_Setup_V\d+_\d+_\d+)",
         expected_setup.removesuffix(".exe")),
        ("ALFA_BUILD_SUITE_WINDOWS.ps1",
         r"(ALFACOPYCENTER_Suite_Setup_V\d+_\d+_\d+\.exe)",
         expected_setup),
        (".github/workflows/alfacopycenter-suite.yml",
         r"^\s*SUITE_TAG:\s*v(\d+\.\d+\.\d+)",
         main_version),
        (".github/workflows/alfacopycenter-suite.yml",
         r"^\s*SUITE_EXE:\s*(ALFACOPYCENTER_Suite_Setup_V\d+_\d+_\d+\.exe)",
         expected_setup),
        ("README.md", r"^# ALFACOPYCENTER Suite v(\d+\.\d+\.\d+)",
         main_version),
        ("surum_gecmisi.py",
         r'^\s*\("(\d+\.\d+\.\d+)",',
         main_version),
        ("CHANGELOG.md",
         r"^## \[v(\d+\.\d+\.\d+)\]",
         main_version),
        (".github/workflows/alfacopycenter-suite.yml",
         r"(docs/ALFACOPYCENTER_SUITE_V\d+_RELEASE\.md)",
         f"docs/ALFACOPYCENTER_SUITE_V{compact}_RELEASE.md"),
    ]
    for path, expression, wanted in rules:
        try:
            found = extract(path, expression)
            if found != wanted:
                errors.append(f"{path}: {found!r}, expected {wanted!r}")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    doc_path = ROOT / "docs" / f"ALFACOPYCENTER_SUITE_V{compact}_RELEASE.md"
    if not doc_path.is_file():
        errors.append(f"Release notes missing: {doc_path.relative_to(ROOT)}")
    if not main_version.startswith("2."):
        errors.append("Unified Suite must use v2.x version format")
    return errors


if __name__ == "__main__":
    issues = verify()
    if issues:
        print("SUITE RELEASE VERSION CHECK FAILED")
        for issue in issues:
            print(" - " + issue)
        sys.exit(1)
    print("SUITE RELEASE VERSION CHECK OK")
