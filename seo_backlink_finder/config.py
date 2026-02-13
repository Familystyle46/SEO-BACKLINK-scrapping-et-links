"""Module de configuration multi-sites.

Charge et fusionne les configurations YAML pour permettre l'utilisation
de l'outil avec différents sites web.
"""

import os
from pathlib import Path
from copy import deepcopy

import yaml


DEFAULT_CONFIG = {
    "site": {
        "url": "",
        "name": "",
        "keywords": [],
        "language": "fr",
        "country": "FR",
    },
    "search": {
        "max_results_per_query": 30,
        "delay_between_requests": 5,
        "google_delay_min": 8,
        "google_delay_max": 15,
        "max_retries_on_429": 3,
        "request_timeout": 15,
        "max_pages_to_analyze": 5,
    },
    "scoring": {
        "weights": {
            "domain_authority": 25,
            "relevance": 30,
            "dofollow": 20,
            "comment_open": 15,
            "page_age": 10,
        }
    },
    "export": {
        "formats": ["csv", "json", "html"],
        "output_dir": "output",
    },
}

CONFIGS_DIR = Path(__file__).parent.parent / "configs"


def _deep_merge(base: dict, override: dict) -> dict:
    """Fusionne deux dictionnaires en profondeur."""
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_config(config_path: str | None = None) -> dict:
    """Charge la configuration depuis un fichier YAML.

    Args:
        config_path: Chemin vers le fichier de config. Si None, utilise default.yaml.

    Returns:
        Dictionnaire de configuration fusionné avec les valeurs par défaut.
    """
    config = deepcopy(DEFAULT_CONFIG)

    # Charger la config par défaut du projet si elle existe
    default_file = CONFIGS_DIR / "default.yaml"
    if default_file.exists():
        with open(default_file, "r", encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, file_config)

    # Charger la config spécifique si fournie
    if config_path:
        path = Path(config_path)
        if not path.is_absolute():
            path = CONFIGS_DIR / path
        if not path.exists():
            raise FileNotFoundError(f"Fichier de configuration introuvable: {path}")
        with open(path, "r", encoding="utf-8") as f:
            site_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, site_config)

    return config


def list_configs() -> list[str]:
    """Liste les fichiers de configuration disponibles."""
    if not CONFIGS_DIR.exists():
        return []
    return [
        f.stem
        for f in sorted(CONFIGS_DIR.glob("*.yaml"))
        if f.stem != "default"
    ]


def create_config(name: str, url: str, keywords: list[str],
                  language: str = "fr", country: str = "FR") -> Path:
    """Crée un nouveau fichier de configuration pour un site.

    Args:
        name: Nom du site (utilisé comme nom de fichier).
        url: URL du site.
        keywords: Liste de mots-clés de la thématique.
        language: Code langue (défaut: fr).
        country: Code pays (défaut: FR).

    Returns:
        Chemin du fichier créé.
    """
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

    config_data = {
        "site": {
            "url": url,
            "name": name,
            "keywords": keywords,
            "language": language,
            "country": country,
        }
    }

    filename = name.lower().replace(" ", "-").replace("_", "-")
    filepath = CONFIGS_DIR / f"{filename}.yaml"

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

    return filepath
