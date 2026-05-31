from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import httpx

from .ffmpeg_manager import FFmpegManager
from .models import QUALITY_MAP, TrackInfo
from .source_manager import SourceManager

ProgressCallback = Callable[[int, int, str], None]


class SearchWorker:
    def __init__(self, source_manager: SourceManager) -> None:
        self._sources = source_manager

    async def _request_instances(
        self, path: str, params_list: list[dict], timeout: int = 15
    ) -> Optional[dict]:
        instances = self._sources.api_instances
        for _ in range(len(instances)):
            base = self._sources.next_api()
            if not base:
                break
            for params in params_list:
                try:
                    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                        resp = await client.get(f"{base}{path}", params=params)
                        if resp.status_code == 200:
                            return resp.json()
                except Exception:
                    continue
        return None

    @staticmethod
    def _extract_cover_url(item: dict) -> Optional[str]:
        album = item.get("album")
        cover_uuid = None
        if isinstance(album, dict):
            cover_uuid = album.get("cover")
        if not cover_uuid:
            cover_uuid = item.get("cover")
        if not cover_uuid or not isinstance(cover_uuid, str):
            return None
        if cover_uuid.startswith("http"):
            return cover_uuid
        formatted = cover_uuid.replace("-", "/")
        return f"https://resources.tidal.com/images/{formatted}/320x320.jpg"

    async def search(self, query: str) -> list[TrackInfo]:
        data = await self._request_instances(
            "/search/",
            [{"s": query}, {"q": query}],
        )
        if data is None:
            raise RuntimeError("No API instances available")
        raw = data.get("data", data)
        results = raw.get("tracks", raw.get("results", raw.get("items", raw if isinstance(raw, list) else [])))
        if isinstance(results, dict):
            results = results.get("items", [])
        tracks: list[TrackInfo] = []
        for item in (results or []):
            tracks.append(TrackInfo(
                id=str(item.get("id", item.get("track_id", ""))),
                title=item.get("title", item.get("name", "Unknown")),
                artist=self._extract_artist(item),
                album=self._extract_album(item),
                duration=int(item.get("duration", item.get("length", 0))),
                isrc=item.get("isrc"),
                cover_url=self._extract_cover_url(item),
            ))
        return tracks

    @staticmethod
    def _extract_artist(item: dict) -> str:
        artist = item.get("artist")
        if isinstance(artist, dict):
            return artist.get("name", "Unknown")
        if artist is not None:
            return artist
        artists = item.get("artists")
        if isinstance(artists, list) and artists:
            a = artists[0]
            return a.get("name", "Unknown") if isinstance(a, dict) else str(a)
        return "Unknown"

    @staticmethod
    def _extract_album(item: dict) -> str:
        album = item.get("album")
        if isinstance(album, dict):
            return album.get("title", "Unknown")
        if album is not None:
            return album
        albums = item.get("albums")
        if isinstance(albums, list) and albums:
            a = albums[0]
            return a.get("title", "Unknown") if isinstance(a, dict) else str(a)
        return "Unknown"

    async def get_track_info(self, track_id: str) -> Optional[TrackInfo]:
        data = await self._request_instances("/info/", [{"id": track_id}])
        if data is None:
            return None
        payload = data.get("data", data)
        return TrackInfo(
            id=str(payload.get("id", track_id)),
            title=payload.get("title", payload.get("name", "Unknown")),
            artist=self._extract_artist(payload),
            album=self._extract_album(payload),
            duration=int(payload.get("duration", payload.get("length", 0))),
            isrc=payload.get("isrc"),
            cover_url=self._extract_cover_url(payload),
        )

    async def resolve_stream_url(
        self, track: TrackInfo, quality: str = "LOSSLESS"
    ) -> Optional[str]:
        if not track.isrc:
            info = await self.get_track_info(track.id)
            if info and info.isrc:
                track.isrc = info.isrc
        if not track.isrc:
            return None
        qobuz_instances = self._sources.qobuz_instances
        if not qobuz_instances:
            return None
        quality_code = QUALITY_MAP.get(quality, "6")
        start_index = self._sources._qobuz_index
        for _ in range(len(qobuz_instances)):
            qobuz_url = self._sources.next_qobuz()
            if not qobuz_url:
                break
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                    resp = await client.get(
                        f"{qobuz_url}/api/get-music",
                        params={"q": track.isrc, "offset": 0},
                    )
                    if resp.status_code != 200:
                        continue
                    items_resp = resp.json()
                    qobuz_data = items_resp.get("data", items_resp)
                    qobuz_tracks = qobuz_data.get("tracks", items_resp)
                    items = qobuz_tracks if isinstance(qobuz_tracks, list) else qobuz_tracks.get("items", items_resp.get("items", []))
                    if not items:
                        continue
                    track_id = items[0].get("id")
                    if not track_id:
                        continue
                    dl_resp = await client.get(
                        f"{qobuz_url}/api/download-music",
                        params={"track_id": track_id, "quality": quality_code},
                    )
                    if dl_resp.status_code != 200:
                        continue
                    dl_data = dl_resp.json()
                    dl_payload = dl_data.get("data", dl_data)
                    url = dl_payload.get("url")
                    if url:
                        return url
            except Exception:
                continue
        return None

    async def download_track(
        self,
        stream_url: str,
        output_path: Path,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_raw = output_path.with_suffix(".raw_download")
        async with httpx.AsyncClient(follow_redirects=True, timeout=300) as client:
            async with client.stream("GET", stream_url) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(temp_raw, "wb") as f:
                    async for chunk in resp.aiter_bytes(65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb and total:
                            progress_cb(downloaded, total, "Downloading")
        try:
            ffmpeg = FFmpegManager.instance()
            if progress_cb:
                progress_cb(0, 1, "Converting to OGG")
            ffmpeg.convert_to_ogg(temp_raw, output_path)
        finally:
            temp_raw.unlink(missing_ok=True)
        return output_path
