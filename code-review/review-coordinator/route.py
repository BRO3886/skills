#!/usr/bin/env python3
"""Deterministic router for the review-coordinator skill.

Given the set of changed files (and a few signals), decide which review
lenses apply, then detect which lens skills are actually installed on this
machine so the coordinator can run a best-effort review and tell the user
what is missing.

The classification logic is pure and importable so the eval harness can test
it without touching the filesystem or an LLM.

Usage:
  route.py --files a.go b.dart            # classify an explicit file list
  route.py --base main                    # derive files from `git diff --name-only base...HEAD`
  route.py --files a.go --bugfix          # mark this as a bug/regression fix
  route.py --files a.go --json            # machine-readable plan (default is also json)
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from glob import glob

# --- lens registry -----------------------------------------------------------
# Each lens maps to candidate skill directory names in priority order. The
# coordinator runs the first available candidate. provenance/install are shown
# to the user when a lens is unavailable so the shared skill degrades honestly.
LENS_REGISTRY = {
    "correctness": {
        "candidates": [],  # built into the coordinator: an adversarial subagent, no external skill
        "provenance": "built-in (coordinator)",
        "install": None,
        "always_on": True,
        "what": "Adversarial bug-hunt + verify the claim; default stance: find reasons NOT to merge.",
    },
    "tests": {
        "candidates": ["run-tests", "test-runner"],
        "provenance": "repo-local, else coordinator auto-detects the test command",
        "install": "Provide a repo run-tests skill, or rely on auto-detected make/npm/go/dotnet test.",
        "always_on": True,
        "what": "Run the suite and print the exit code. No green run, no merge-safe verdict.",
    },
    "security": {
        "candidates": ["security-lens", "security-review"],
        "provenance": "optional installed skill",
        "install": "Install a repository-grounded security review skill in an agent-visible skill root.",
        "always_on": True,
        "what": "Review security-sensitive behavior against the repository's actual enforcement mechanisms.",
    },
    "quality": {
        "candidates": ["code-quality-review", "maintainability-review"],
        "provenance": "optional installed skill",
        "install": "Install a code-quality or maintainability review skill in an agent-visible skill root.",
        "always_on": False,
        "what": "Strict maintainability / abstraction / spaghetti / 1k-line-file audit.",
    },
    "pr-conventions": {
        "candidates": ["review-pr", "review-changes", "review-feature"],
        "provenance": "repo-local",
        "install": "Add a repo-local review-pr / review-changes skill.",
        "always_on": False,
        "what": "Project conventions + logical soundness via the repo's own reviewer.",
    },
    "architecture": {
        "candidates": ["architecture-review", "codebase-architecture"],
        "provenance": "optional installed skill",
        "install": "Install an architecture review skill in an agent-visible skill root.",
        "always_on": False,
        "what": "Deepening / structural opportunities. Auto-added on security-critical diffs.",
    },
    "diagnose": {
        "candidates": ["diagnose"],
        "provenance": "optional installed skill",
        "install": "Install the diagnose skill.",
        "always_on": False,
        "what": "Disciplined bug/perf diagnosis loop. Added when the diff is a bug/regression fix.",
    },
    "go": {
        "candidates": ["go-review", "go-conventions", "go-best-practices"],
        "provenance": "optional installed skill",
        "install": "Install a Go review or conventions skill in an agent-visible skill root.",
        "always_on": False,
        "what": "Go backend conventions + architecture patterns.",
    },
    "flutter": {
        "candidates": ["flutter-review", "flutter-conventions", "dart-best-practices"],
        "provenance": "optional installed skill",
        "install": "Install a Flutter or Dart review skill in an agent-visible skill root.",
        "always_on": False,
        "what": "Flutter/Dart app conventions + architecture patterns.",
    },
    "frontend": {
        "candidates": ["make-interfaces-feel-better"],
        "provenance": "optional installed skill",
        "install": "Install the make-interfaces-feel-better skill.",
        "always_on": False,
        "what": "Design-engineering polish for UI components, animations, interaction states.",
    },
    "docs": {
        "candidates": ["documentation-review", "technical-writing-review"],
        "provenance": "optional installed skill",
        "install": "Install a documentation review skill in an agent-visible skill root.",
        "always_on": False,
        "what": "Detect AI-slop writing patterns in docs/markdown/copy.",
    },
}

# --- classification ----------------------------------------------------------
CODE_EXTS = {
    ".go", ".dart", ".ts", ".tsx", ".js", ".jsx", ".py", ".cs", ".java", ".kt",
    ".rb", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".swift", ".scala", ".php",
    ".vue", ".svelte", ".css", ".scss", ".sql",
}
DOC_EXTS = {".md", ".mdx", ".txt", ".rst"}
FRONTEND_EXTS = {".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss"}

SECURITY_PATH_TOKENS = (
    "crypto", "encrypt", "decrypt", "backup", "secret", "auth", "token",
    "hipaa", "pii", "password", "/keys", "keystore", "kms", "cipher",
)


def _ext(path: str) -> str:
    base = os.path.basename(path).lower()
    dot = base.rfind(".")
    return base[dot:] if dot != -1 else ""


def classify(files, bugfix=False):
    """Pure: changed files -> set of category tags. No I/O."""
    files = [f for f in files if f and f.strip()]
    exts = {_ext(f) for f in files}
    lowered = [f.lower() for f in files]
    names = {os.path.basename(f).lower() for f in files}

    has_code = bool(exts & CODE_EXTS)
    has_docs = bool(exts & DOC_EXTS)

    tags = set()
    if has_docs:
        tags.add("docs")

    if has_code:
        tags.update({"correctness", "tests", "security", "quality", "pr-conventions"})
        if ".go" in exts:
            tags.add("go")
        if ".dart" in exts or "pubspec.yaml" in names:
            tags.add("flutter")
        if exts & FRONTEND_EXTS:
            tags.add("frontend")
        if any(tok in p for p in lowered for tok in SECURITY_PATH_TOKENS):
            tags.add("architecture")  # elevate scrutiny; correctness already on
        if bugfix:
            tags.add("diagnose")

    return tags


def plan_lenses(files, bugfix=False):
    """Return the ordered list of planned lens keys for a changeset."""
    tags = classify(files, bugfix=bugfix)
    ordered = [k for k in LENS_REGISTRY if k in tags]
    return ordered, tags


# --- availability detection --------------------------------------------------
def _skill_search_roots():
    roots = [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    for variable in ("AGENT_SKILL_DIRS", "SKILL_DIRS"):
        roots.extend(os.path.expanduser(p) for p in os.environ.get(variable, "").split(os.pathsep) if p)
    for agent_root in ("AGENT_HOME", "CODEX_HOME"):
        if os.environ.get(agent_root):
            roots.append(os.path.join(os.path.expanduser(os.environ[agent_root]), "skills"))
    roots.extend([
        os.path.expanduser("~/.agents/skills"),
        os.path.expanduser("~/.codex/skills"),
        os.path.join(os.getcwd(), ".agents", "skills"),
        os.path.join(os.getcwd(), ".codex", "skills"),
    ])
    roots += glob(os.path.expanduser("~/.agents/plugins/**/skills"), recursive=True)
    roots += glob(os.path.expanduser("~/.codex/plugins/**/skills"), recursive=True)
    return list(dict.fromkeys(r for r in roots if os.path.isdir(r)))


def detect_skill(name):
    """Return the path to an installed skill dir by name, or None."""
    for root in _skill_search_roots():
        cand = os.path.join(root, name, "SKILL.md")
        if os.path.isfile(cand):
            return os.path.dirname(cand)
        hits = glob(os.path.join(root, "**", name, "SKILL.md"), recursive=True)
        if hits:
            return os.path.dirname(hits[0])
    return None


def resolve(lens_keys):
    available, skipped = [], []
    for key in lens_keys:
        reg = LENS_REGISTRY[key]
        if not reg["candidates"]:
            available.append({"lens": key, "skill": None, "via": reg["provenance"], "what": reg["what"]})
            continue
        found = None
        for cand in reg["candidates"]:
            path = detect_skill(cand)
            if path:
                found = (cand, path)
                break
        if found:
            available.append({"lens": key, "skill": found[0], "location": found[1],
                              "via": reg["provenance"], "what": reg["what"]})
        else:
            skipped.append({"lens": key, "reason": "no installed skill found",
                            "candidates": reg["candidates"], "provenance": reg["provenance"],
                            "install": reg["install"]})
    return available, skipped


# --- cli ---------------------------------------------------------------------
def _git_files(base):
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True, text=True, check=True,
        )
        return [l for l in out.stdout.splitlines() if l.strip()]
    except Exception as e:  # noqa: BLE001
        print(f"warning: could not derive files from git ({e})", file=sys.stderr)
        return []


def main():
    ap = argparse.ArgumentParser(description="Plan review lenses for a changeset.")
    ap.add_argument("--files", help="comma- or newline-separated changed files")
    ap.add_argument("--base", default="main", help="git base ref (default: main)")
    ap.add_argument("--target", default="", help="human label for what's being reviewed")
    ap.add_argument("--bugfix", action="store_true", help="this diff fixes a bug/regression")
    ap.add_argument("--json", action="store_true", help="json output (default)")
    args = ap.parse_args()

    if args.files:
        sep = "\n" if "\n" in args.files else ","
        files = [f.strip() for f in args.files.split(sep) if f.strip()]
    else:
        files = _git_files(args.base)

    lens_keys, tags = plan_lenses(files, bugfix=args.bugfix)
    available, skipped = resolve(lens_keys)

    plan = {
        "target": args.target or (f"git diff {args.base}...HEAD" if not args.files else "explicit file list"),
        "changed_files": files,
        "categories": sorted(tags),
        "lenses_available": available,
        "lenses_skipped": skipped,
        "note": "lenses_skipped are NOT errors — review proceeds best-effort with what's available.",
    }
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
