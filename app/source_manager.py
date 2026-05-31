from __future__ import annotations

from typing import Optional

import httpx

from .models import FALLBACK_API_INSTANCES, FALLBACK_QOBUZ_INSTANCES, INSTANCES_URL


class SourceManager:
    def __init__(self) -> None:
        self._api_instances: list[str] = list(FALLBACK_API_INSTANCES)
        self._qobuz_instances: list[str] = list(FALLBACK_QOBUZ_INSTANCES)
        self._api_index = 0
        self._qobuz_index = 0

    async def refresh_instances(self) -> None:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                resp = await client.get(INSTANCES_URL)
                if resp.status_code == 200:
                    data = resp.json()
                    api = data.get("api", [])
                    if api:
                        self._api_instances = [
                            e["url"] for e in api if "url" in e
                        ] or list(FALLBACK_API_INSTANCES)
                    qobuz = data.get("qobuz", [])
                    if qobuz:
                        self._qobuz_instances = [
                            e["url"] for e in qobuz if "url" in e
                        ] or list(FALLBACK_QOBUZ_INSTANCES)
        except Exception:
            pass

    @property
    def api_instances(self) -> list[str]:
        return list(self._api_instances)

    @property
    def qobuz_instances(self) -> list[str]:
        return list(self._qobuz_instances)

    def next_api(self) -> Optional[str]:
        if not self._api_instances:
            return None
        inst = self._api_instances[self._api_index % len(self._api_instances)]
        self._api_index += 1
        return inst

    def next_qobuz(self) -> Optional[str]:
        if not self._qobuz_instances:
            return None
        inst = self._qobuz_instances[self._qobuz_index % len(self._qobuz_instances)]
        self._qobuz_index += 1
        return inst
