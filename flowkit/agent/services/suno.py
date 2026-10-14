"""Suno music generation client — sunoapi.org backend."""
import asyncio
import logging
import time
from typing import Optional

import httpx

from agent.config import (
    SUNO_API_KEY, SUNO_BASE_URL, SUNO_CALLBACK_URL, SUNO_MODEL,
    SUNO_POLL_INTERVAL, SUNO_POLL_TIMEOUT,
)

logger = logging.getLogger(__name__)


class SunoClient:
    """Async client for the Suno API (api.sunoapi.org)."""

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or SUNO_API_KEY
        self.base_url = (base_url or SUNO_BASE_URL).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30, headers=self._headers,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.close()
            self._client = None

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _check_key(self):
        if not self.api_key:
            raise RuntimeError(
                "SUNO_API_KEY not configured. "
                "Get one at https://sunoapi.org/api-key"
            )

    @staticmethod
    def _check_response(data: dict):
        code = data.get("code", 200)
        if code != 200:
            raise RuntimeError(f"Suno API error {code}: {data.get('msg', 'unknown')}")

    # ── Generate ─────────────────────────────────────────────

    async def generate(
        self,
        prompt: str = "",
        style: str = "",
        title: str = "",
        instrumental: bool = False,
        model: str = "",
        custom_mode: bool = True,
        callback_url: str = "",
    ) -> str:
        """Submit a music generation request.

        Two modes:
        - Custom (custom_mode=True): prompt = lyrics with [Verse]/[Chorus], style = genre tags
        - Description (custom_mode=False): prompt = natural language description

        Returns taskId.
        """
        self._check_key()
        payload: dict = {
            "model": model or SUNO_MODEL,
            "instrumental": instrumental,
            "customMode": custom_mode,
            "prompt": prompt,
        }
        if custom_mode:
            if style:
                payload["style"] = style
            if title:
                payload["title"] = title
        payload["callBackUrl"] = callback_url or SUNO_CALLBACK_URL

        client = await self._get_client()
        r = await client.post(
            f"{self.base_url}/api/v1/generate",
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

        self._check_response(data)
        task_id = data["data"]["taskId"]
        logger.info("Suno generate: taskId=%s", task_id)
        return task_id

    # ── Task status / polling ────────────────────────────────

    async def get_task(self, task_id: str) -> dict:
        """Get task status and clips."""
        self._check_key()
        client = await self._get_client()
        r = await client.get(
            f"{self.base_url}/api/v1/generate/record-info",
            params={"taskId": task_id},
        )
        r.raise_for_status()
        data = r.json()

        self._check_response(data)
        return data.get("data", {})

    async def poll_task(
        self,
        task_id: str,
        interval: float = 0,
        timeout: float = 0,
    ) -> dict:
        """Poll a task until SUCCESS. Raises on FAILED or timeout."""
        interval = interval or SUNO_POLL_INTERVAL
        timeout = timeout or SUNO_POLL_TIMEOUT
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            task = await self.get_task(task_id)
            status = task.get("status", "")
            elapsed = timeout - (deadline - time.monotonic())
            logger.info("Suno task %s: %s (%.0fs)", task_id[:12], status, elapsed)

            if status == "SUCCESS":
                return task
            if status == "FAILED":
                raise RuntimeError(f"Suno task {task_id} failed")

            await asyncio.sleep(interval)

        raise TimeoutError(f"Suno task {task_id} did not complete in {timeout}s")

    # ── Lyrics ───────────────────────────────────────────────

    async def generate_lyrics(self, prompt: str, callback_url: str = "") -> str:
        """Generate lyrics from a natural language prompt. Returns taskId."""
        self._check_key()
        payload: dict = {"prompt": prompt}
        payload["callBackUrl"] = callback_url or SUNO_CALLBACK_URL

        client = await self._get_client()
        r = await client.post(
            f"{self.base_url}/api/v1/lyrics",
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

        self._check_response(data)
        task_id = data["data"]["taskId"]
        logger.info("Suno lyrics: taskId=%s", task_id)
        return task_id

    # ── Extend ───────────────────────────────────────────────

    async def extend(
        self,
        audio_id: str,
        prompt: str = "",
        continue_at: Optional[float] = None,
        model: str = "",
        default_param_flag: bool = True,
        callback_url: str = "",
    ) -> str:
        """Extend/continue an existing track. Returns taskId."""
        self._check_key()
        payload: dict = {
            "audioId": audio_id,
            "defaultParamFlag": default_param_flag,
            "model": model or SUNO_MODEL,
        }
        if prompt:
            payload["prompt"] = prompt
        if continue_at is not None:
            payload["continueAt"] = continue_at
        payload["callBackUrl"] = callback_url or SUNO_CALLBACK_URL

        client = await self._get_client()
        r = await client.post(
            f"{self.base_url}/api/v1/generate/extend",
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

        self._check_response(data)
        task_id = data["data"]["taskId"]
        logger.info("Suno extend: taskId=%s", task_id)
        return task_id

    # ── Vocal removal ────────────────────────────────────────

    async def vocal_removal(
        self,
        task_id: str,
        audio_id: str,
        callback_url: str = "",
    ) -> str:
        """Separate vocals from instrumental. Returns taskId."""
        self._check_key()
        payload: dict = {"taskId": task_id, "audioId": audio_id}
        payload["callBackUrl"] = callback_url or SUNO_CALLBACK_URL

        client = await self._get_client()
        r = await client.post(
            f"{self.base_url}/api/v1/vocal-removal/generate",
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

        self._check_response(data)
        new_task_id = data["data"]["taskId"]
        logger.info("Suno vocal removal: taskId=%s", new_task_id)
        return new_task_id

    # ── Convert to WAV ───────────────────────────────────────

    async def convert_to_wav(
        self,
        task_id: str,
        audio_id: str,
        callback_url: str = "",
    ) -> str:
        """Convert a clip to WAV format. Returns taskId."""
        self._check_key()
        payload: dict = {"taskId": task_id, "audioId": audio_id}
        payload["callBackUrl"] = callback_url or SUNO_CALLBACK_URL

        client = await self._get_client()
        r = await client.post(
            f"{self.base_url}/api/v1/convert-to-wav",
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

        self._check_response(data)
        new_task_id = data["data"]["taskId"]
        logger.info("Suno convert-to-wav: taskId=%s", new_task_id)
        return new_task_id

    # ── Credits ──────────────────────────────────────────────

    async def get_credits(self) -> dict:
        """Get remaining credits."""
        self._check_key()
        client = await self._get_client()
        r = await client.get(
            f"{self.base_url}/api/v1/get-credits",
        )
        r.raise_for_status()
        data = r.json()

        self._check_response(data)
        return data.get("data", {})


# Singleton
_suno_client: Optional[SunoClient] = None


def get_suno_client() -> SunoClient:
    global _suno_client
    if _suno_client is None:
        _suno_client = SunoClient()
    return _suno_client
