from __future__ import annotations

from app.models import (
    INSTANCES_URL,
    QUALITY_LABELS,
    QUALITY_MAP,
    FALLBACK_API_INSTANCES,
    FALLBACK_QOBUZ_INSTANCES,
    MusicMod,
    TrackInfo,
)


class TestTrackInfo:
    def test_minimal(self) -> None:
        t = TrackInfo(id="1", title="T", artist="A", album="Al", duration=100)
        assert t.id == "1"
        assert t.title == "T"
        assert t.artist == "A"
        assert t.album == "Al"
        assert t.duration == 100
        assert t.isrc is None
        assert t.cover_url is None
        assert t.provider == "tidal"

    def test_full(self) -> None:
        t = TrackInfo(
            id="42",
            title="FabienK",
            artist="Angine de Poitrine",
            album="Angine de Poitrine",
            duration=200,
            isrc="FR9W12345678",
            cover_url="https://example.com/cover.jpg",
            provider="tidal",
        )
        assert t.isrc == "FR9W12345678"
        assert t.cover_url == "https://example.com/cover.jpg"


class TestSearchResult:
    def test_default_empty(self) -> None:
        from app.models import SearchResult
        r = SearchResult(query="test")
        assert r.tracks == []
        assert r.total_results == 0

    def test_with_tracks(self) -> None:
        from app.models import SearchResult
        t = TrackInfo(id="1", title="T", artist="A", album="Al", duration=10)
        r = SearchResult(query="test", tracks=[t], total_results=1)
        assert len(r.tracks) == 1
        assert r.tracks[0].title == "T"


class TestStreamInfo:
    def test_defaults(self) -> None:
        from app.models import StreamInfo
        s = StreamInfo(url="https://example.com/stream")
        assert s.mime_type == "audio/ogg"
        assert s.quality == "LOSSLESS"

    def test_custom(self) -> None:
        from app.models import StreamInfo
        s = StreamInfo(url="https://example.com/stream", mime_type="audio/flac", quality="HI_RES_LOSSLESS")
        assert s.mime_type == "audio/flac"
        assert s.quality == "HI_RES_LOSSLESS"


class TestMusicMod:
    def test_localization_key(self, music_mod: MusicMod) -> None:
        assert music_mod.localization_key == "menu_jukebox_custom_12345678"

    def test_screen_key(self, music_mod: MusicMod) -> None:
        assert music_mod.screen_key == "menu_jukebox_screen_custom_12345678"

    def test_to_xml_no_intro(self, music_mod: MusicMod) -> None:
        xml = music_mod.to_xml()
        assert '<table name="FabienK Menu Track">' in xml
        assert '<MenuMusic id="custom_12345678"' in xml
        assert 'source="sounds/menu_loop.ogg"' in xml
        assert 'volume="0.4"' in xml
        assert "start_source" not in xml

    def test_to_xml_with_intro(self, music_mod_with_intro: MusicMod) -> None:
        xml = music_mod_with_intro.to_xml()
        assert '<table name="FabienK Menu Track">' in xml
        assert 'start_source="sounds/menu_intro.ogg"' in xml
        assert 'volume="0.5"' in xml

    def test_to_localization(self, music_mod: MusicMod) -> None:
        loc = music_mod.to_localization("FabienK")
        assert "menu_jukebox_custom_12345678" in loc
        assert "menu_jukebox_screen_custom_12345678" in loc
        assert '"FabienK"' in loc

    def test_to_localization_special_chars(self) -> None:
        mod = MusicMod(name="Test", track_id="test_1")
        loc = mod.to_localization("Track Name With Spaces & Symbols")
        assert "Track Name With Spaces & Symbols" in loc

    def test_folder_path_default(self) -> None:
        mod = MusicMod(name="Test", track_id="test")
        assert mod.folder_path is None

    def test_volume_default(self) -> None:
        mod = MusicMod(name="Test", track_id="test")
        assert mod.volume == 0.4

    def test_has_intro_default(self) -> None:
        mod = MusicMod(name="Test", track_id="test")
        assert mod.has_intro is False


class TestConstants:
    def test_instances_url(self) -> None:
        assert INSTANCES_URL == "https://tidal-uptime.geeked.wtf"

    def test_fallback_api_instances_non_empty(self) -> None:
        assert len(FALLBACK_API_INSTANCES) >= 5

    def test_fallback_qobuz_instances_non_empty(self) -> None:
        assert len(FALLBACK_QOBUZ_INSTANCES) >= 2

    def test_all_api_instances_https(self) -> None:
        for url in FALLBACK_API_INSTANCES:
            assert url.startswith("https://"), f"{url} does not start with https://"

    def test_all_qobuz_instances_https(self) -> None:
        for url in FALLBACK_QOBUZ_INSTANCES:
            assert url.startswith("https://"), f"{url} does not start with https://"

    def test_quality_map_has_all_keys(self) -> None:
        assert set(QUALITY_MAP.keys()) == {"HI_RES_LOSSLESS", "LOSSLESS", "HIGH"}

    def test_quality_map_values(self) -> None:
        assert QUALITY_MAP["HI_RES_LOSSLESS"] == "27"
        assert QUALITY_MAP["LOSSLESS"] == "6"
        assert QUALITY_MAP["HIGH"] == "5"

    def test_quality_labels_present(self) -> None:
        assert len(QUALITY_LABELS) == 3
        for key in QUALITY_MAP:
            assert key in QUALITY_LABELS
