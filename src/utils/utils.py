import os
import json
import logging

logger = logging.getLogger(__name__)

def _read_data_file(filename: str, is_json: bool = False):
    base_dir = os.path.join(os.path.dirname(__file__), '..', '..')
    filepath = os.path.join(base_dir, 'data', filename)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if is_json:
                return json.load(f)
            return f.read()
    except FileNotFoundError:
        logger.error(f"Data file not found: {filepath}")
        return "Informazione non disponibile al momento."
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from file: {filepath}")
        return "Formato dati non valido."
    except Exception as e:
        logger.error(f"An error occurred reading file {filepath}: {e}")
        return "Si è verificato un errore nel recupero delle informazioni."
    