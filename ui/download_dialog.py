from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout, QPushButton

from app.models import TrackInfo
from app.search_worker import SearchWorker


class DownloadWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(Path)
    error = Signal(str)

    def __init__(
        self,
        worker: SearchWorker,
        track: TrackInfo,
        output_path: Path,
        quality: str,
    ) -> None:
        super().__init__()
        self._worker = worker
        self._track = track
        self._output = output_path
        self._quality = quality

    async def _run_async(self) -> Path:
        stream_url = await self._worker.resolve_stream_url(self._track, self._quality)
        if not stream_url:
            raise RuntimeError("Could not resolve stream URL")
        return await self._worker.download_track(
            stream_url, self._output, self._emit_progress
        )

    def _emit_progress(self, current: int, total: int, stage: str) -> None:
        self.progress.emit(current, total, stage)

    def run(self) -> None:
        import asyncio
        try:
            result = asyncio.run(self._run_async())
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DownloadDialog(QDialog):
    def __init__(
        self,
        search_worker: SearchWorker,
        track: TrackInfo,
        output_path: Path,
        quality: str = "LOSSLESS",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._result_path: Optional[Path] = None
        self.setWindowTitle(f"Downloading: {track.title}")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        self._label = QLabel(f"Downloading {track.title} - {track.artist}")
        layout.addWidget(self._label)
        self._progress = QProgressBar()
        layout.addWidget(self._progress)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self._cancel_btn)
        self._worker = DownloadWorker(search_worker, track, output_path, quality)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, stage: str) -> None:
        if total > 0:
            pct = int(current / total * 100)
            self._progress.setValue(pct)
        self._label.setText(stage)

    def _on_finished(self, path: Path) -> None:
        self._result_path = path
        self.accept()

    def _on_error(self, msg: str) -> None:
        self._label.setText(f"Error: {msg}")
        self._cancel_btn.setText("Close")

    @property
    def result_path(self) -> Optional[Path]:
        return self._result_path
