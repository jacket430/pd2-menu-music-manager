from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import httpx

from .models import MusicMod


def _parse_mods(mod_overrides_path: Path) -> list[MusicMod]:
    results: list[MusicMod] = []
    if not mod_overrides_path.is_dir():
        return results
    for folder in mod_overrides_path.iterdir():
        if not folder.is_dir():
            continue
        main_xml = folder / "main.xml"
        if not main_xml.exists():
            continue
        mod = _parse_main_xml(main_xml)
        if mod:
            mod.folder_path = folder
            results.append(mod)
    results.sort(key=lambda m: m.name.lower())
    return results


def _parse_main_xml(path: Path) -> Optional[MusicMod]:
    text = path.read_text("utf-8", errors="replace")
    name_match = re.search(r'<table\s+name="([^"]+)"', text)
    if not name_match:
        return None
    name = name_match.group(1)
    music_match = re.search(
        r"<MenuMusic\s+([^>]+)>", text, re.IGNORECASE
    )
    if not music_match:
        return None
    attrs = music_match.group(1)
    track_id = _xml_attr(attrs, "id") or ""
    vol_str = _xml_attr(attrs, "volume") or "0.4"
    volume = float(vol_str)
    has_intro = bool(_xml_attr(attrs, "start_source"))
    return MusicMod(
        name=name,
        track_id=track_id,
        volume=volume,
        has_intro=has_intro,
        folder_path=path.parent,
    )


def _xml_attr(attrs_text: str, name: str) -> Optional[str]:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', attrs_text)
    return m.group(1) if m else None


def create_music_mod(
    mod_overrides_path: Path,
    track_id: str,
    display_name: str,
    loop_ogg_path: Path,
    intro_ogg_path: Optional[Path] = None,
    volume: float = 0.4,
    cover_url: Optional[str] = None,
) -> Path:
    safe_name = re.sub(r"[^\w\s-]", "", display_name).strip()
    if not safe_name:
        safe_name = track_id
    mod_dir = mod_overrides_path / f"{safe_name} Menu Track"
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "sounds").mkdir(exist_ok=True)
    (mod_dir / "loc").mkdir(exist_ok=True)

    _copy_ogg(loop_ogg_path, mod_dir / "sounds" / "menu_loop.ogg")
    if intro_ogg_path:
        _copy_ogg(intro_ogg_path, mod_dir / "sounds" / "menu_intro.ogg")

    if cover_url:
        _download_icon(cover_url, mod_dir / "icon.png")

    mod = MusicMod(
        name=f"{display_name} Menu Track",
        track_id=track_id,
        volume=volume,
        has_intro=intro_ogg_path is not None,
        folder_path=mod_dir,
    )
    xml_path = mod_dir / "main.xml"
    xml_path.write_text(mod.to_xml(), "utf-8")

    loc_path = mod_dir / "loc" / "en.txt"
    loc_path.write_text(mod.to_localization(display_name), "utf-8")

    return mod_dir


def _copy_ogg(src: Path, dst: Path) -> None:
    import shutil
    if src.suffix.lower() == ".ogg":
        shutil.copy2(src, dst)
    else:
        from .ffmpeg_manager import FFmpegManager
        ffmpeg = FFmpegManager.instance()
        ffmpeg.convert_to_ogg(src, dst)


def _download_icon(cover_url: str, dst: Path) -> None:
    import io
    resp = httpx.get(cover_url, follow_redirects=True, timeout=15)
    resp.raise_for_status()
    from PIL import Image
    img = Image.open(io.BytesIO(resp.content))
    # If image has transparency, keep it; otherwise convert to RGB for smaller PNG
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.save(dst, "PNG")


def get_display_name(mod: MusicMod) -> str:
    if not mod.folder_path:
        return mod.name
    loc_file = mod.folder_path / "loc" / "en.txt"
    if not loc_file.exists():
        return mod.name
    try:
        data = json.loads(loc_file.read_text("utf-8", errors="replace"))
        return data.get(mod.localization_key, mod.name)
    except (json.JSONDecodeError, KeyError):
        return mod.name


def update_display_name(mod: MusicMod, new_name: str) -> None:
    if not mod.folder_path:
        return
    loc_file = mod.folder_path / "loc" / "en.txt"
    try:
        data = json.loads(loc_file.read_text("utf-8", errors="replace"))
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}
    data[mod.localization_key] = new_name
    data[mod.screen_key] = new_name
    loc_file.write_text(json.dumps(data, indent=4), "utf-8")


def update_volume(mod: MusicMod, new_volume: float) -> None:
    if not mod.folder_path:
        return
    mod.volume = new_volume
    main_xml = mod.folder_path / "main.xml"
    if main_xml.exists():
        text = main_xml.read_text("utf-8", errors="replace")
        text = re.sub(
            r'(volume\s*=\s*)"[^"]*"',
            rf'\1"{new_volume}"',
            text,
        )
        if f'volume="{new_volume}"' not in text:
            text = re.sub(
                r'(<MenuMusic[^>]*?)(\s*/>)',
                rf'\1 volume="{new_volume}"\2',
                text,
            )
        main_xml.write_text(text, "utf-8")


def delete_mod(mod: MusicMod) -> None:
    if mod.folder_path and mod.folder_path.exists():
        import shutil
        shutil.rmtree(mod.folder_path)
        mod.folder_path = None


def list_mods(mod_overrides_path: Path) -> list[MusicMod]:
    return _parse_mods(mod_overrides_path)
