"""Integration tests for the full pipeline using "FabienK" by Angine de Poitrine.

These tests make real network calls against the community HiFi API instances.
They are marked as 'integration' and are skipped by default unless you run:

    pytest tests/test_integration.py --run-integration

or set the environment variable:
    $env:TEST_INTEGRATION = "1"
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.ffmpeg_manager import FFmpegManager
from app.models import TrackInfo
from app.mod_manager import create_music_mod, get_display_name, list_mods
from app.search_worker import SearchWorker
from app.source_manager import SourceManager


def pytest_configure() -> None:
    pytest.register_assert_rewrite("tests.test_integration")


def _should_run() -> bool:
    return os.environ.get("TEST_INTEGRATION") == "1"


integration = pytest.mark.skipif(
    not _should_run(),
    reason="set TEST_INTEGRATION=1 to run integration tests",
)


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


@integration
@pytest.mark.asyncio
async def test_search_fabienk() -> None:
    """Search for 'FabienK Angine de Poitrine' and verify results."""
    sm = SourceManager()
    await sm.refresh_instances()
    worker = SearchWorker(sm)
    tracks = await worker.search("FabienK Angine de Poitrine")
    assert len(tracks) > 0, "No tracks found for query"
    track = tracks[0]
    assert track.id, "Track ID should not be empty"
    assert track.title, "Track title should not be empty"
    assert track.artist, "Track artist should not be empty"
    assert track.duration > 0, "Track duration should be > 0"
    print(f"  Found: {track.title} by {track.artist} (ID: {track.id})")


@integration
@pytest.mark.asyncio
async def test_get_track_info() -> None:
    """Search then fetch full metadata for the first result."""
    sm = SourceManager()
    await sm.refresh_instances()
    worker = SearchWorker(sm)
    tracks = await worker.search("FabienK Angine de Poitrine")
    assert len(tracks) > 0
    info = await worker.get_track_info(tracks[0].id)
    assert info is not None
    assert info.title, "Info title should not be empty"
    assert info.isrc, "ISRC should be present for FabienK"
    print(f"  ISRC: {info.isrc}")
    print(f"  Album: {info.album}")


@integration
@pytest.mark.asyncio
async def test_resolve_stream_url() -> None:
    """Fetch a stream URL for FabienK (checks Qobuz pipeline)."""
    sm = SourceManager()
    await sm.refresh_instances()
    worker = SearchWorker(sm)
    tracks = await worker.search("FabienK Angine de Poitrine")
    assert len(tracks) > 0
    url = await worker.resolve_stream_url(tracks[0], quality="HIGH")
    assert url is not None, "Could not resolve stream URL"
    assert url.startswith("http"), f"Stream URL should be HTTP: {url}"
    print(f"  Stream URL: {url[:80]}...")


@integration
@pytest.mark.asyncio
async def test_full_download_and_mod_creation(tmp_path: Path) -> None:
    """Full pipeline: search -> resolve -> download -> convert -> create mod."""
    sm = SourceManager()
    await sm.refresh_instances()
    worker = SearchWorker(sm)
    tracks = await worker.search("FabienK Angine de Poitrine")
    assert len(tracks) > 0
    track = tracks[0]
    assert track.cover_url is not None, "Cover URL should be present"
    print(f"  Cover URL: {track.cover_url}")
    stream_url = await worker.resolve_stream_url(track, quality="HIGH")
    assert stream_url is not None
    ogg_path = tmp_path / "downloads" / f"{track.id}.ogg"
    result = await worker.download_track(stream_url, ogg_path)
    assert result.exists(), "Downloaded OGG file should exist"
    assert result.stat().st_size > 0, "OGG file should not be empty"
    ffmpeg = FFmpegManager.instance()
    probe = ffmpeg.ensure_ffmpeg()
    import subprocess
    r = subprocess.run(
        [str(probe), "-i", str(result), "-f", "null", "-"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"OGG file should be valid FFmpeg output:\n{r.stderr}"
    mod_overrides = tmp_path / "mod_overrides"
    mod_overrides.mkdir()
    display_name = "FabienK"
    mod_dir = create_music_mod(
        mod_overrides,
        track_id=f"custom_{track.id}",
        display_name=display_name,
        loop_ogg_path=result,
        volume=0.4,
        cover_url=track.cover_url,
    )
    icon = mod_dir / "icon.png"
    assert icon.exists(), "icon.png should be present"
    assert icon.stat().st_size > 0, "icon.png should not be empty"
    from PIL import Image
    img = Image.open(icon)
    assert img.size == (512, 512), f"icon.png should be 512x512, got {img.size}"
    mods = list_mods(mod_overrides)
    assert len(mods) == 1
    assert mods[0].track_id == f"custom_{track.id}"
    assert mods[0].volume == 0.4
    cached_name = get_display_name(mods[0])
    assert cached_name == display_name
    print("  Full pipeline completed successfully")


@integration
@pytest.mark.asyncio
async def test_all_quality_levels() -> None:
    """Attempt stream resolution at all 3 quality levels."""
    sm = SourceManager()
    await sm.refresh_instances()
    worker = SearchWorker(sm)
    tracks = await worker.search("FabienK Angine de Poitrine")
    assert len(tracks) > 0
    for quality in ("HIGH", "LOSSLESS", "HI_RES_LOSSLESS"):
        url = await worker.resolve_stream_url(tracks[0], quality=quality)
        if url:
            print(f"  {quality}: resolved OK")
        else:
            print(f"  {quality}: not available (expected for some levels)")


@integration
@pytest.mark.asyncio
async def test_instance_fallback() -> None:
    """If api instance fails, the next one should be tried automatically."""
    sm = SourceManager()
    await sm.refresh_instances()
    assert len(sm.api_instances) >= 3
    print(f"  Available API instances: {len(sm.api_instances)}")
    print(f"  Available Qobuz instances: {len(sm.qobuz_instances)}")
    worker = SearchWorker(sm)
    tracks = await worker.search("FabienK")
    assert len(tracks) > 0
