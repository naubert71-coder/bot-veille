"""Triage des entrées via Gemini, avec bascule de modèle, retry et timeout."""
import concurrent.futures
import os
import re
import time

from google import genai
from google.genai import errors

_client = None

# Délai maximal accordé à un seul appel Gemini. Au-delà, on considère le
# modèle comme indisponible et on passe au suivant (évite les runs bloqués).
_CALL_TIMEOUT = 60


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
    return f"{prompt_template}\n\nEntrées candidates :\n{content}"


def _call_with_timeout(client, model_name: str, prompt: str, timeout: int):
    """Exécute generate_content avec un délai maximal. Lève TimeoutError si
    l'appel réseau pend au-delà de `timeout` secondes."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            client.models.generate_content,
            model=model_name,
            contents=prompt,
        )
        return future.result(timeout=timeout)


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
        try:
            print(f"Tentative avec {model_name}...")
            response = _call_with_timeout(client, model_name, prompt, _CALL_TIMEOUT)
            text = getattr(response, "text", None)
            if not text or not text.strip():
                finish_reason = None
                if response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                print(
                    f"Réponse vide de {model_name} "
                    f"(finish_reason={finish_reason}). Modèle suivant..."
                )
                continue
            response_text = text.strip()
            print(f"Succès avec le modèle : {model_name}")
            break
        except concurrent.futures.TimeoutError:
            print(
                f"Timeout ({_CALL_TIMEOUT} s) sur {model_name}. "
                "Modèle suivant..."
            )
            continue
        except errors.ServerError:
            print(f"Surcharge temporaire sur {model_name} (503). Modèle suivant...")
            time.sleep(3)
        except errors.ClientError as exc:
            print(f"Erreur client sur {model_name} ({exc}). Modèle suivant...")
            time.sleep(2)
        except Exception as exc:
            print(f"Erreur sur {model_name} ({exc}). Modèle suivant...")

    if not response_text:
        return None

    return strip_code_fence(response_text)
