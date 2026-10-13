"""Check the direct dependencies against their newest releases on PyPI.

Fails when the newest release of a runtime dependency falls outside the range that
pyproject.toml allows, or when the lowest-dependencies CI job doesn't pin the lower
bounds of pyproject.toml. Warns when uv.lock lags behind a newer allowed release.

    uv run --no-project --with packaging python scripts/check_dependencies.py
"""

import json
import re
import sys
import tomllib
import urllib.request
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parent.parent
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
# shared with the test tools, which need newer versions than our lower bound
NOT_PINNED_IN_LOWEST_JOB = {"typing-extensions"}

problems: list[str] = []


def error(message: str) -> None:
    problems.append(message)
    print(f"::error::{message}")


def warning(message: str) -> None:
    print(f"::warning::{message}")


def releases(name: str) -> dict[Version, list[dict]]:
    url = f"https://pypi.org/pypi/{name}/json"
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.load(response)
    result = {}
    for raw_version, files in data["releases"].items():
        try:
            version = Version(raw_version)
        except InvalidVersion:
            continue
        files = [file for file in files if not file["yanked"]]
        if files and not version.is_prerelease:
            result[version] = files
    return result


def supports_python(files: list[dict], python: Version) -> bool:
    return any(
        not file["requires_python"]
        or SpecifierSet(file["requires_python"]).contains(python)
        for file in files
    )


def locked_versions() -> dict[str, Version]:
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    versions: dict[str, Version] = {}
    for package in lock["package"]:
        if "version" in package:
            name = canonicalize_name(package["name"])
            version = Version(package["version"])
            versions[name] = max(version, versions.get(name, version))
    return versions


def lowest_job_pins() -> dict[str, Version]:
    pins = re.findall(
        r'--with "([A-Za-z0-9_.-]+)==([^"]+)"', TESTS_WORKFLOW.read_text()
    )
    return {canonicalize_name(name): Version(version) for name, version in pins}


def lower_bound(requirement: Requirement) -> Version | None:
    bounds = [
        Version(spec.version)
        for spec in requirement.specifier
        if spec.operator in (">=", "~=", "==")
    ]
    return max(bounds, default=None)


def main() -> int:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    runtime = [Requirement(req) for req in project["project"]["dependencies"]]
    dev = [Requirement(req) for req in project["dependency-groups"]["dev"]]
    # uv.lock has to satisfy the oldest supported Python too
    oldest_python = lower_bound(
        Requirement(f"python{project['project']['requires-python']}")
    )
    locked = locked_versions()

    for requirement in runtime + dev:
        available = releases(requirement.name)
        newest = max(available)
        if not requirement.specifier.contains(newest):
            error(
                f"{requirement.name} {newest} is out, but pyproject.toml allows "
                f"{requirement.specifier}: test it and widen the range"
            )
            continue
        lockable = [
            version
            for version, files in available.items()
            if requirement.specifier.contains(version)
            and (oldest_python is None or supports_python(files, oldest_python))
        ]
        newest_lockable = max(lockable, default=newest)
        lock_version = locked.get(canonicalize_name(requirement.name))
        if lock_version is not None and lock_version < newest_lockable:
            warning(
                f"uv.lock has {requirement.name} {lock_version}, {newest_lockable} is out: "
                f"uv lock --upgrade-package {requirement.name}"
            )

    pins = lowest_job_pins()
    for requirement in runtime:
        name = canonicalize_name(requirement.name)
        if name in NOT_PINNED_IN_LOWEST_JOB:
            continue
        bound = lower_bound(requirement)
        if pins.pop(name, None) != bound:
            error(
                f"the lowest-dependencies job in {TESTS_WORKFLOW.name} has to pin "
                f"{requirement.name}=={bound}, the lower bound in pyproject.toml"
            )
    for name in pins:
        error(
            f"the lowest-dependencies job pins {name}, which isn't a runtime dependency"
        )

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
