from __future__ import annotations

import os
import shutil
import stat
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Optional

import httpx


def _get_platform_key() -> tuple[str, str]:
    import platform
    machine = platform.machine().lower()
    system = platform.system().lower()
    if system == "windows":
        return "windows", "win64" if "64" in machine else "win32"
    if system == "darwin":
        arch = "arm64" if machine in ("arm64", "aarch64") else "x86_64"
        return "darwin", arch
    arch = "arm64" if machine in ("arm64", "aarch64") else "x86_64"
    return "linux", arch


class FFmpegManager:
    _instance: Optional[FFmpegManager] = None

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base = Path(base_dir or Path.cwd() / ".ffmpeg")
        self._bin_path: Optional[Path] = None

    @classmethod
    def instance(cls, base_dir: Optional[Path] = None) -> FFmpegManager:
        if cls._instance is None:
            cls._instance = cls(base_dir)
        return cls._instance

    @property
    def ffmpeg_path(self) -> Optional[Path]:
        if self._bin_path and self._bin_path.exists():
            return self._bin_path
        system_path = shutil.which("ffmpeg")
        if system_path:
            return Path(system_path)
        return None

    def ensure_ffmpeg(self) -> Path:
        existing = self.ffmpeg_path
        if existing:
            return existing
        return self._download()

    def _download(self) -> Path:
        self._base.mkdir(parents=True, exist_ok=True)
        os_name, arch = _get_platform_key()
        url = self._build_download_url(os_name, arch)
        dest = self._base / "ffmpeg_download"
        dest.mkdir(exist_ok=True)
        archive_path = dest / "ffmpeg_archive"
        with httpx.Client(follow_redirects=True, timeout=60) as client:
            response = client.get(url)
            response.raise_for_status()
            archive_path.write_bytes(response.content)
        if os_name == "windows":
            extract_dir = dest / "ffmpeg_extracted"
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(extract_dir)
            for candidate in extract_dir.rglob("ffmpeg.exe"):
                shutil.copy2(candidate, self._base / "ffmpeg.exe")
                self._bin_path = self._base / "ffmpeg.exe"
                break
        else:
            extract_dir = dest / "ffmpeg_extracted"
            with tarfile.open(archive_path) as tf:
                tf.extractall(extract_dir)
            for candidate in extract_dir.rglob("ffmpeg"):
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    shutil.copy2(candidate, self._base / "ffmpeg")
                    st = (self._base / "ffmpeg").stat()
                    os.chmod(self._base / "ffmpeg", st.st_mode | stat.S_IEXEC)
                    self._bin_path = self._base / "ffmpeg"
                    break
        shutil.rmtree(dest, ignore_errors=True)
        if self._bin_path is None or not self._bin_path.exists():
            raise RuntimeError("Could not locate ffmpeg binary after download")
        return self._bin_path

    def _build_download_url(self, os_name: str, arch: str) -> str:
        base = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
        if os_name == "windows":
            return f"{base}/ffmpeg-master-latest-win64-gpl.zip"
        if os_name == "darwin":
            return f"{base}/ffmpeg-master-latest-{os_name}-{arch}-gpl.tar.xz"
        return f"{base}/ffmpeg-master-latest-{os_name}-{arch}-gpl.tar.xz"

    def convert_to_ogg(
        self, input_path: Path, output_path: Path, progress_cb=None
    ) -> None:
        ffmpeg = self.ensure_ffmpeg()
        cmd = [
            str(ffmpeg),
            "-y",
            "-i", str(input_path),
            "-c:a", "libvorbis",
            "-q:a", "3",
            "-vn",
            str(output_path),
        ]
        import subprocess
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed:\n{stderr}")
