# CodeViz PRD

## Overview

A CLI tool that generates 3D "Code Park" style visualizations of codebases, viewable in VR on Quest 3 via WebXR.

## MVP Scope

**In scope:**
- Local filesystem path as input
- Blender Python script for 3D scene generation
- Code Park style: files as rooms with syntax-highlighted code on walls
- Export to glTF/GLB format
- Simple WebXR viewer (Three.js) for Quest 3 browser
- Basic navigation (teleport locomotion)

**Out of scope (future):**
- GitHub integration / OAuth
- Voice queries / AI chat
- Real-time code updates
- Dependency graph visualization
- Collaborative viewing

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────┐
│  Codebase   │ ──▶ │  CLI + Blender  │ ──▶ │   scene.glb     │ ──▶ │  WebXR      │
│  (local)    │     │  Python Script  │     │   (3D scene)    │     │  Viewer     │
└─────────────┘     └─────────────────┘     └─────────────────┘     └─────────────┘
```

## Component Details

### 1. CLI (`cli.py`)

**Input:**
```bash
codeviz generate --path /path/to/codebase --output scene.glb
```

**Options:**
- `--path` — Root directory of codebase (required)
- `--output` — Output glTF/GLB file (default: `./scene.glb`)
- `--extensions` — File extensions to include (default: common code files)
- `--max-files` — Limit number of files for performance (default: 100)
- `--max-lines` — Max lines per file to render (default: 200)

### 2. Parser Module (`parser/`)

**Responsibilities:**
- Walk directory tree, respecting .gitignore
- Read file contents
- Extract metrics: LOC, file size, extension/language
- Tokenize code for syntax highlighting (use Pygments)

**Output:** JSON intermediate representation
```json
{
  "files": [
    {
      "path": "src/main.py",
      "language": "python",
      "loc": 150,
      "tokens": [
        {"type": "keyword", "value": "def", "line": 1},
        {"type": "function", "value": "main", "line": 1}
      ]
    }
  ],
  "directories": [
    {"path": "src", "file_count": 10}
  ]
}
```

### 3. Layout Module (`layout/`)

**Responsibilities:**
- Arrange rooms in 3D space
- Group by directory (rooms in same dir are adjacent)
- Scale room size by LOC

**Layout algorithm (MVP):**
- Grid layout within each directory
- Directories arranged in a larger grid
- Hallways connecting directory clusters

**Room dimensions:**
- Width: fixed (e.g., 4 units)
- Depth: scales with LOC (more lines = deeper room)
- Height: fixed (e.g., 3 units)
- Wall coverage: code wraps around 3 walls

### 4. Blender Generator (`blender_gen.py`)

**Runs via:** `blender --background --python blender_gen.py -- <args>`

**Responsibilities:**
- Create room geometry (floor, walls, ceiling)
- Generate code textures:
  - Render syntax-highlighted code to image using PIL/Pillow
  - Monospace font, dark background, colored tokens
  - One texture per wall segment
- Apply textures as materials
- Add basic lighting (ambient + point lights in rooms)
- Export as glTF/GLB

**Texture generation:**
- Resolution: 2048x2048 per wall segment
- Font: monospace, ~14pt equivalent
- Theme: VS Code Dark+ or similar
- Fit ~50-60 lines per wall at readable size

### 5. WebXR Viewer (`viewer/`)

**Tech stack:**
- Three.js + WebXR
- GLTFLoader for scene import
- Hand tracking + controllers

**Features (MVP):**
- Load and render glTF scene
- WebXR session (immersive-vr mode)
- Teleport locomotion (point and click to move)
- Room labels (directory/file name floating above)

**Hosting:**
- Static files, can run from `localhost` or GitHub Pages
- No backend required

## File Structure

```
codeviz/
├── cli.py                  # Entry point
├── requirements.txt        # Python deps (pygments, pillow, etc.)
├── parser/
│   ├── __init__.py
│   ├── walker.py           # Directory traversal
│   └── tokenizer.py        # Syntax tokenization
├── layout/
│   ├── __init__.py
│   └── grid.py             # Grid layout algorithm
├── generator/
│   ├── __init__.py
│   ├── blender_gen.py      # Blender script
│   └── textures.py         # Code-to-image rendering
├── viewer/
│   ├── index.html
│   ├── main.js             # Three.js + WebXR setup
│   └── style.css
└── docs/
    └── prd.md
```

## Dependencies

**Python:**
- `pygments` — Syntax highlighting
- `pillow` — Image generation for textures
- `pathspec` — .gitignore parsing
- Blender 4.x (external, must be installed)

**JavaScript (viewer):**
- `three` — 3D rendering
- No build step needed, use ES modules from CDN

## Success Criteria

MVP is complete when:
1. CLI can process a small codebase (~20 files) and output a .glb file
2. Scene opens in Blender and looks correct (rooms with code on walls)
3. WebXR viewer loads scene and works on Quest 3 browser
4. User can teleport between rooms and read code on walls

## Open Questions

1. **Text readability in VR** — May need experimentation with font size, texture resolution, wall distance
2. **Performance limits** — How many rooms/textures before Quest 3 browser struggles?
3. **Layout aesthetics** — Grid is functional but boring; may want organic clustering later

## Future Enhancements

- Dependency lines connecting related files (imports visualized as paths/tubes)
- Search: highlight rooms matching a query
- Voice + AI: "explain this function" with code context
- GitHub integration: browse and load repos directly
- Multiplayer: explore with teammates
- Metrics overlay: color rooms by complexity/churn/coverage
