"""Triage of entries via Gemini, with model fallback, retry and timeout."""
import concurrent.futures
import os
import re
import time

from google import genai
from google.genai import errors

_client = None

# Maximum time allowed for a single Gemini call. Beyond that, the model is
# considered unavailable and we move to the next one (avoids blocked runs).
_CALL_TIMEOUT = 60


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Required environment variable missing or empty: GEMINI_API_KEY"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def strip_code_fence(text: str) -> str:
    """Remove an enclosing ```markdown/html``` fence, whatever the tag."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _build_prompt(prompt_template: str, entries: list[str], max_items: int) -> str:
    content = "\n\n---\n\n".join(entries[:max_items])
    return f"{prompt_template}\n\nCandidate entries:\n{content}"


def _call_with_timeout(client, model_name: str, prompt: str, timeout: int):
    """Runs generate_content with a hard time limit. Raises TimeoutError if
    the network call hangs beyond `timeout` seconds."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            client.models.generate_content,
            model=model_name,
            contents=prompt,
        )
        return future.result(timeout=timeout)


def _normalize_result(text: str) -> str:
    """Normalizes the model output to either 'NONE' or a usable HTML fragment.

    A model that answered but kept nothing (a lone preamble, or 'NONE' glued
    to other text) must be turned into 'NONE', otherwise the bot sends an
    empty digest instead of a clean 'no news' email.
    """
    cleaned = strip_code_fence(text)

    # The model answered but retained nothing: normalize to "NONE".
    if cleaned.upper().startswith("NONE"):
        return "NONE"

    # Residue without any card (preamble only): treat as nothing.
    if "article-card" not in cleaned:
        print("Response without a usable card, treated as empty.")
        return "NONE"

    return cleaned


def triage(config: dict, entries: list[str], prompt_template: str) -> str | None:
    """Returns the triaged HTML fragment, or None if no model answered."""
    triage_cfg = config.get("triage", {})
    model_chain = triage_cfg.get("model_chain", ["gemini-2.5-flash"])
    max_items = triage_cfg.get("max_items", 200)

    prompt = _build_prompt(prompt_template, entries, max_items)
    print(
        f"Prompt sent: ~{len(prompt)} characters, "
        f"{min(len(entries), max_items)} entries out of {len(entries)}."
    )

    client = _get_client()
    response_text = None

    for model_name in model_chain:
        try:
            print(f"Trying {model_name}...")
            response = _call_with_timeout(client, model_name, prompt, _CALL_TIMEOUT)
            text = getattr(response, "text", None)
            if not text or not text.strip():
                finish_reason = None
                if response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                print(
                    f"Empty response from {model_name} "
                    f"(finish_reason={finish_reason}). Next model..."
                )
                continue
            response_text = text.strip()
            print(f"Success with model: {model_name}")
            break
        except concurrent.futures.TimeoutError:
            print(
                f"Timeout ({_CALL_TIMEOUT}s) on {model_name}. Next model..."
            )
            continue
        except errors.ServerError:
            print(f"Temporary overload on {model_name} (503). Next model...")
            time.sleep(3)
        except errors.ClientError as exc:
            print(f"Client error on {model_name} ({exc}). Next model...")
            time.sleep(2)
        except Exception as exc:
            print(f"Error on {model_name} ({exc}). Next model...")

    if not response_text:
        return None

    return _normalize_result(response_text)
