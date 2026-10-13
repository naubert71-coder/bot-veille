"""Entry point of the watch bot. Reads config.yaml and runs the pipeline."""
import os
import sys

import yaml

from engine import collect, render, transport, triage


def _load_config() -> dict:
    config_path = os.environ.get("VEILLE_CONFIG", "config.yaml")
    if not os.path.exists(config_path):
        raise RuntimeError(f"Config file not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_prompt(config: dict) -> str:
    prompt_file = config.get("triage", {}).get("prompt_file", "prompts/biblio.md")
    if not os.path.exists(prompt_file):
        raise RuntimeError(f"Prompt file not found: {prompt_file}")
    with open(prompt_file, encoding="utf-8") as f:
        return f.read().strip()


def _maybe_send_empty(config: dict, reason: str) -> None:
    """Sends the 'no news' email only if send_if_empty is enabled (default: on)."""
    if config.get("output", {}).get("send_if_empty", True):
        transport.send_empty(config, reason)
    else:
        print(f"No email sent (send_if_empty=false): {reason}")


def main() -> None:
    config = _load_config()
    prompt_template = _load_prompt(config)

    entries = collect.collect_sources(config)
    if not entries:
        print("No entry collected for the period.")
        _maybe_send_empty(config, "No article collected from the RSS feeds.")
        return

    result = triage.triage(config, entries, prompt_template)

    if result is None:
        print("All models were temporarily unavailable.")
        _maybe_send_empty(config, "Gemini models temporarily unavailable.")
        return

    if result == "NONE" or len(result) == 0:
        print("No relevant article retained after filtering.")
        _maybe_send_empty(config, "No relevant article after filtering.")
        return

    html = render.render_cards(config, result)
    transport.send_digest(config, html)
    print("HTML email sent successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FATAL ERROR: {exc}")
        sys.exit(1)
