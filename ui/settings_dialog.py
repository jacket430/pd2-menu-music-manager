from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.models import QUALITY_LABELS


class SettingsDialog(QDialog):
    def __init__(
        self,
        current_mod_overrides: str,
        current_quality: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._result_mod_overrides: str = current_mod_overrides
        self._result_quality: str = current_quality
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        mo_layout = QHBoxLayout()
        self._mo_path = QLineEdit(current_mod_overrides)
        self._mo_path.setReadOnly(True)
        mo_layout.addWidget(self._mo_path)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        mo_layout.addWidget(browse_btn)
        form.addRow("mod_overrides path:", mo_layout)
        label = QLabel(
            "Path to assets/mod_overrides in your PAYDAY 2 install"
        )
        label.setStyleSheet("color: gray; font-size: 10px;")
        form.addRow("", label)
        self._quality_combo = QComboBox()
        for key, label_text in QUALITY_LABELS.items():
            self._quality_combo.addItem(f"{label_text} ({key})", key)
        idx = self._quality_combo.findData(current_quality)
        if idx >= 0:
            self._quality_combo.setCurrentIndex(idx)
        form.addRow("Download quality:", self._quality_combo)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select mod_overrides directory"
        )
        if path:
            self._mo_path.setText(path)

    def _accept(self) -> None:
        self._result_mod_overrides = self._mo_path.text()
        self._result_quality = self._quality_combo.currentData()
        self.accept()

    @property
    def mod_overrides_path(self) -> str:
        return self._result_mod_overrides

    @property
    def quality(self) -> str:
        return self._result_quality
