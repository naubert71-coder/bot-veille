"""Point d'entrée du bot de veille. Lit config.yaml et orchestre le pipeline."""
import os
import sys

import yaml

from engine import collect, render, transport, triage


def _load_config() -> dict:
    config_path = os.environ.get("VEILLE_CONFIG", "config.yaml")
    if not os.path.exists(config_path):
        raise RuntimeError(
            f"Fichier de configuration introuvable : {config_path}"
        )
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_prompt(config: dict) -> str:
    prompt_file = config.get("triage", {}).get("prompt_file", "prompts/biblio.md")
    if not os.path.exists(prompt_file):
        raise RuntimeError(f"Fichier de prompt introuvable : {prompt_file}")
    with open(prompt_file, encoding="utf-8") as f:
        return f.read().strip()


def main() -> None:
    config = _load_config()
    prompt_template = _load_prompt(config)

    entries = collect.collect_sources(config)
    if not entries:
        print("Aucune entrée récupérée sur la période.")
        transport.send_empty(config, "Aucun article récupéré sur les flux RSS.")
        return

    result = triage.triage(config, entries, prompt_template)

    if result is None:
        print("Tous les modèles étaient temporairement indisponibles.")
        transport.send_empty(config, "Modèles Gemini temporairement indisponibles.")
        return

    if result == "AUCUN" or len(result) == 0:
        print("Aucun article pertinent retenu après filtrage.")
        transport.send_empty(config, "Aucun article pertinent après filtrage.")
        return

    html = render.render_cards(config, result)
    transport.send_digest(config, html)
    print("E-mail HTML envoyé avec succès.")


if __name__ == "__main__":
    main()
