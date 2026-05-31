# PD2 Menu Music Manager

A desktop GUI tool for searching, downloading, converting, and installing custom menu music mods for **PAYDAY 2**.

## Features

- **Search** - Query community-hosted HiFi music APIs for tracks
- **Stream resolution** - Resolve stream URLs via Qobuz API instances using ISRC codes
- **Download & convert** - Downloads audio and converts to OGG Vorbis (libvorbis) using FFmpeg
- **Auto-mod creation** - Generates `main.xml` with `<MenuMusic>`, localization, and fetches album art
- **Mod management** - Browse, rename, adjust volume, preview, and delete installed music mods
- **FFmpeg auto-download** - Automatically downloads FFmpeg from BtbN builds if not found

## Requirements

- Python 3.12+
- Windows (for the pre-built .exe; the Python source works cross-platform with modifications)
- BeardLib mod installed for Payday 2

## Quick Start (from source)

```bash
pip install -r requirements.txt
python main.py
```

## Build standalone .exe

```bash
pip install -r requirements.txt
python build_exe.py
```

Or directly with PyInstaller:

```bash
pyinstaller "PD2 Menu Music Manager.spec"
```

The compiled `.exe` will be in `dist/`.

## Usage

1. Launch the application
2. Set your PAYDAY 2 `mod_overrides` path in Settings
3. Search for a track
4. Click Download - the tool creates a proper mod folder with `main.xml`
5. Launch PAYDAY 2 and enable the mod

## Downloads

Pre-built binaries are available on the [Releases](https://github.com/jacket430/pd2-menu-music-manager/releases) page.
