from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QMessageBox,
)

from app.models import TrackInfo
from app.mod_manager import create_music_mod
from app.search_worker import SearchWorker
from ui.download_dialog import DownloadDialog


class SearchThread(QThread):
    results = Signal(list)
    error = Signal(str)

    def __init__(self, worker: SearchWorker, query: str) -> None:
        super().__init__()
        self._worker = worker
        self._query = query

    async def _run_async(self) -> list:
        return await self._worker.search(self._query)

    def run(self) -> None:
        try:
            tracks = asyncio.run(self._run_async())
            self.results.emit(tracks)
        except Exception as e:
            self.error.emit(str(e))


class SearchPanel(QWidget):
    mods_changed = Signal()

    def __init__(
        self,
        search_worker: SearchWorker,
        mod_overrides_path: Path,
        quality: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._worker = search_worker
        self._mod_overrides_path = mod_overrides_path
        self._quality = quality
        self._tracks: list[TrackInfo] = []
        self._search_thread: Optional[SearchThread] = None
        layout = QVBoxLayout(self)
        search_row = QHBoxLayout()
        self._query_input = QLineEdit()
        self._query_input.setPlaceholderText("Search for a song...")
        self._query_input.returnPressed.connect(self._do_search)
        search_row.addWidget(self._query_input)
        self._search_btn = QPushButton("Search")
        self._search_btn.clicked.connect(self._do_search)
        search_row.addWidget(self._search_btn)
        layout.addLayout(search_row)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Title", "Artist", "Album", "Duration"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemDoubleClicked.connect(self._download_selected)
        layout.addWidget(self._table)
        btn_row = QHBoxLayout()
        self._download_btn = QPushButton("Download && Create Mod")
        self._download_btn.setEnabled(False)
        self._download_btn.clicked.connect(self._download_selected)
        btn_row.addWidget(self._download_btn)
        btn_row.addStretch()
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(5, 100)
        self._volume_slider.setValue(100)
        self._volume_slider.setFixedWidth(120)
        self._volume_spin = QSpinBox()
        self._volume_spin.setRange(5, 100)
        self._volume_spin.setValue(100)
        self._volume_slider.valueChanged.connect(self._volume_spin.setValue)
        self._volume_spin.valueChanged.connect(self._volume_slider.setValue)
        btn_row.addWidget(QLabel("In-game volume %:"))
        btn_row.addWidget(self._volume_slider)
        btn_row.addWidget(self._volume_spin)
        layout.addLayout(btn_row)
        self._status = QLabel("")
        self._status.setStyleSheet("color: gray;")
        layout.addWidget(self._status)

    def set_mod_overrides_path(self, path: Path) -> None:
        self._mod_overrides_path = path

    def set_quality(self, quality: str) -> None:
        self._quality = quality

    def _do_search(self) -> None:
        query = self._query_input.text().strip()
        if not query:
            return
        self._tracks.clear()
        self._table.setRowCount(0)
        self._download_btn.setEnabled(False)
        self._search_btn.setEnabled(False)
        self._status.setText("Searching...")
        self._search_thread = SearchThread(self._worker, query)
        self._search_thread.results.connect(self._on_results)
        self._search_thread.error.connect(self._on_search_error)
        self._search_thread.start()

    def _on_results(self, tracks: list[TrackInfo]) -> None:
        self._tracks = tracks
        self._table.setRowCount(len(tracks))
        for i, t in enumerate(tracks):
            self._table.setItem(i, 0, QTableWidgetItem(t.title))
            self._table.setItem(i, 1, QTableWidgetItem(t.artist))
            self._table.setItem(i, 2, QTableWidgetItem(t.album))
            mins = t.duration // 60
            secs = t.duration % 60
            self._table.setItem(i, 3, QTableWidgetItem(f"{mins}:{secs:02d}"))
        self._download_btn.setEnabled(len(tracks) > 0)
        self._search_btn.setEnabled(True)
        self._status.setText(f"Found {len(tracks)} result(s)")

    def _on_search_error(self, msg: str) -> None:
        self._search_btn.setEnabled(True)
        self._status.setText(f"Search failed: {msg}")

    def _download_selected(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if idx < 0 or idx >= len(self._tracks):
            return
        track = self._tracks[idx]
        name, ok = QInputDialog.getText(
            self, "Mod Name", "Display name for the jukebox:",
            text=track.title,
        )
        if not ok or not name.strip():
            return
        target = (Path(tempfile.gettempdir()) / "pd2_menu_music_download" / f"{track.id}.ogg").resolve()
        dlg = DownloadDialog(self._worker, track, target, self._quality, self)
        if dlg.exec() == DownloadDialog.DialogCode.Accepted and dlg.result_path:
            try:
                create_music_mod(
                    mod_overrides_path=self._mod_overrides_path,
                    track_id=f"custom_{track.id}",
                    display_name=name.strip(),
                    loop_ogg_path=dlg.result_path,
                    volume=self._volume_spin.value() / 100.0,
                    cover_url=track.cover_url,
                )
                target.unlink(missing_ok=True)
                QMessageBox.information(
                    self, "Success", f'Created mod "{name.strip()}" in mod_overrides.'
                )
                self.mods_changed.emit()
            except Exception as e:
                target.unlink(missing_ok=True)
                QMessageBox.critical(self, "Error", f"Failed to create mod: {e}")
