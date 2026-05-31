from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TrackInfo:
    id: str
    title: str
    artist: str
    album: str
    duration: int
    isrc: Optional[str] = None
    cover_url: Optional[str] = None
    provider: str = "tidal"


@dataclass
class SearchResult:
    query: str
    tracks: list[TrackInfo] = field(default_factory=list)
    total_results: int = 0


@dataclass
class StreamInfo:
    url: str
    mime_type: str = "audio/ogg"
    quality: str = "LOSSLESS"


@dataclass
class MusicMod:
    name: str
    track_id: str
    volume: float = 0.4
    has_intro: bool = False
    folder_path: Optional[Path] = None

    @property
    def localization_key(self) -> str:
        return f"menu_jukebox_{self.track_id}"

    @property
    def screen_key(self) -> str:
        return f"menu_jukebox_screen_{self.track_id}"

    def to_xml(self) -> str:
        intro_attr = f' start_source="sounds/menu_intro.ogg"' if self.has_intro else ""
        return (
            f'<table name="{self.name}">\n'
            f'    <Localization directory="loc" default="en.txt"/>\n'
            f'    <MenuMusic id="{self.track_id}"{intro_attr} source="sounds/menu_loop.ogg" volume="{self.volume}"/>\n'
            f"</table>\n"
        )

    def to_localization(self, display_name: str) -> str:
        return (
            "{\n"
            f'    "{self.localization_key}" : "{display_name}",\n'
            f'    "{self.screen_key}" : "{display_name}"\n'
            "}\n"
        )


INSTANCES_URL = "https://tidal-uptime.geeked.wtf"

FALLBACK_API_INSTANCES = [
    "https://hifi.geeked.wtf",
    "https://eu-central.monochrome.tf",
    "https://us-west.monochrome.tf",
    "https://api.monochrome.tf",
    "https://monochrome-api.samidy.com",
    "https://wolf.qqdl.site",
    "https://vogel.qqdl.site",
]

FALLBACK_QOBUZ_INSTANCES = [
    "https://qdl-api.monochrome.tf",
    "https://qobuz.kennyy.com.br",
    "https://mono.scavengerfurs.net",
]

QUALITY_MAP = {
    "HI_RES_LOSSLESS": "27",
    "LOSSLESS": "6",
    "HIGH": "5",
}

QUALITY_LABELS = {
    "HI_RES_LOSSLESS": "24-bit FLAC",
    "LOSSLESS": "16-bit FLAC (CD quality)",
    "HIGH": "320kbps MP3/AAC",
}
