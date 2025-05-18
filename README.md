# Houdini Cache Manager

A custom PySide2-based tool for SideFX Houdini that visually manages simulation cache directories. It enables quick inspection, safe deletion, and version matching of cache folders directly within Houdini.

![screenshot](docs/screenshot.png) <!-- Replace or remove if no image available -->

---

## Features

- 📁 **Tree-based Cache Viewer**
  - Automatically loads all directories under `$CACHEPATH`
  - Displays comment, size, and modification date
- 🔒 **Protection System** <- Not implemented yet
  - Reads `cacheinfo.json` to detect and lock protected caches
  - Prevents accidental deletion
- 🔍 **Version Matching** <- Works 
  - Automatically highlights folders that match parameters from `filecache::2.0` nodes
- 🧹 **Safe Deletion**
  - Only allows deletion of folders without children
  - Confirm-before-delete prompt
- 🧠 **Metadata Awareness** <- Not implemented yet
  - Displays comments stored in `cacheinfo.json`

---

## Requirements

- Houdini 18.5+
- Python 3 (used by Houdini internally)
- Houdini environment variable: `$CACHEPATH`

---

## Installation

1. Create shelf tool and paste the code.

## Limitation

1. Tested in Linux (Debian based) OS only.
2. Some features may not work (Some features definitely does not work)
