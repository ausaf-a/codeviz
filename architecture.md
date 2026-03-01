# CodeViz Architecture

## What It Does
Turns a codebase into a 3D virtual world you can explore in VR. Each file becomes a "room" with syntax-highlighted code on the walls.

## Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Codebase   │ ──▶ │    Parser    │ ──▶ │   Blender    │ ──▶ │  VR Viewer   │
│   (local)    │     │  + Textures  │     │   (3D gen)   │     │  (WebXR)     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

## Components

### 1. Parser (`parser/`)
- Walks directory tree, respects .gitignore
- Tokenizes code with Pygments for syntax highlighting
- Outputs: file list with content, LOC, language

### 2. Layout (`layout/`)
- Calculates 3D positions for each file's room
- Groups files by directory
- Outputs: position (x,y,z), dimensions, rotation per room

### 3. Texture Generator (`generator/textures.py`)
- Renders syntax-highlighted code to PNG images
- VS Code Dark+ color scheme
- One texture per wall (3 walls per room)

### 4. Blender Generator (`generator/blender_gen.py`)
- Creates room geometry (floor, ceiling, 3 walls)
- Applies code textures to walls
- Exports as GLB (binary glTF)

### 5. WebXR Viewer (`viewer/`)
- Three.js loads the GLB
- WebXR for Quest 3 immersive mode
- Locomotion: walk, strafe, turn, fly

## Data Flow

```
cli.py generate --path ./mycode --output scene.glb

1. parser/walker.py    →  List of files with content
2. layout/grid.py      →  Room positions (x, y, z)
3. generator/textures  →  PNG files in temp dir
4. generator/blender   →  scene.glb (3D model)
5. viewer/             →  Load GLB, enter VR
```

## Key Files

| File | Purpose |
|------|---------|
| `cli.py` | Main entry point, orchestrates everything |
| `parser/walker.py` | Find and read code files |
| `parser/tokenizer.py` | Syntax highlighting tokens |
| `layout/grid.py` | Room positioning algorithm |
| `generator/textures.py` | Code → PNG images |
| `generator/blender_gen.py` | PNG + positions → 3D GLB |
| `viewer/main.js` | WebXR + Three.js viewer |

## VR Controls

- **Left stick**: Walk forward/back, strafe left/right
- **Right stick X**: Turn left/right
- **Right stick Y**: Fly up/down

## Running It

```bash
# Generate
python cli.py generate --path ./code --output scene.glb \
  --blender /Applications/Blender.app/Contents/MacOS/Blender

# Serve (need HTTPS for Quest VR)
npx serve viewer -l 8080
npx cloudflared tunnel --url http://localhost:8080

# Open the cloudflare URL on Quest 3 browser
```
