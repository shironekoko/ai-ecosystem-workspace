"""
List all tasks inside a chosen Label Studio project.

Usage:
    python core/label_studio_tasks.py          (uses first project)
    python core/label_studio_tasks.py 3        (project id = 3)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.label_studio_client import get_client


def list_tasks(project_id: int | None = None, ls=None):
    ls = ls or get_client()

    # If no project_id given, pick the first project
    if project_id is None:
        projects = list(ls.projects.list())
        if not projects:
            print("No projects found in Label Studio.")
            return
        project_id = projects[0].id
        print(f"(No project_id given -- using first project: id={project_id})\n")

    # Get project info
    project = ls.projects.get(id=project_id)
    print(f"=== Tasks in Project: {project.title} (id={project.id}) ===\n")

    # List tasks
    tasks = ls.tasks.list(project=project_id)

    count = 0
    for t in tasks:
        count += 1
        print(f"  Task ID      : {t.id}")
        print(f"  Data         : {t.data}")
        annotations = t.annotations if t.annotations else []
        print(f"  Annotations  : {len(annotations)}")
        print()

    if count == 0:
        print("  (no tasks in this project)")
    else:
        print(f"Total: {count} task(s)")


if __name__ == "__main__":
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else None
    list_tasks(pid)
