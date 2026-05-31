from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.models import TrackInfo
from app.search_worker import SearchWorker
from app.source_manager import SourceManager


def _mock_response(status_code: int = 200, json_data: object = None) -> AsyncMock:
    resp = AsyncMock(spec=["status_code", "json", "raise_for_status", "headers", "aiter_bytes"])
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_data or {})
    resp.raise_for_status = Mock(return_value=None)
    resp.headers = {}
    return resp


@pytest.fixture
def worker() -> SearchWorker:
    return SearchWorker(SourceManager())


@pytest.fixture
def mock_search_response() -> dict:
    return {
        "version": "2.3",
        "data": {
            "items": [
                {
                    "id": 12345678,
                    "title": "FabienK",
                    "duration": 200,
                    "isrc": "FR9W12345678",
                    "artist": {"name": "Angine de Poitrine"},
                    "artists": [{"id": 999, "name": "Angine de Poitrine"}],
                    "album": {"title": "Vol.II"},
                }
            ]
        },
    }


@pytest.fixture
def mock_info_response() -> dict:
    return {
        "id": 12345678,
        "title": "FabienK",
        "duration": 200,
        "isrc": "FR9W12345678",
        "artist": {"name": "Angine de Poitrine"},
        "artists": [{"id": 999, "name": "Angine de Poitrine"}],
        "album": {"title": "Vol.II"},
    }


@pytest.fixture
def mock_get_music_response() -> dict:
    return {"items": [{"id": 999999}]}


@pytest.fixture
def mock_download_music_response() -> dict:
    return {"url": "https://stream.example.com/track.flac"}


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_returns_tracks(
        self, worker: SearchWorker, mock_search_response: dict
    ) -> None:
        resp = _mock_response(200, mock_search_response)
        worker._sources._api_instances = ["https://mock.api"]
        with patch.object(worker._sources, "next_api", return_value="https://mock.api"):
            with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=resp)):
                tracks = await worker.search("FabienK")
                assert len(tracks) == 1
                assert tracks[0].title == "FabienK"
                assert tracks[0].artist == "Angine de Poitrine"
                assert tracks[0].isrc == "FR9W12345678"
                assert tracks[0].album == "Vol.II"

    @pytest.mark.asyncio
    async def test_search_handles_empty_data(self, worker: SearchWorker) -> None:
        resp = _mock_response(200, {"version": "2.3", "data": {"items": []}})
        worker._sources._api_instances = ["https://mock.api"]
        with patch.object(worker._sources, "next_api", return_value="https://mock.api"):
            with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=resp)):
                tracks = await worker.search("nothing")
                assert tracks == []

    @pytest.mark.asyncio
    async def test_search_no_instances(self, worker: SearchWorker) -> None:
        worker._sources._api_instances = []
        with patch.object(worker._sources, "next_api", return_value=None):
            with pytest.raises(RuntimeError, match="No API instances available"):
                await worker.search("test")

    @pytest.mark.asyncio
    async def test_search_fallback_response_keys(self, worker: SearchWorker) -> None:
        resp = _mock_response(
            200,
            {
                "tracks": [
                    {
                        "id": 555,
                        "title": "Track Name",
                        "artist": "Artist Name",
                        "album": "Album Title",
                        "duration": 180,
                    }
                ]
            },
        )
        worker._sources._api_instances = ["https://mock.api"]
        with patch.object(worker._sources, "next_api", return_value="https://mock.api"):
            with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=resp)):
                tracks = await worker.search("test")
                assert len(tracks) == 1
                assert tracks[0].title == "Track Name"
                assert tracks[0].artist == "Artist Name"

    @pytest.mark.asyncio
    async def test_search_tries_multiple_params(
        self, worker: SearchWorker, mock_search_response: dict
    ) -> None:
        fail_resp = _mock_response(400)
        ok_resp = _mock_response(200, mock_search_response)

        call_count = 0

        async def side_effect(url, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return fail_resp
            return ok_resp

        worker._sources._api_instances = ["https://mock.api"]
        with patch.object(worker._sources, "next_api", return_value="https://mock.api"):
            with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=side_effect)):
                tracks = await worker.search("test")
                assert len(tracks) == 1
                assert tracks[0].title == "FabienK"

    @pytest.mark.asyncio
    async def test_search_fallback_through_instances(
        self, worker: SearchWorker, mock_search_response: dict
    ) -> None:
        live_resp = _mock_response(200, mock_search_response)

        call_count = 0

        async def side_effect(url, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Connection failed")
            return live_resp

        worker._sources._api_instances = ["https://dead.api", "https://live.api"]
        with patch.object(worker._sources, "next_api") as mock_next:
            mock_next.side_effect = ["https://dead.api", "https://live.api"]
            with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=side_effect)):
                tracks = await worker.search("test")
                assert len(tracks) == 1
                assert tracks[0].title == "FabienK"


class TestGetTrackInfo:
    @pytest.mark.asyncio
    async def test_returns_track_info(
        self, worker: SearchWorker, mock_info_response: dict
    ) -> None:
        resp = _mock_response(200, mock_info_response)
        worker._sources._api_instances = ["https://mock.api"]
        with patch.object(worker._sources, "next_api", return_value="https://mock.api"):
            with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=resp)):
                info = await worker.get_track_info("12345678")
                assert info is not None
                assert info.title == "FabienK"
                assert info.isrc == "FR9W12345678"

    @pytest.mark.asyncio
    async def test_returns_none_when_all_fail(self, worker: SearchWorker) -> None:
        worker._sources._api_instances = []
        with patch.object(worker._sources, "next_api", return_value=None):
            info = await worker.get_track_info("999999")
            assert info is None


class TestResolveStreamUrl:
    @pytest.mark.asyncio
    async def test_resolves_with_isrc(
        self,
        worker: SearchWorker,
        track_fabienk: TrackInfo,
        mock_get_music_response: dict,
        mock_download_music_response: dict,
    ) -> None:
        mock_get = _mock_response(200, mock_get_music_response)
        mock_dl = _mock_response(200, mock_download_music_response)

        async def side_effect(url, **kw):
            if "/api/get-music" in str(url):
                return mock_get
            return mock_dl

        worker._sources._qobuz_instances = ["https://qobuz.mock"]
        with patch.object(worker._sources, "next_qobuz", return_value="https://qobuz.mock"):
            with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=side_effect)):
                url = await worker.resolve_stream_url(track_fabienk)
                assert url == "https://stream.example.com/track.flac"

    @pytest.mark.asyncio
    async def test_fetches_isrc_if_missing(
        self,
        worker: SearchWorker,
        track_no_isrc: TrackInfo,
        mock_info_response: dict,
        mock_get_music_response: dict,
        mock_download_music_response: dict,
    ) -> None:
        mock_info = _mock_response(200, mock_info_response)
        mock_get = _mock_response(200, mock_get_music_response)
        mock_dl = _mock_response(200, mock_download_music_response)

        def get_side(url, **kw):
            if "/info/" in str(url):
                return mock_info
            if "/api/get-music" in str(url):
                return mock_get
            return mock_dl

        worker._sources._api_instances = ["https://mock.api"]
        worker._sources._qobuz_instances = ["https://qobuz.mock"]
        with patch.object(worker._sources, "next_api", return_value="https://mock.api"):
            with patch.object(worker._sources, "next_qobuz", return_value="https://qobuz.mock"):
                with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=get_side)):
                    url = await worker.resolve_stream_url(track_no_isrc)
                    assert url == "https://stream.example.com/track.flac"
                    assert track_no_isrc.isrc == "FR9W12345678"

    @pytest.mark.asyncio
    async def test_returns_none_on_qobuz_failure(
        self, worker: SearchWorker, track_fabienk: TrackInfo
    ) -> None:
        worker._sources._qobuz_instances = []
        with patch.object(worker._sources, "next_qobuz", return_value=None):
            url = await worker.resolve_stream_url(track_fabienk)
            assert url is None

    @pytest.mark.asyncio
    async def test_returns_none_if_no_isrc_after_fetch(
        self, worker: SearchWorker, track_no_isrc: TrackInfo
    ) -> None:
        mock_info = _mock_response(200, {"id": "87654321", "title": "No ISRC"})
        worker._sources._api_instances = ["https://mock.api"]
        with patch.object(worker._sources, "next_api", return_value="https://mock.api"):
            with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_info)):
                url = await worker.resolve_stream_url(track_no_isrc)
                assert url is None


class TestDownloadTrack:
    @pytest.mark.asyncio
    async def test_downloads_and_converts(
        self, worker: SearchWorker, tmp_path: Path
    ) -> None:
        async def mock_aiter_bytes(size):
            yield b"x" * 1024
            yield b"y" * 1024

        resp = _mock_response(200)
        resp.headers = {"content-length": "2048"}
        resp.aiter_bytes = mock_aiter_bytes

        output = tmp_path / "output.ogg"
        with patch("httpx.AsyncClient.stream") as mock_ctx:
            mock_ctx.return_value.__aenter__.return_value = resp
            with patch("app.search_worker.FFmpegManager.convert_to_ogg") as mock_ff:
                result = await worker.download_track(
                    "https://example.com/stream", output
                )
                assert result == output
                mock_ff.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleans_up_temp_file(
        self, worker: SearchWorker, tmp_path: Path
    ) -> None:
        async def mock_aiter_bytes(size):
            yield b"data"

        resp = _mock_response(200)
        resp.headers = {"content-length": "4"}
        resp.aiter_bytes = mock_aiter_bytes

        output = tmp_path / "output.ogg"
        with patch("httpx.AsyncClient.stream") as mock_ctx:
            mock_ctx.return_value.__aenter__.return_value = resp
            with patch(
                "app.search_worker.FFmpegManager.convert_to_ogg",
                side_effect=RuntimeError("fail"),
            ):
                with pytest.raises(RuntimeError):
                    await worker.download_track("https://example.com/stream", output)
                assert not output.with_suffix(".raw_download").exists()
