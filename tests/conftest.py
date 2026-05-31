from __future__ import annotations

from pathlib import Path

import pytest

from app.models import MusicMod, TrackInfo
from app.source_manager import SourceManager


@pytest.fixture
def track_fabienk() -> TrackInfo:
    return TrackInfo(
        id="12345678",
        title="FabienK",
        artist="Angine de Poitrine",
        album="Angine de Poitrine",
        duration=200,
        isrc="FR9W12345678",
    )


@pytest.fixture
def track_no_isrc() -> TrackInfo:
    return TrackInfo(
        id="87654321",
        title="No ISRC Track",
        artist="Test Artist",
        album="Test Album",
        duration=180,
    )


@pytest.fixture
def music_mod() -> MusicMod:
    return MusicMod(
        name="FabienK Menu Track",
        track_id="custom_12345678",
        volume=0.4,
    )


@pytest.fixture
def music_mod_with_intro() -> MusicMod:
    return MusicMod(
        name="FabienK Menu Track",
        track_id="custom_12345678",
        volume=0.5,
        has_intro=True,
    )


@pytest.fixture
def temp_mod_overrides(tmp_path: Path) -> Path:
    d = tmp_path / "mod_overrides"
    d.mkdir()
    return d


@pytest.fixture
def sample_main_xml() -> str:
    return (
        '<table name="FabienK Menu Track">\n'
        '    <Localization directory="loc" default="en.txt"/>\n'
        '    <MenuMusic id="custom_12345678" source="sounds/menu_loop.ogg" volume="0.4"/>\n'
        "</table>\n"
    )


@pytest.fixture
def sample_main_xml_with_intro() -> str:
    return (
        '<table name="FabienK With Intro">\n'
        '    <Localization directory="loc" default="en.txt"/>\n'
        '    <MenuMusic id="custom_with_intro" start_source="sounds/menu_intro.ogg" source="sounds/menu_loop.ogg" volume="0.3"/>\n'
        "</table>\n"
    )


@pytest.fixture
def source_manager() -> SourceManager:
    return SourceManager()


@pytest.fixture
def sample_ogg(tmp_path: Path) -> Path:
    p = tmp_path / "sample.ogg"
    p.write_bytes(b"OggS\x00\x02")
    return p
