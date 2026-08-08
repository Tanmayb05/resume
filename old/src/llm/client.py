"""Async LLM client wrapping Ollama's AsyncClient with Tenacity retry logic.

All pipeline stages call LLMs through this single integration point so that
timeout, retry, and error-reporting behavior is consistent across the codebase.
"""
import asyncio
import logging

from ollama import AsyncClient
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    RetryError,
)

from src.config import AppConfig
from src.llm.errors import LLMError

logger = logging.getLogger(__name__)


def _is_transient(exc: Exception) -> bool:
    """Return True for errors that warrant a retry; False for permanent failures.

    Retry on:  connection errors, timeouts, Ollama 5xx, rate limits (429).
    Fail fast: auth errors, validation errors, bad model name.
    """
    if isinstance(exc, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
        return True
    error_str = str(exc).lower()
    return any(code in error_str for code in ["500", "502", "503", "504", "429", "connection"])


class LLMClient:
    """Async LLM client backed by a local Ollama server.

    Usage:
        config = AppConfig()
        client = LLMClient(config)
        text = await client.call("Tell me about Python.")
        text = await client.call("Write a cover letter...", model="llama3")
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._client = AsyncClient(
            host=config.llm_host,
            timeout=float(config.llm_timeout_seconds),
        )
        logger.debug("LLMClient initialised (host=%s, model=%s)", config.llm_host, config.llm_default_model)

    async def call(self, prompt: str, model: str | None = None) -> str:
        """Call the LLM and return the raw response text.

        Retries up to config.llm_max_retries times on transient failures
        (connection errors, timeouts, 5xx). Raises LLMError immediately on
        permanent failures (auth, bad model name, validation errors).

        Args:
            prompt: Full prompt text to send to the model.
            model: Model name override (e.g. 'zephyr', 'llama3').
                   Uses config.llm_default_model if None.

        Returns:
            Raw response text from the model (may contain markdown fences).

        Raises:
            LLMError: After max retries on transient errors, or immediately on
                      permanent errors.
        """
        model = model or self.config.llm_default_model
        max_retries = self.config.llm_max_retries

        @retry(
            retry=retry_if_exception(_is_transient),
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            reraise=False,
        )
        async def _call_with_retry() -> str:
            logger.debug("LLM call -> model=%s prompt_length=%d", model, len(prompt))
            try:
                response = await self._client.generate(
                    model=model,
                    prompt=prompt,
                    stream=False,
                )
                text = response["response"]
                logger.debug("LLM call <- %d chars returned", len(text))
                return text
            except (ConnectionError, TimeoutError, asyncio.TimeoutError):
                raise  # Tenacity will retry
            except Exception as exc:
                if not _is_transient(exc):
                    # Permanent error — fail immediately, no retry
                    raise LLMError(
                        f"Permanent LLM error (model={model})",
                        original_error=exc,
                        attempts=1,
                    ) from exc
                raise  # Transient — let Tenacity retry

        try:
            return await _call_with_retry()
        except LLMError:
            raise  # Already wrapped
        except RetryError as exc:
            original = exc.last_attempt.exception()
            raise LLMError(
                f"LLM call failed after {max_retries} attempt(s) (model={model})",
                original_error=original,
                attempts=max_retries,
            ) from exc
        except Exception as exc:
            raise LLMError(
                f"Unexpected LLM error (model={model})",
                original_error=exc,
                attempts=1,
            ) from exc
