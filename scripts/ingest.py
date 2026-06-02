#!/usr/bin/env python3
"""
Builds Firestore vector collections from case_studies.json and projects.json.

Prerequisites:
  1. Run `terraform apply` (creates the Firestore database)
  2. Create vector indexes (one-time, see below)
  3. Set GEMINI_API_KEY and GCP_PROJECT_ID in .env

Create vector indexes before first run:
    gcloud alpha firestore indexes composite create \
      --project=$GCP_PROJECT_ID \
      --collection-group=case_study_embeddings \
      --query-scope=COLLECTION \
      --field-config field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}'

    gcloud alpha firestore indexes composite create \
      --project=$GCP_PROJECT_ID \
      --collection-group=project_embeddings \
      --query-scope=COLLECTION \
      --field-config field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}'

Usage:
    uv run scripts/ingest.py
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv
from google.cloud.firestore import Client
from google.cloud.firestore_v1.vector import Vector

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")

if not GEMINI_API_KEY:
    raise SystemExit("GEMINI_API_KEY is required")


def embed_text(text: str) -> list[float]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_EMBEDDING_MODEL}:embedContent"
    payload = {
        "model": f"models/{GEMINI_EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": 768,
    }

    resp = httpx.post(
        url,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]


def ingest_case_studies(db: Client) -> None:
    collection = db.collection("case_study_embeddings")
    studies = json.loads((DATA_DIR / "case_studies.json").read_text())
    count = 0

    for study in studies:
        slug = study["slug"]
        title = study["title"]
        sections: dict[str, str] = {
            "challenge": study.get("challenge", ""),
            "approach": study.get("approach", ""),
            "results": study.get("results", ""),
            "retrospective": study.get("retrospective", ""),
        }
        for i, decision in enumerate(study.get("decisions", [])):
            sections[f"decision_{i}"] = decision

        for section, text in sections.items():
            if not text:
                continue
            doc_id = f"{slug}__{section}"
            content = f"{title} — {section}: {text}"
            embedding = embed_text(content)
            collection.document(doc_id).set(
                {
                    "slug": slug,
                    "section": section,
                    "title": title,
                    "content": content,
                    "embedding": Vector(embedding),
                }
            )
            count += 1
            time.sleep(0.1)  # stay within free-tier rate limits

    logger.info("case_study_embeddings: %d documents upserted", count)


def ingest_projects(db: Client) -> None:
    collection = db.collection("project_embeddings")
    projects = json.loads((DATA_DIR / "projects.json").read_text())

    for project in projects:
        slug = project["slug"]
        tech = ", ".join(project.get("technologies", []))
        content = f"{project['title']}: {project.get('description', '')} Technologies: {tech}"
        embedding = embed_text(content)
        collection.document(slug).set(
            {
                "slug": slug,
                "title": project["title"],
                "category": project.get("category", ""),
                "type": project.get("type", ""),
                "status": project.get("status", ""),
                "content": content,
                "embedding": Vector(embedding),
            }
        )
        time.sleep(0.1)

    logger.info("project_embeddings: %d documents upserted", len(projects))


def main() -> None:
    db = Client(project=GCP_PROJECT_ID or None)
    logger.info("Connected to Firestore project: %s", GCP_PROJECT_ID or "(default ADC)")
    ingest_case_studies(db)
    ingest_projects(db)
    logger.info("Ingest complete.")


if __name__ == "__main__":
    main()
