from __future__ import annotations

import json
from pathlib import Path

from app.mod_manager import (
    _parse_main_xml,
    _xml_attr,
    create_music_mod,
    delete_mod,
    get_display_name,
    list_mods,
    update_display_name,
    update_volume,
)
from app.models import MusicMod


class TestXmlAttr:
    def test_finds_simple_attr(self) -> None:
        assert _xml_attr('id="test" source="sounds/menu.ogg"', "id") == "test"

    def test_finds_second_attr(self) -> None:
        assert _xml_attr('id="a" volume="0.5"', "volume") == "0.5"

    def test_missing_attr(self) -> None:
        assert _xml_attr('id="test"', "volume") is None

    def test_attr_with_spaces(self) -> None:
        assert _xml_attr('  id =  "value"  ', "id") == "value"


class TestParseMainXml:
    def test_parses_basic_mod(self, sample_main_xml: str, tmp_path: Path) -> None:
        p = tmp_path / "main.xml"
        p.write_text(sample_main_xml)
        mod = _parse_main_xml(p)
        assert mod is not None
        assert mod.name == "FabienK Menu Track"
        assert mod.track_id == "custom_12345678"
        assert mod.volume == 0.4
        assert mod.has_intro is False

    def test_parses_with_intro(self, sample_main_xml_with_intro: str, tmp_path: Path) -> None:
        p = tmp_path / "main.xml"
        p.write_text(sample_main_xml_with_intro)
        mod = _parse_main_xml(p)
        assert mod is not None
        assert mod.name == "FabienK With Intro"
        assert mod.track_id == "custom_with_intro"
        assert mod.volume == 0.3
        assert mod.has_intro is True

    def test_returns_none_for_no_table(self, tmp_path: Path) -> None:
        p = tmp_path / "main.xml"
        p.write_text("<notatable/><MenuMusic id='x' source='y.ogg'/>")
        mod = _parse_main_xml(p)
        assert mod is None

    def test_returns_none_for_no_menumusic(self, tmp_path: Path) -> None:
        p = tmp_path / "main.xml"
        p.write_text('<table name="test"><Localization/></table>')
        mod = _parse_main_xml(p)
        assert mod is None

    def test_parses_float_volume(self, tmp_path: Path) -> None:
        p = tmp_path / "main.xml"
        p.write_text(
            '<table name="Test"><MenuMusic id="x" source="y.ogg" volume="0.75"/></table>'
        )
        mod = _parse_main_xml(p)
        assert mod is not None
        assert mod.volume == 0.75

    def test_default_volume_0_4(self, tmp_path: Path) -> None:
        p = tmp_path / "main.xml"
        p.write_text('<table name="Test"><MenuMusic id="x" source="y.ogg"/></table>')
        mod = _parse_main_xml(p)
        assert mod is not None
        assert mod.volume == 0.4


class TestCreateMusicMod:
    def test_creates_folder_structure(
        self, temp_mod_overrides: Path, sample_ogg: Path
    ) -> None:
        result = create_music_mod(
            temp_mod_overrides, "custom_test", "Test Song", sample_ogg
        )
        assert result.exists()
        assert (result / "main.xml").exists()
        assert (result / "loc" / "en.txt").exists()
        assert (result / "sounds" / "menu_loop.ogg").exists()

    def test_xml_content(self, temp_mod_overrides: Path, sample_ogg: Path) -> None:
        result = create_music_mod(
            temp_mod_overrides, "custom_test", "Test Song", sample_ogg, volume=0.5
        )
        xml_text = (result / "main.xml").read_text()
        assert "Test Song Menu Track" in xml_text
        assert 'id="custom_test"' in xml_text
        assert 'volume="0.5"' in xml_text
        assert 'source="sounds/menu_loop.ogg"' in xml_text

    def test_localization_content(
        self, temp_mod_overrides: Path, sample_ogg: Path
    ) -> None:
        result = create_music_mod(
            temp_mod_overrides, "custom_test", "Test Song", sample_ogg
        )
        loc_text = (result / "loc" / "en.txt").read_text()
        data = json.loads(loc_text)
        assert data["menu_jukebox_custom_test"] == "Test Song"
        assert data["menu_jukebox_screen_custom_test"] == "Test Song"

    def test_with_intro(self, temp_mod_overrides: Path, sample_ogg: Path) -> None:
        result = create_music_mod(
            temp_mod_overrides, "custom_test", "Test Song", sample_ogg, intro_ogg_path=sample_ogg
        )
        assert (result / "sounds" / "menu_intro.ogg").exists()
        xml_text = (result / "main.xml").read_text()
        assert 'start_source="sounds/menu_intro.ogg"' in xml_text

    def test_folder_name_sanitized(
        self, temp_mod_overrides: Path, sample_ogg: Path
    ) -> None:
        result = create_music_mod(
            temp_mod_overrides, "custom_test", "Test///Song!!!", sample_ogg
        )
        assert "TestSong" in result.name

    def test_parses_back_correctly(
        self, temp_mod_overrides: Path, sample_ogg: Path
    ) -> None:
        create_music_mod(
            temp_mod_overrides, "roundtrip", "Round Trip", sample_ogg, volume=0.3
        )
        mods = list_mods(temp_mod_overrides)
        assert len(mods) == 1
        assert mods[0].track_id == "roundtrip"
        assert mods[0].volume == 0.3


class TestGetDisplayName:
    def test_returns_mod_name_when_no_loc(
        self, music_mod: MusicMod
    ) -> None:
        assert get_display_name(music_mod) == "FabienK Menu Track"

    def test_returns_localized_name(
        self, music_mod: MusicMod, tmp_path: Path
    ) -> None:
        mod_dir = tmp_path / "mod"
        mod_dir.mkdir()
        loc_dir = mod_dir / "loc"
        loc_dir.mkdir()
        loc_file = loc_dir / "en.txt"
        loc_file.write_text(
            json.dumps({"menu_jukebox_custom_12345678": "FabienK Display"})
        )
        music_mod.folder_path = mod_dir
        assert get_display_name(music_mod) == "FabienK Display"

    def test_falls_back_on_bad_json(
        self, music_mod: MusicMod, tmp_path: Path
    ) -> None:
        mod_dir = tmp_path / "mod"
        mod_dir.mkdir()
        loc_dir = mod_dir / "loc"
        loc_dir.mkdir()
        loc_file = loc_dir / "en.txt"
        loc_file.write_text("not valid json")
        music_mod.folder_path = mod_dir
        assert get_display_name(music_mod) == "FabienK Menu Track"


class TestUpdateDisplayName:
    def test_updates_loc_file(
        self, music_mod: MusicMod, tmp_path: Path
    ) -> None:
        mod_dir = tmp_path / "mod"
        mod_dir.mkdir()
        loc_dir = mod_dir / "loc"
        loc_dir.mkdir()
        (loc_dir / "en.txt").write_text(
            json.dumps({"menu_jukebox_custom_12345678": "Old Name"})
        )
        music_mod.folder_path = mod_dir
        update_display_name(music_mod, "New Name")
        data = json.loads((loc_dir / "en.txt").read_text())
        assert data["menu_jukebox_custom_12345678"] == "New Name"
        assert data["menu_jukebox_screen_custom_12345678"] == "New Name"

    def test_creates_loc_if_missing(
        self, music_mod: MusicMod, tmp_path: Path
    ) -> None:
        mod_dir = tmp_path / "mod"
        mod_dir.mkdir()
        loc_dir = mod_dir / "loc"
        loc_dir.mkdir()
        music_mod.folder_path = mod_dir
        update_display_name(music_mod, "Brand New")
        data = json.loads((loc_dir / "en.txt").read_text())
        assert data["menu_jukebox_custom_12345678"] == "Brand New"


class TestUpdateVolume:
    def test_updates_existing_volume_in_xml(
        self, music_mod: MusicMod, tmp_path: Path
    ) -> None:
        mod_dir = tmp_path / "mod"
        mod_dir.mkdir()
        xml_path = mod_dir / "main.xml"
        xml_path.write_text(
            '<table name="Test"><MenuMusic id="x" source="y.ogg" volume="0.4"/></table>'
        )
        music_mod.folder_path = mod_dir
        update_volume(music_mod, 0.7)
        assert 'volume="0.7"' in xml_path.read_text()

    def test_adds_volume_if_missing(
        self, music_mod: MusicMod, tmp_path: Path
    ) -> None:
        mod_dir = tmp_path / "mod"
        mod_dir.mkdir()
        xml_path = mod_dir / "main.xml"
        xml_path.write_text(
            '<table name="Test"><MenuMusic id="x" source="y.ogg"/></table>'
        )
        music_mod.folder_path = mod_dir
        update_volume(music_mod, 0.5)
        text = xml_path.read_text()
        assert 'volume="0.5"' in text or 'volume = "0.5"' in text


class TestDeleteMod:
    def test_deletes_directory(
        self, music_mod: MusicMod, tmp_path: Path
    ) -> None:
        mod_dir = tmp_path / "mod"
        mod_dir.mkdir()
        (mod_dir / "main.xml").write_text("<table/>")
        music_mod.folder_path = mod_dir
        assert mod_dir.exists()
        delete_mod(music_mod)
        assert not mod_dir.exists()
        assert music_mod.folder_path is None

    def test_no_error_if_missing(self) -> None:
        mod = MusicMod(name="Gone", track_id="gone")
        delete_mod(mod)
        # should not raise


class TestListMods:
    def test_empty_directory(self, tmp_path: Path) -> None:
        assert list_mods(tmp_path) == []

    def test_finds_music_mods(
        self, temp_mod_overrides: Path, sample_ogg: Path
    ) -> None:
        create_music_mod(temp_mod_overrides, "test1", "Song One", sample_ogg)
        create_music_mod(temp_mod_overrides, "test2", "Song Two", sample_ogg)
        mods = list_mods(temp_mod_overrides)
        assert len(mods) == 2

    def test_sorted_alphabetically(
        self, temp_mod_overrides: Path, sample_ogg: Path
    ) -> None:
        create_music_mod(temp_mod_overrides, "b", "Beta Song", sample_ogg)
        create_music_mod(temp_mod_overrides, "a", "Alpha Song", sample_ogg)
        mods = list_mods(temp_mod_overrides)
        assert mods[0].name == "Alpha Song Menu Track"
        assert mods[1].name == "Beta Song Menu Track"

    def test_skips_non_mod_folders(
        self, temp_mod_overrides: Path, sample_ogg: Path
    ) -> None:
        (temp_mod_overrides / "not_a_mod").mkdir()
        (temp_mod_overrides / "also_not").mkdir()
        mods = list_mods(temp_mod_overrides)
        assert mods == []

    def test_ignores_non_directories(
        self, temp_mod_overrides: Path
    ) -> None:
        (temp_mod_overrides / "file.txt").write_text("hi")
        mods = list_mods(temp_mod_overrides)
        assert mods == []
