"""
List all projects in Label Studio and print summary info.

Usage:
    python core/label_studio_projects.py
    python -m core.label_studio_projects
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.label_studio_client import get_client


def list_projects(ls=None):
    ls = ls or get_client()
    projects = ls.projects.list()

    print("=== All Projects in Label Studio ===\n")

    count = 0
    for p in projects:
        count += 1
        print(f"  Project ID : {p.id}")
        print(f"  Title      : {p.title}")
        print(f"  Created    : {p.created_at}")
        print(f"  Tasks      : {p.task_number}")
        print(f"  Label cfg  : {(p.label_config or '')[:80]}...")
        print()

    if count == 0:
        print("  (no projects found)")
    else:
        print(f"Total: {count} project(s)")


if __name__ == "__main__":
    list_projects()
