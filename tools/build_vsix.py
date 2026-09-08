"""Бастаи VS Code месозад — builds an installable .vsix, with no npm.

    py tools/build_vsix.py

A .vsix is a ZIP with three required pieces: a `[Content_Types].xml`, an
`extension.vsixmanifest`, and the extension itself under `extension/`. The
usual tool for producing one is `vsce`, which needs Node and a network. This
does the same job with the standard library, so anyone who has Python can
build and install the editor support — which, for a school in Dushanbe, is a
meaningfully lower bar.

Install the result with:

    code --install-extension tajiklang-<version>.vsix
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "editors" / "vscode"
OUTPUT_DIR = ROOT / "dist"

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="md" ContentType="text/markdown"/>
  <Default Extension="vsixmanifest" ContentType="text/xml"/>
  <Default Extension="png" ContentType="image/png"/>
</Types>
"""

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0"
    xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011"
    xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="{name}" Version="{version}"
              Publisher="{publisher}"/>
    <DisplayName>{display_name}</DisplayName>
    <Description xml:space="preserve">{description}</Description>
    <Tags>{tags}</Tags>
    <Categories>{categories}</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{engine}"/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value=""/>
      <Property Id="Microsoft.VisualStudio.Services.Links.Source"
                Value="{repository}"/>
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest"
           Path="extension/package.json" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details"
           Path="extension/README.md" Addressable="true"/>
  </Assets>
</PackageManifest>
"""


def _utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _utf8_stdout()

    package = json.loads((SOURCE / "package.json").read_text(encoding="utf-8"))
    version = package["version"]
    name = package["name"]
    publisher = package["publisher"]

    OUTPUT_DIR.mkdir(exist_ok=True)
    target = OUTPUT_DIR / f"{name}-{version}.vsix"

    manifest = MANIFEST.format(
        name=escape(name),
        version=escape(version),
        publisher=escape(publisher),
        display_name=escape(package.get("displayName", name)),
        description=escape(package.get("description", "")),
        tags=escape(",".join(package.get("keywords", []) or ["tajiklang"])),
        categories=escape(",".join(package.get("categories", ["Programming Languages"]))),
        engine=escape(package["engines"]["vscode"]),
        repository=escape("https://github.com/BahromPython/tajiklang-2.0.0"),
    )

    files = sorted(
        path for path in SOURCE.rglob("*") if path.is_file() and path.suffix != ".vsix"
    )

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("extension.vsixmanifest", manifest)
        for path in files:
            archive.write(path, "extension/" + path.relative_to(SOURCE).as_posix())

    size = target.stat().st_size / 1024
    print(f"{target.relative_to(ROOT)} — {len(files) + 2} entries, {size:.0f} KB")
    print()
    print("Насб кардан / Install:")
    print(f"    code --install-extension {target.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
