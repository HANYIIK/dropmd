import importlib.util
from pathlib import Path
import plistlib

import pytest


spec = importlib.util.spec_from_file_location(
    "macos_compatibility", Path(__file__).parents[1] / "scripts/check_macos_compatibility.py"
)
compatibility = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compatibility)


@pytest.mark.parametrize("older,newer", [("9.9", "10.0"), ("13.9", "14"), ("14.1", "14.10"), ("14.0", "26.0")])
def test_versions_are_compared_numerically(older, newer):
    assert compatibility.version_tuple(older) < compatibility.version_tuple(newer)
    assert compatibility.version_tuple("14") == compatibility.version_tuple("14.0.0")


@pytest.mark.parametrize("value", [None, 14, "", "14.beta", "14.0.0.1"])
def test_invalid_versions_are_rejected(value):
    with pytest.raises(ValueError, match="Invalid macOS version"):
        compatibility.version_tuple(value)


def test_every_architecture_is_parsed_without_confusing_sdk_versions():
    output = """DropMD (architecture arm64):
Load command 8
      cmd LC_BUILD_VERSION
 platform 1
    minos 14.0
      sdk 26.2
DropMD (architecture x86_64):
Load command 9
      cmd LC_VERSION_MIN_MACOSX
  version 13.0
      sdk 15.0
"""
    assert compatibility.minimum_versions(output) == [("arm64", "14.0"), ("x86_64", "13.0")]


@pytest.mark.parametrize("output", ["", "cmd LC_UUID\nversion 14.0", "App (architecture arm64):\ncmd LC_BUILD_VERSION\nminos 14.0\nApp (architecture x86_64):\ncmd LC_UUID"])
def test_missing_architecture_targets_fail_closed(output):
    with pytest.raises(ValueError, match="Missing macOS deployment target"):
        compatibility.minimum_versions(output)


def make_app(tmp_path):
    app = tmp_path / "DropMD.app"
    contents = app / "Contents"
    contents.mkdir(parents=True)
    (contents / "Info.plist").write_bytes(plistlib.dumps({"LSMinimumSystemVersion": "14.0"}))
    (contents / "Python").write_bytes(bytes.fromhex("cffaedfe") + b"fake binary")
    return app


def test_scan_rejects_incompatible_python_and_ignores_non_macho(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    (app / "Contents/readme.txt").write_text("not a binary")
    (app / "Contents/Java.class").write_bytes(bytes.fromhex("cafebabe") + b"java bytecode")
    called = []

    def run_tool(arguments):
        called.append(arguments)
        if arguments[0] == "file":
            return "Java class data" if arguments[-1].endswith(".class") else "Mach-O 64-bit executable arm64"
        return "cmd LC_BUILD_VERSION\nminos 26.0\nsdk 26.2"

    monkeypatch.setattr(compatibility, "run_tool", run_tool)
    minimum, count, violations = compatibility.check_app(app)
    assert minimum == "14.0" and count == 1
    assert violations == ["Contents/Python (native) requires macOS 26.0"]
    assert [call[-1] for call in called if call[0] == "otool"] == [str(app / "Contents/Python")]


def test_compatible_bundle_passes_and_repeated_symlink_is_scanned_once(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    alias = app / "Contents/A-Python"
    try:
        alias.symlink_to("Python")
    except OSError:
        pytest.skip("Host does not permit creating symlinks")
    calls = []

    def run_tool(arguments):
        calls.append(arguments)
        if arguments[0] == "file":
            return "symbolic link to Python" if Path(arguments[-1]).is_symlink() else "Mach-O executable"
        return "cmd LC_BUILD_VERSION\nminos 14.0\nsdk 26.2"

    monkeypatch.setattr(compatibility, "run_tool", run_tool)
    assert compatibility.check_app(app) == ("14.0", 1, [])
    target = str((app / "Contents/Python").resolve())
    assert calls == [["file", "-b", target], ["otool", "-l", target]]


def test_one_incompatible_architecture_rejects_the_bundle(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    output = "App (architecture arm64):\ncmd LC_BUILD_VERSION\nminos 14.0\nApp (architecture x86_64):\ncmd LC_VERSION_MIN_MACOSX\nversion 15.0"
    monkeypatch.setattr(compatibility, "run_tool", lambda arguments: "Mach-O universal binary" if arguments[0] == "file" else output)
    assert compatibility.check_app(app)[2] == ["Contents/Python (x86_64) requires macOS 15.0"]


@pytest.mark.parametrize("violations,status", [([], 0), (["Python requires macOS 26.0"], 1)])
def test_cli_exit_status_blocks_incompatible_packages(monkeypatch, capsys, violations, status):
    monkeypatch.setattr(compatibility.sys, "argv", ["check_macos_compatibility.py", "DropMD.app"])
    monkeypatch.setattr(compatibility, "check_app", lambda app: ("14.0", 1, violations))
    assert compatibility.main() == status
    output = capsys.readouterr()
    assert "failed" in output.err if status else "passed" in output.out


def test_bundle_without_native_binaries_fails_closed(tmp_path):
    app = make_app(tmp_path)
    (app / "Contents/Python").write_text("not a binary")
    with pytest.raises(ValueError, match="No Mach-O binaries"):
        compatibility.check_app(app)
