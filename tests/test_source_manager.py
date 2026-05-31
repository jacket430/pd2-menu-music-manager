from __future__ import annotations

import pytest

from app.models import FALLBACK_API_INSTANCES, FALLBACK_QOBUZ_INSTANCES


class TestSourceManagerInit:
    def test_starts_with_fallbacks(self, source_manager) -> None:
        assert len(source_manager.api_instances) == len(FALLBACK_API_INSTANCES)
        assert len(source_manager.qobuz_instances) == len(FALLBACK_QOBUZ_INSTANCES)

    def test_instances_are_copies(self, source_manager) -> None:
        api_copy = source_manager.api_instances
        qobuz_copy = source_manager.qobuz_instances
        assert api_copy == FALLBACK_API_INSTANCES
        assert qobuz_copy == FALLBACK_QOBUZ_INSTANCES


class TestNextApi:
    def test_rotates_through_instances(self, source_manager) -> None:
        first = source_manager.next_api()
        second = source_manager.next_api()
        assert first != second
        assert first in FALLBACK_API_INSTANCES
        assert second in FALLBACK_API_INSTANCES

    def test_wraps_around(self, source_manager) -> None:
        n = len(FALLBACK_API_INSTANCES)
        seen = set()
        for _ in range(n):
            seen.add(source_manager.next_api())
        assert seen == set(FALLBACK_API_INSTANCES)
        wrapped = source_manager.next_api()
        assert wrapped == FALLBACK_API_INSTANCES[0]

    def test_returns_none_if_empty(self) -> None:
        from app.source_manager import SourceManager
        sm = SourceManager()
        sm._api_instances = []
        assert sm.next_api() is None


class TestNextQobuz:
    def test_rotates(self, source_manager) -> None:
        first = source_manager.next_qobuz()
        second = source_manager.next_qobuz()
        assert first != second
        assert first in FALLBACK_QOBUZ_INSTANCES
        assert second in FALLBACK_QOBUZ_INSTANCES

    def test_returns_none_if_empty(self) -> None:
        from app.source_manager import SourceManager
        sm = SourceManager()
        sm._qobuz_instances = []
        assert sm.next_qobuz() is None


class TestRefreshInstances:
    @pytest.mark.asyncio
    async def test_fetch_failure_keeps_fallbacks(self, source_manager) -> None:
        await source_manager.refresh_instances()
        assert len(source_manager.api_instances) == len(FALLBACK_API_INSTANCES)
        assert len(source_manager.qobuz_instances) == len(FALLBACK_QOBUZ_INSTANCES)

    @pytest.mark.asyncio
    async def test_exception_does_not_clear(self, source_manager) -> None:
        source_manager._api_instances = []
        source_manager._qobuz_instances = []
        await source_manager.refresh_instances()
        assert source_manager.api_instances == []
        assert source_manager.qobuz_instances == []
