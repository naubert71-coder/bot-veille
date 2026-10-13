"""Triage des entrées via Gemini, avec bascule de modèle et retry."""
import os
import re
import time

from google import genai
from google.genai import errors

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Variable d'environnement requise absente ou vide : GEMINI_API_KEY"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def strip_code_fence(text: str) -> str:
    """Retire un bloc ```markdown/html``` englobant, quel que soit le tag."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _build_prompt(prompt_template: str, entries: list[str], max_items: int) -> str:
    content = "\n\n---\n\n".join(entries[:max_items])
    return (
        f"{prompt_template}\n\n"
        f"Entrées candidates :\n{content}"
    )


def triage(config: dict, entries: list[str], prompt_template: str) -> str | None:
    """Retourne le fragment HTML trié, ou None si aucun modèle n'a répondu."""
    triage_cfg = config.get("triage", {})
    model_chain = triage_cfg.get("model_chain", ["gemini-2.5-flash"])
    max_items = triage_cfg.get("max_items", 200)

    prompt = _build_prompt(prompt_template, entries, max_items)
    print(
        f"Prompt envoyé : ~{len(prompt)} caractères, "
        f"{min(len(entries), max_items)} entrées sur {len(entries)}."
    )

    client = _get_client()
    response_text = None

    for model_name in model_chain:
        for attempt in range(3):
            try:
                print(f"Tentative avec {model_name} (essai {attempt + 1}/3)...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                text = getattr(response, "text", None)
                if not text or not text.strip():
                    finish_reason = None
                    if response.candidates:
                        finish_reason = response.candidates[0].finish_reason
                    print(
                        f"Réponse vide de {model_name} "
                        f"(finish_reason={finish_reason}). Modèle suivant..."
                    )
                    break
                response_text = text.strip()
                print(f"Succès avec le modèle : {model_name}")
                break
            except errors.ServerError:
                print(
                    f"Surcharge temporaire sur {model_name} (503). "
                    "Attente de 10 s avant réessai..."
                )
                time.sleep(10)
            except errors.ClientError as exc:
                print(f"Erreur client sur {model_name} ({exc}). Attente de 30 s...")
                time.sleep(30)
            except Exception as exc:
                print(f"Erreur sur {model_name} ({exc}). Modèle suivant...")
                break

        if response_text:
            break

    if not response_text:
        return None

    return strip_code_fence(response_text)
