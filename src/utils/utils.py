import json
import logging
import os

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


def _read_data_file(filename: str, is_json: bool = False):
    filepath = os.path.join(_BASE_DIR, "data", filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f) if is_json else f.read()
    except FileNotFoundError:
        logger.error(f"Data file not found: {filepath}")
        return "Information currently unavailable."
    except json.JSONDecodeError:
        logger.error(f"JSON decode error: {filepath}")
        return "Invalid data format."
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return "Error retrieving information."


def load_prompt(name: str) -> str:
    filepath = os.path.join(_BASE_DIR, "prompts", f"{name}.md")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {filepath}")
        return ""
    except Exception as e:
        logger.error(f"Error reading prompt {filepath}: {e}")
        return ""
