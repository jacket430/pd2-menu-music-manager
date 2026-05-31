from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QInputDialog,
    QDoubleSpinBox,
    QFormLayout,
    QDialog,
)

from app.mod_manager import (
    delete_mod,
    get_display_name,
    list_mods,
    update_display_name,
    update_volume,
)
from app.models import MusicMod


class VolumeDialog(QDialog):
    def __init__(self, current_vol: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Volume")
        self.setMinimumWidth(250)
        layout = QFormLayout(self)
        self._spin = QDoubleSpinBox()
        self._spin.setRange(0.0, 1.0)
        self._spin.setSingleStep(0.05)
        self._spin.setValue(current_vol)
        layout.addRow("Volume (0–1):", self._spin)
        from PySide6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @property
    def volume(self) -> float:
        return self._spin.value()


class ModListPanel(QWidget):
    def __init__(self, mod_overrides_path: Path, parent=None) -> None:
        super().__init__(parent)
        self._mod_overrides_path = mod_overrides_path
        self._mods: list[MusicMod] = []
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.errorOccurred.connect(
            lambda err, msg: self._status.setText(f"Playback error: {msg}")
        )
        self._player.mediaStatusChanged.connect(self._on_media_status)
        layout = QVBoxLayout(self)
        header = QLabel("Installed Menu Music Mods")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Name", "Track ID", "Volume"])
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self._table)
        btn_row = QHBoxLayout()
        self._preview_btn = QPushButton("Preview")
        self._preview_btn.setEnabled(False)
        self._preview_btn.clicked.connect(self._preview)
        btn_row.addWidget(self._preview_btn)
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_preview)
        btn_row.addWidget(self._stop_btn)
        self._rename_btn = QPushButton("Rename")
        self._rename_btn.setEnabled(False)
        self._rename_btn.clicked.connect(self._rename)
        btn_row.addWidget(self._rename_btn)
        self._volume_btn = QPushButton("Edit Volume")
        self._volume_btn.setEnabled(False)
        self._volume_btn.clicked.connect(self._edit_volume)
        btn_row.addWidget(self._volume_btn)
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(self._delete_btn)
        layout.addLayout(btn_row)
        self._status = QLabel("")
        self._status.setStyleSheet("color: gray;")
        layout.addWidget(self._status)
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(40)
        self._volume_slider.valueChanged.connect(self._slider_changed)
        layout.addWidget(self._volume_slider)

    def refresh(self) -> None:
        self._mods = list_mods(self._mod_overrides_path)
        self._table.setRowCount(len(self._mods))
        for i, mod in enumerate(self._mods):
            display = get_display_name(mod)
            self._table.setItem(i, 0, QTableWidgetItem(display))
            self._table.setItem(i, 1, QTableWidgetItem(mod.track_id))
            self._table.setItem(i, 2, QTableWidgetItem(str(mod.volume)))
        self._update_status()

    def set_mod_overrides_path(self, path: Path) -> None:
        self._mod_overrides_path = path
        self.refresh()

    def _on_selection(self) -> None:
        has_selection = bool(self._table.selectedItems())
        self._preview_btn.setEnabled(has_selection)
        self._rename_btn.setEnabled(has_selection)
        self._volume_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)

    def _selected_mod(self) -> Optional[MusicMod]:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        idx = rows[0].row()
        if 0 <= idx < len(self._mods):
            return self._mods[idx]
        return None

    def _preview(self) -> None:
        mod = self._selected_mod()
        if not mod or not mod.folder_path:
            return
        loop_path = mod.folder_path / "sounds" / "menu_loop.ogg"
        if loop_path.exists():
            self._player.setSource(QUrl.fromLocalFile(str(loop_path)))
            self._audio_output.setVolume(self._volume_slider.value() / 100.0)
            self._player.play()
            self._stop_btn.setEnabled(True)
            self._status.setText(f"Playing: {get_display_name(mod)}")

    def _stop_preview(self) -> None:
        self._player.stop()
        self._stop_btn.setEnabled(False)
        self._status.setText("")

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._player.setPosition(0)
            self._player.play()

    def _slider_changed(self, val: int) -> None:
        self._audio_output.setVolume(val / 100.0)

    def _rename(self) -> None:
        mod = self._selected_mod()
        if not mod:
            return
        current = get_display_name(mod)
        name, ok = QInputDialog.getText(self, "Rename Mod", "Display name:", text=current)
        if ok and name.strip():
            update_display_name(mod, name.strip())
            self.refresh()

    def _edit_volume(self) -> None:
        mod = self._selected_mod()
        if not mod:
            return
        dlg = VolumeDialog(mod.volume, self)
        if dlg.exec() == VolumeDialog.DialogCode.Accepted:
            update_volume(mod, dlg.volume)
            self.refresh()

    def _delete(self) -> None:
        mod = self._selected_mod()
        if not mod:
            return
        name = get_display_name(mod)
        reply = QMessageBox.question(
            self,
            "Delete Mod",
            f'Delete "{name}"?\nThis cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_mod(mod)
            self.refresh()

    def _update_status(self) -> None:
        count = len(self._mods)
        self._status.setText(f"{count} music mod(s) installed")
