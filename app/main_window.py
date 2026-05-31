from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QMessageBox,
)

from app.ffmpeg_manager import FFmpegManager
from app.mod_manager import list_mods
from app.search_worker import SearchWorker
from app.source_manager import SourceManager
from ui.mod_list_panel import ModListPanel
from ui.search_panel import SearchPanel
from ui.settings_dialog import SettingsDialog


def _default_mod_overrides() -> Path:
    home = Path.home()
    candidates = [
        home / "Documents" / "PAYDAY 2" / "mod_overrides",
        Path("C:/Program Files (x86)/Steam/steamapps/common/PAYDAY 2/assets/mod_overrides"),
        Path("C:/Program Files/Steam/steamapps/common/PAYDAY 2/assets/mod_overrides"),
        Path("D:/SteamLibrary/steamapps/common/PAYDAY 2/assets/mod_overrides"),
        home / "AppData/Local/PAYDAY 2/assets/mod_overrides",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings("PD2ModTools", "MenuMusicManager")
        self._source_manager = SourceManager()
        self._search_worker = SearchWorker(self._source_manager)
        self._ffmpeg = FFmpegManager.instance()

        mo_path = self._settings.value("mod_overrides_path", "")
        self._mod_overrides_path = Path(mo_path) if mo_path else _default_mod_overrides()
        self._quality = self._settings.value("quality", "LOSSLESS")

        self.setWindowTitle("PD2 Menu Music Manager")
        self.setMinimumSize(800, 600)

        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        self._search_panel = SearchPanel(
            self._search_worker,
            self._mod_overrides_path,
            self._quality,
        )
        self._search_panel.mods_changed.connect(self._on_mods_changed)
        self._tabs.addTab(self._search_panel, "Search & Download")

        self._mod_list_panel = ModListPanel(self._mod_overrides_path)
        self._tabs.addTab(self._mod_list_panel, "Installed Mods")

        self._init_menu()
        self._init_ffmpeg()
        self._init_sources()
        self._mod_list_panel.refresh()

    def _init_menu(self) -> None:
        from PySide6.QtGui import QAction
        menu = self.menuBar()
        settings_menu = menu.addMenu("Settings")
        pref_action = QAction("Preferences...", self)
        pref_action.triggered.connect(self._open_settings)
        settings_menu.addAction(pref_action)
        help_menu = menu.addMenu("Help")
        about_action = QAction("About...", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_ffmpeg(self) -> None:
        if not self._ffmpeg.ffmpeg_path:
            try:
                self._ffmpeg.ensure_ffmpeg()
            except Exception:
                pass

    def _init_sources(self) -> None:
        try:
            asyncio.run(self._source_manager.refresh_instances())
        except Exception:
            pass

    def _open_settings(self) -> None:
        dlg = SettingsDialog(
            str(self._mod_overrides_path),
            self._quality,
            self,
        )
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            new_path = dlg.mod_overrides_path
            self._mod_overrides_path = Path(new_path)
            self._settings.setValue("mod_overrides_path", new_path)
            self._quality = dlg.quality
            self._settings.setValue("quality", self._quality)
            self._search_panel.set_mod_overrides_path(self._mod_overrides_path)
            self._search_panel.set_quality(self._quality)
            self._mod_list_panel.set_mod_overrides_path(self._mod_overrides_path)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About PD2 Menu Music Manager",
            "A tool to search, download, and create Payday 2 menu music mods.\n\n"
            "Uses community-hosted HiFi API instances "
            "(from the Monochrome project) for TIDAL search and Qobuz for stream URLs.",
        )

    def _on_mods_changed(self) -> None:
        self._mod_list_panel.refresh()
