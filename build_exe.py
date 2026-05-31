"""Build a standalone .exe for PD2 Menu Music Manager."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SPEC = HERE / "PD2 Menu Music Manager.spec"


def main() -> None:
    cmd = ["pyinstaller"]
    if SPEC.exists():
        cmd.append(str(SPEC))
    else:
        cmd += [
            "--windowed",
            "--onefile",
            "--name", "PD2 Menu Music Manager",
            "--hidden-import", "PIL.Image",
            "--hidden-import", "ui.settings_dialog",
            str(HERE / "main.py"),
        ]
    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=HERE)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
