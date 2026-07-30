#!/usr/bin/env python3
"""Inventory a local ITR intake directory without parsing document contents."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATEGORY_HINTS = {
    "acknowledgement-or-prior-return": ("ack", "acknowledg", "itr-v", "prior-itr", "return"),
    "ais-tis-26as": ("ais", "tis", "26as"),
    "bank-or-interest": ("bank", "statement", "interest", "fd", "rd", "deposit"),
    "capital-gains-or-broker": (
        "capital-gain",
        "capital_gain",
        "broker",
        "stocks",
        "pnl",
        "tradebook",
        "demat",
        "cas",
        "mutual",
    ),
    "deduction": (
        "80c",
        "80d",
        "80g",
        "nps",
        "insurance",
        "donation",
        "tuition",
        "medical",
    ),
    "dividend": ("dividend",),
    "foreign": ("foreign", "overseas", "rsu", "esop", "form67", "form-67"),
    "house-property": ("rent", "property", "home-loan", "housing-loan", "municipal"),
    "salary-or-pension": ("form16", "form-16", "salary", "payslip", "pension"),
    "tax-payment-or-tds": ("challan", "tds", "tcs", "form16a", "form-16a", "advance-tax"),
    "vda-or-crypto": ("crypto", "vda", "bitcoin", "ethereum", "token", "nft"),
}

SUPPORTED_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".heic",
    ".jpeg",
    ".jpg",
    ".json",
    ".ods",
    ".pdf",
    ".png",
    ".txt",
    ".xls",
    ".xlsb",
    ".xlsm",
    ".xlsx",
    ".xml",
    ".zip",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local manifest of an ITR document intake directory."
    )
    parser.add_argument("directory", type=Path, help="Intake directory to inventory")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--no-hash",
        action="store_true",
        help="Skip SHA-256 calculation",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def category_hint(relative_path: str) -> str:
    normalized = relative_path.lower()
    matches = [
        category
        for category, hints in CATEGORY_HINTS.items()
        if any(hint in normalized for hint in hints)
    ]
    return ",".join(matches) if matches else "unclassified"


def inventory(root: Path, include_hash: bool) -> dict[str, Any]:
    resolved = root.expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"Directory does not exist: {resolved}")
    if not resolved.is_dir():
        raise SystemExit(f"Not a directory: {resolved}")

    files: list[dict[str, Any]] = []
    skipped_symlinks: list[str] = []

    for path in sorted(resolved.rglob("*")):
        relative = path.relative_to(resolved).as_posix()
        if path.is_symlink():
            skipped_symlinks.append(relative)
            continue
        if not path.is_file() or any(part.startswith(".") for part in path.relative_to(resolved).parts):
            continue

        stat = path.stat()
        extension = path.suffix.lower()
        item: dict[str, Any] = {
            "path": relative,
            "extension": extension or "(none)",
            "size_bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(
                stat.st_mtime, timezone.utc
            ).isoformat(timespec="seconds"),
            "category_hint": category_hint(relative),
            "supported_extension": extension in SUPPORTED_EXTENSIONS,
        }
        if include_hash:
            item["sha256"] = sha256(path)
        files.append(item)

    duplicate_groups: list[list[str]] = []
    if include_hash:
        by_hash: dict[str, list[str]] = defaultdict(list)
        for item in files:
            by_hash[item["sha256"]].append(item["path"])
        duplicate_groups = [
            paths for paths in by_hash.values() if len(paths) > 1
        ]

    return {
        "root": str(resolved),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file_count": len(files),
        "total_bytes": sum(item["size_bytes"] for item in files),
        "category_counts": dict(
            sorted(Counter(item["category_hint"] for item in files).items())
        ),
        "unsupported_files": [
            item["path"] for item in files if not item["supported_extension"]
        ],
        "skipped_symlinks": skipped_symlinks,
        "duplicate_groups": duplicate_groups,
        "files": files,
        "notice": "Category values are filename hints only; inspect file contents.",
    }


def escape_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# ITR intake inventory",
        "",
        f"- Root: `{manifest['root']}`",
        f"- Files: {manifest['file_count']}",
        f"- Total bytes: {manifest['total_bytes']}",
        f"- Generated UTC: {manifest['generated_utc']}",
        f"- Notice: {manifest['notice']}",
        "",
        "## Files",
        "",
        "| Path | Hint | Extension | Bytes | Modified UTC | SHA-256 |",
        "|---|---|---:|---:|---|---|",
    ]
    for item in manifest["files"]:
        digest = item.get("sha256", "(skipped)")
        lines.append(
            "| "
            + " | ".join(
                escape_cell(value)
                for value in (
                    item["path"],
                    item["category_hint"],
                    item["extension"],
                    item["size_bytes"],
                    item["modified_utc"],
                    digest,
                )
            )
            + " |"
        )

    lines.extend(["", "## Completeness signals", ""])
    if manifest["unsupported_files"]:
        lines.append(
            "- Unsupported extensions: "
            + ", ".join(f"`{path}`" for path in manifest["unsupported_files"])
        )
    else:
        lines.append("- Unsupported extensions: none")

    if manifest["skipped_symlinks"]:
        lines.append(
            "- Skipped symlinks: "
            + ", ".join(f"`{path}`" for path in manifest["skipped_symlinks"])
        )
    else:
        lines.append("- Skipped symlinks: none")

    if manifest["duplicate_groups"]:
        lines.append("- Duplicate-content groups:")
        for group in manifest["duplicate_groups"]:
            lines.append("  - " + ", ".join(f"`{path}`" for path in group))
    else:
        lines.append("- Duplicate-content groups: none detected")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    manifest = inventory(args.directory, include_hash=not args.no_hash)
    if args.format == "json":
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(render_markdown(manifest))


if __name__ == "__main__":
    main()
