"""Expand the two local Iris includes without changing upstream model files.

Workaround for native sdformat 16.1.0 SDF_PATH parsing on Windows. This only
prepares a local world; it never starts Gazebo, SITL, or a flight.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Resolver:
    def __init__(self, models: Path):
        self.models = models.resolve(strict=True)
        self.sources: dict[Path, str] = {}
        self.expanded: list[dict] = []
        self.meshes: list[dict] = []

    def remember(self, path: Path) -> None:
        self.sources.setdefault(path, digest(path))

    def local_uri(self, uri: str) -> Path:
        if not uri.startswith("model://"):
            raise ValueError(f"Only local model:// URIs are allowed: {uri!r}")
        target = (self.models / uri[len("model://"):]).resolve(strict=True)
        if not target.is_relative_to(self.models):
            raise ValueError(f"URI escapes the local model root: {uri!r}")
        return target

    def expand(self, parent: ET.Element, chain: tuple[Path, ...] = ()) -> None:
        # Iterate over a snapshot because includes are replaced in place.
        for child in list(parent):
            if child.tag != "include":
                self.expand(child, chain)
                continue

            if child.get("merge", "false").lower() not in ("false", "0"):
                raise ValueError("Merged includes need different frame semantics")
            unexpected = {e.tag for e in child} - {"uri", "name", "pose"}
            if unexpected:
                raise ValueError(f"Unsupported include overrides: {unexpected}")
            uri = (child.findtext("uri") or "").strip()
            source = self.local_uri(uri)
            if source.is_dir():
                source = source / "model.sdf"
            source = source.resolve(strict=True)
            if source in chain:
                raise ValueError(f"Recursive model include: {source}")
            self.remember(source)
            imported = ET.parse(source).getroot()
            models = imported.findall("model")
            if imported.tag != "sdf" or len(models) != 1:
                raise ValueError(f"Expected exactly one SDF model: {source}")
            model = copy.deepcopy(models[0])

            name = child.findtext("name")
            if name is not None:
                model.set("name", name.strip())
            pose = child.find("pose")
            if pose is not None:
                for old in list(model.findall("pose")):
                    model.remove(old)
                model.insert(0, copy.deepcopy(pose))

            self.expand(model, chain + (source,))
            index = list(parent).index(child)
            model.tail = child.tail
            parent.remove(child)
            parent.insert(index, model)
            self.expanded.append({
                "uri": uri,
                "source": source.as_posix(),
                "model_name": model.get("name"),
                "pose": model.findtext("pose"),
            })

    def absolute_meshes(self, root: ET.Element) -> None:
        for element in root.findall(".//mesh/uri"):
            original = (element.text or "").strip()
            path = self.local_uri(original)
            if not path.is_file():
                raise ValueError(f"Mesh is not a file: {path}")
            element.text = path.as_posix()
            self.meshes.append({
                "original_uri": original,
                "absolute_path": element.text,
                "exists": True,
            })


def main() -> int:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
                        default=base / "iris.sdf")
    parser.add_argument("--models", type=Path,
                        default=base / ".local/ardupilot_gazebo/models")
    parser.add_argument("--output", type=Path,
                        default=base / ".local/iris.sdf")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    output = args.output.resolve()
    resolver = Resolver(args.models)
    resolver.remember(source)
    tree = ET.parse(source)
    root = tree.getroot()
    resolver.expand(root)
    resolver.absolute_meshes(root)

    if len(resolver.expanded) != 2:
        raise ValueError(f"Expected two Iris includes, got {len(resolver.expanded)}")
    if len(resolver.meshes) != 6:
        raise ValueError(f"Expected six mesh URI entries, got {len(resolver.meshes)}")
    if root.findall(".//include") or root.findall(".//uri") != root.findall(".//mesh/uri"):
        raise ValueError("Unresolved include or non-mesh resource URI remains")
    vehicle = root.find("./world/model[@name='iris_with_ardupilot']")
    if vehicle is None or vehicle.find("./model[@name='iris_with_standoffs']") is None:
        raise ValueError("Original nested model names were not preserved")
    plugin = vehicle.find("./plugin[@name='ArduPilotPlugin']")
    if plugin is None or plugin.findtext("fdm_addr") != "127.0.0.1" or plugin.findtext("fdm_port_in") != "9002":
        raise ValueError("Expected the local ArduPilot JSON physics connection")
    if vehicle.find("pose").attrib != {"degrees": "true"} or vehicle.findtext("pose") != "0 0 0.195 0 0 90":
        raise ValueError("Original include pose override was not preserved")
    if output == source or output.is_relative_to(resolver.models):
        raise ValueError("Output must not overwrite the source world or source models")

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(output, encoding="utf-8", xml_declaration=True)
    checked = ET.parse(output).getroot()
    if checked.findall(".//include"):
        raise ValueError("Written XML still contains include elements")
    for path, original_hash in resolver.sources.items():
        if digest(path) != original_hash:
            raise RuntimeError(f"Source unexpectedly changed: {path}")

    print(json.dumps({
        "status": "prepared_not_started",
        "output": output.as_posix(),
        "output_sha256": digest(output),
        "expanded_include_count": len(resolver.expanded),
        "remaining_include_count": len(checked.findall(".//include")),
        "nested_models_preserved": True,
        "expanded_models": resolver.expanded,
        "mesh_uri_count": len(resolver.meshes),
        "meshes": resolver.meshes,
        "json_bind": "127.0.0.1:9002",
        "source_hashes_unchanged": {p.as_posix(): h for p, h in resolver.sources.items()},
        "gazebo_or_sitl_started": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
