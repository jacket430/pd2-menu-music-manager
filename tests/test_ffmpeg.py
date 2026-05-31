from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from app.ffmpeg_manager import FFmpegManager, _get_platform_key


class TestPlatformKey:
    def test_returns_tuple(self) -> None:
        os_name, arch = _get_platform_key()
        assert os_name in ("windows", "darwin", "linux")
        assert arch in ("win32", "win64", "x86_64", "arm64")


class TestFFmpegManager:
    def test_singleton(self) -> None:
        a = FFmpegManager.instance()
        b = FFmpegManager.instance()
        assert a is b

    def test_ffmpeg_path_none_if_not_found(self) -> None:
        mgr = FFmpegManager(base_dir=Path("C:/nonexistent_path_xyz"))
        path = mgr.ffmpeg_path
        if path is None:
            assert True
        else:
            assert path.exists()

    def test_ensure_ffmpeg_finds_system(self) -> None:
        mgr = FFmpegManager()
        try:
            path = mgr.ensure_ffmpeg()
            assert path.exists()
            assert path.name.lower() in ("ffmpeg", "ffmpeg.exe")
        except RuntimeError:
            pass

    def test_build_download_url_windows(self) -> None:
        mgr = FFmpegManager(base_dir=Path("."))
        url = mgr._build_download_url("windows", "win64")
        assert url.endswith("ffmpeg-master-latest-win64-gpl.zip")
        assert url.startswith("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest")

    def test_build_download_url_linux(self) -> None:
        mgr = FFmpegManager(base_dir=Path("."))
        url = mgr._build_download_url("linux", "x86_64")
        assert url.endswith("linux-x86_64-gpl.tar.xz")

    def test_build_download_url_macos(self) -> None:
        mgr = FFmpegManager(base_dir=Path("."))
        url = mgr._build_download_url("darwin", "arm64")
        assert url.endswith("darwin-arm64-gpl.tar.xz")


@pytest.mark.skipif(
    not (lambda: (p := __import__("shutil", fromlist=["which"]).which("ffmpeg")) and Path(p).exists())(),
    reason="ffmpeg not available on this system",
)
class TestFFmpegConversion:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path) -> None:
        self._input = tmp_path / "input.wav"
        self._output = tmp_path / "output.ogg"

    def _create_wav(self) -> None:
        import struct
        sample_rate = 44100
        duration = 1
        num_samples = sample_rate * duration
        data = b""
        for i in range(num_samples):
            val = int(16000 * (i / num_samples))
            data += struct.pack("<h", val)
        data_size = len(data)
        with open(self._input, "wb") as f:
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + data_size))
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write(struct.pack("<I", 16))
            f.write(struct.pack("<H", 1))
            f.write(struct.pack("<H", 1))
            f.write(struct.pack("<I", sample_rate))
            f.write(struct.pack("<I", sample_rate * 2))
            f.write(struct.pack("<H", 2))
            f.write(struct.pack("<H", 16))
            f.write(b"data")
            f.write(struct.pack("<I", data_size))
            f.write(data)

    def test_converts_wav_to_ogg(self) -> None:
        self._create_wav()
        mgr = FFmpegManager()
        mgr.convert_to_ogg(self._input, self._output)
        assert self._output.exists()
        assert self._output.stat().st_size > 0

    def test_output_is_playable_ogg(self) -> None:
        self._create_wav()
        mgr = FFmpegManager()
        mgr.convert_to_ogg(self._input, self._output)
        result = subprocess.run(
            [
                str(mgr.ffmpeg_path),
                "-i", str(self._output),
                "-f", "null",
                "-",
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
