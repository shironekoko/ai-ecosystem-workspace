"""
Create example projects in Label Studio with sample tasks.

This script creates 3 example projects, each with a different labeling
template and sample data, so you have something to list afterwards.

Usage:
    python core/label_studio_setup.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.label_studio_client import get_client


# ---------------------------------------------------------------------------
# Labeling config templates
# ---------------------------------------------------------------------------
SENTIMENT_CONFIG = """
<View>
  <Header value="Classify the sentiment of the text:"/>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text" choice="single" showInLine="true">
    <Choice value="Positive"/>
    <Choice value="Negative"/>
    <Choice value="Neutral"/>
  </Choices>
</View>
""".strip()

NER_CONFIG = """
<View>
  <Labels name="label" toName="text">
    <Label value="Person" background="red"/>
    <Label value="Organization" background="blue"/>
    <Label value="Location" background="green"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
""".strip()

IMAGE_CONFIG = """
<View>
  <Image name="image" value="$image"/>
  <Choices name="choice" toName="image" choice="single">
    <Choice value="Cat"/>
    <Choice value="Dog"/>
    <Choice value="Other"/>
  </Choices>
</View>
""".strip()

# ---------------------------------------------------------------------------
# Sample tasks for each project
# ---------------------------------------------------------------------------
SENTIMENT_TASKS = [
    {"data": {"text": "I love this product! It works perfectly."}},
    {"data": {"text": "Terrible experience, will never buy again."}},
    {"data": {"text": "The weather today is partly cloudy."}},
    {"data": {"text": "Best purchase I have made this year!"}},
    {"data": {"text": "The delivery was late and the box was damaged."}},
]

NER_TASKS = [
    {"data": {"text": "Elon Musk announced that Tesla will open a new factory in Berlin."}},
    {"data": {"text": "Google CEO Sundar Pichai spoke at the conference in San Francisco."}},
    {"data": {"text": "The United Nations held a meeting in New York last Friday."}},
    {"data": {"text": "Dr. Somchai works at Chulalongkorn University in Bangkok."}},
]

IMAGE_TASKS = [
    {"data": {"image": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/1200px-Cat_November_2010-1a.jpg"}},
    {"data": {"image": "https://upload.wikimedia.org/wikipedia/commons/2/26/YellowLabradorLooking_new.jpg"}},
    {"data": {"image": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Image_created_with_a_mobile_phone.png/1200px-Image_created_with_a_mobile_phone.png"}},
]

# ---------------------------------------------------------------------------
# Project definitions
# ---------------------------------------------------------------------------
PROJECTS = [
    {
        "title": "Sentiment Analysis",
        "description": "Classify text as Positive / Negative / Neutral",
        "label_config": SENTIMENT_CONFIG,
        "tasks": SENTIMENT_TASKS,
    },
    {
        "title": "Named Entity Recognition",
        "description": "Tag Person, Organization, Location in text",
        "label_config": NER_CONFIG,
        "tasks": NER_TASKS,
    },
    {
        "title": "Image Classification",
        "description": "Classify images as Cat / Dog / Other",
        "label_config": IMAGE_CONFIG,
        "tasks": IMAGE_TASKS,
    },
]


def setup(ls=None):
    ls = ls or get_client()

    print("=== Creating example projects in Label Studio ===\n")

    for proj_def in PROJECTS:
        # Create project
        project = ls.projects.create(
            title=proj_def["title"],
            description=proj_def["description"],
            label_config=proj_def["label_config"],
        )
        print(f"  [OK] Project created: id={project.id}  title={project.title}")

        # Import tasks
        ls.projects.import_tasks(
            id=project.id,
            request=proj_def["tasks"],
        )
        print(f"       Imported {len(proj_def['tasks'])} task(s)")
        print()

    print("Done! 3 projects created with sample tasks.")
    print("Run:  python -m core.label_studio_projects   to list them.")


if __name__ == "__main__":
    setup()
