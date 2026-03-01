# CodeViz - Agent Context

## Project Overview
A CLI tool that generates 3D "Code Park" style visualizations of codebases, viewable in VR on Quest 3 via WebXR.

## Current State (Working)
- CLI generates 3D scenes from local codebases
- Blender Python script creates rooms with syntax-highlighted code on walls
- WebXR viewer works on Quest 3 via cloudflared tunnel
- VR locomotion: left stick = walk/strafe, right stick X = turn, right stick Y = fly up/down

## Tech Stack
- **Python**: CLI, parsing, texture generation (Pygments, Pillow)
- **Blender 5.0**: Headless 3D scene generation via Python API
- **Three.js**: WebXR viewer with GLTFLoader
- **Hosting**: cloudflared tunnel for HTTPS (required for WebXR on Quest)

## Key Commands
```bash
# Generate scene
python cli.py generate --path /path/to/codebase --output scene.glb --blender /Applications/Blender.app/Contents/MacOS/Blender

# Serve with HTTPS (use cloudflared for Quest)
npx serve /Users/ausaf/dev/codeviz/viewer -l 8080
npx cloudflared tunnel --url http://localhost:8080
```

## Pipeline
```
codebase → parser/ (walk + tokenize) → layout/ (positioning) → generator/textures.py (code→PNG)
         → generator/blender_gen.py (rooms + walls + textures) → scene.glb
         → viewer/ (Three.js WebXR) → Quest 3 browser
```

## Known Issues / TODO

### Layout Problem
Current grid layout is too linear - directories chain along X-axis making it hard to see overview.
**Planned fix**: Radial layout where directories are pie slices around center, spawn above for bird's-eye view.

### Controller Bug
Virtual controllers stay at origin instead of following player.
**Fix**: Add controllers to `playerRig` instead of `scene` in `setupControllers()`.

### Planned Features
1. **Minimap** (left grip): Show top-down view, point-and-click teleport
2. **Imports panel** (right grip): Show file's imports, navigate to them
3. **Radial layout**: Better spatial arrangement for overview

## File Structure
```
codeviz/
├── cli.py                    # Entry point, orchestrates pipeline
├── parser/
│   ├── walker.py             # Directory traversal, gitignore
│   └── tokenizer.py          # Pygments syntax tokenization
├── layout/
│   └── grid.py               # Current layout (needs radial.py)
├── generator/
│   ├── textures.py           # Code → PNG with syntax highlighting
│   └── blender_gen.py        # Blender script for 3D generation
├── viewer/
│   ├── index.html            # WebXR page
│   └── main.js               # Three.js + VR controls
└── docs/
    └── prd.md                # Original PRD
```

## Code Patterns

### Layout Data Flow
```python
# cli.py
files = list(walk_codebase(path))           # parser/walker.py
layouts = compute_layout(files, config)      # layout/grid.py
# layouts is list of RoomLayout(position, dimensions, rotation, ...)
```

### Blender Invocation
```python
# cli.py calls Blender headless:
blender --background --python generator/blender_gen.py -- --input scene.json --output scene.glb --textures ./textures
```

### VR Player Movement
```javascript
// viewer/main.js
playerRig = new THREE.Group();  // Camera parent for VR
scene.add(playerRig);
// Move/rotate playerRig, not camera directly
playerRig.position.addScaledVector(direction, speed);
playerRig.rotation.y -= turnAmount;
```

## Blender 5.0 Notes
- `bpy.ops.export_scene.gltf()` params changed - don't use `export_colors`
- Object collection linking changed - use helper to check before unlink:
```python
def move_to_collection(obj, collection):
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    if obj.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(obj)
```

## Texture Generation
- VS Code Dark+ color scheme
- 2048x2048 PNG per wall
- Pygments tokenization → PIL rendering
- 3 walls per room (left, back, right - front is open entrance)
