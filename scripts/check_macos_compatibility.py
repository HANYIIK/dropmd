import argparse
from pathlib import Path
import plistlib
import re
import subprocess
import sys


MACHO_MAGICS = {
    bytes.fromhex(value)
    for value in ("feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca")
}


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+(?:\.\d+){0,2}", value):
        raise ValueError(f"Invalid macOS version: {value!r}")
    parts = tuple(map(int, value.split(".")))
    return parts + (0,) * (3 - len(parts))


def minimum_versions(output):
    architectures = set()
    found = []
    architecture = "native"
    command = None
    for line in output.splitlines():
        match = re.search(r"\(architecture ([^)]+)\):$", line)
        if match:
            architecture = match.group(1)
            architectures.add(architecture)
            command = None
        fields = line.split()
        if len(fields) != 2:
            continue
        key, value = fields
        if key == "cmd":
            command = value
        elif (command == "LC_BUILD_VERSION" and key == "minos") or (
            command == "LC_VERSION_MIN_MACOSX" and key == "version"
        ):
            version_tuple(value)
            found.append((architecture, value))
    missing = (architectures or {"native"}) - {architecture for architecture, _ in found}
    if missing:
        raise ValueError(f"Missing macOS deployment target for architecture(s): {', '.join(sorted(missing))}")
    return found


def run_tool(arguments):
    return subprocess.run(arguments, check=True, capture_output=True, text=True, timeout=30).stdout


def macho_files(app):
    seen = set()
    for path in sorted(app.rglob("*")):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        with path.open("rb") as stream:
            magic = stream.read(4)
        if magic in MACHO_MAGICS and "Mach-O" in run_tool(["file", "-b", str(resolved)]):
            yield path


def check_app(app):
    with (app / "Contents/Info.plist").open("rb") as stream:
        minimum = plistlib.load(stream)["LSMinimumSystemVersion"]
    declared = version_tuple(minimum)
    violations = []
    count = 0
    for path in macho_files(app):
        count += 1
        try:
            versions = minimum_versions(run_tool(["otool", "-l", str(path.resolve())]))
        except ValueError as error:
            raise ValueError(f"{path.relative_to(app).as_posix()}: {error}") from error
        for architecture, required in versions:
            if version_tuple(required) > declared:
                violations.append(f"{path.relative_to(app).as_posix()} ({architecture}) requires macOS {required}")
    if not count:
        raise ValueError("No Mach-O binaries found in the app bundle")
    return minimum, count, violations


def main():
    parser = argparse.ArgumentParser(description="Reject app bundles that require a newer macOS than they declare.")
    parser.add_argument("app", type=Path)
    arguments = parser.parse_args()
    try:
        minimum, count, violations = check_app(arguments.app)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"macOS compatibility check failed: {error}", file=sys.stderr)
        return 1
    if violations:
        print(f"macOS compatibility check failed: app declares {minimum}; {len(violations)} incompatible deployment targets:", file=sys.stderr)
        for violation in violations[:10]:
            print(f"- {violation}", file=sys.stderr)
        if len(violations) > 10:
            print(f"- ... and {len(violations) - 10} more", file=sys.stderr)
        return 1
    print(f"macOS compatibility check passed: {count} Mach-O files support declared macOS {minimum}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
