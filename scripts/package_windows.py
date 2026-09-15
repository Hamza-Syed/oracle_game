"""Zip the existing one-folder build and write its SHA-256 checksum."""

import hashlib
from pathlib import Path
import zipfile


def main():
    project = Path(__file__).resolve().parent.parent
    version = (project / "VERSION").read_text(encoding="utf-8").strip()
    source = project / "dist" / "TheOracle"
    if not (source / "TheOracle.exe").is_file():
        raise SystemExit("Build TheOracle.spec before packaging.")
    name = f"TheOracle-v{version}-Windows"
    archive = project / "dist" / f"{name}.zip"
    files = sorted(path for path in source.rglob("*") if path.is_file())
    for path in files:
        relative = path.relative_to(source)
        if (path.name == "memory.json" or path.name.startswith("memory.corrupt")
                or path.suffix == ".tmp" or any(part in {".git", ".venv", "tests", "__pycache__"}
                                               for part in relative.parts)):
            raise SystemExit(f"Unexpected developer/runtime data in build: {relative}")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in files:
            zipped.write(path, f"{name}/{path.relative_to(source).as_posix()}")
    with archive.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    checksum = archive.with_suffix(".sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(f"ZIP: {archive}\nBytes: {archive.stat().st_size}\nSHA-256: {digest}")


if __name__ == "__main__":
    main()
