"""
Blender script to generate Code Park style 3D rooms.

Run with: blender --background --python blender_gen.py -- --input scene_data.json --output scene.glb
"""

import sys
import json
import argparse
import math
from pathlib import Path

# Blender imports (only available when running inside Blender)
try:
    import bpy
    import bmesh
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False
    print("Warning: Blender modules not available. Run this script inside Blender.")


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Clear orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


def create_material_with_texture(name: str, texture_path: str) -> bpy.types.Material:
    """Create a material with an image texture."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    nodes.clear()

    # Create nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)

    tex_image = nodes.new('ShaderNodeTexImage')
    tex_image.location = (-300, 0)

    # Load image
    if Path(texture_path).exists():
        tex_image.image = bpy.data.images.load(texture_path)
    else:
        print(f"Warning: Texture not found: {texture_path}")

    # Link nodes
    links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # Make it emissive so it's visible without lights
    bsdf.inputs['Emission Strength'].default_value = 0.3
    links.new(tex_image.outputs['Color'], bsdf.inputs['Emission Color'])

    return mat


def create_floor_material() -> bpy.types.Material:
    """Create a simple floor material."""
    mat = bpy.data.materials.new(name="Floor")
    mat.use_nodes = True

    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.15, 0.15, 0.18, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.8

    return mat


def create_ceiling_material() -> bpy.types.Material:
    """Create a ceiling material with slight emission."""
    mat = bpy.data.materials.new(name="Ceiling")
    mat.use_nodes = True

    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.1, 0.1, 0.12, 1.0)
    bsdf.inputs['Emission Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs['Emission Strength'].default_value = 0.1

    return mat


def move_to_collection(obj, collection):
    """Move an object to a collection, unlinking from scene collection if needed."""
    # Link to target collection
    if obj.name not in collection.objects:
        collection.objects.link(obj)

    # Unlink from scene collection if present
    scene_collection = bpy.context.scene.collection
    if obj.name in scene_collection.objects:
        scene_collection.objects.unlink(obj)


def create_room(
    name: str,
    position: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    wall_textures: list[str],
    floor_mat: bpy.types.Material,
    ceiling_mat: bpy.types.Material,
) -> bpy.types.Object:
    """
    Create a room with textured walls.

    Args:
        name: Room name
        position: (x, y, z) position
        dimensions: (width, depth, height)
        wall_textures: List of texture paths for walls [left, back, right]
        floor_mat: Material for floor
        ceiling_mat: Material for ceiling
    """
    width, depth, height = dimensions
    x, y, z = position

    # Create room collection
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)

    # Create floor
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x + width/2, z + depth/2, y))
    floor = bpy.context.active_object
    floor.name = f"{name}_floor"
    floor.scale = (width, depth, 1)
    floor.data.materials.append(floor_mat)
    move_to_collection(floor, collection)

    # Create ceiling
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x + width/2, z + depth/2, y + height))
    ceiling = bpy.context.active_object
    ceiling.name = f"{name}_ceiling"
    ceiling.scale = (width, depth, 1)
    ceiling.rotation_euler = (math.pi, 0, 0)  # Flip to face down
    ceiling.data.materials.append(ceiling_mat)
    move_to_collection(ceiling, collection)

    # Wall positions and rotations: left, back, right (no front wall - entrance)
    walls = [
        # Left wall
        {
            "location": (x, z + depth/2, y + height/2),
            "rotation": (math.pi/2, 0, math.pi/2),
            "scale": (depth, height, 1),
            "texture_idx": 0,
        },
        # Back wall
        {
            "location": (x + width/2, z + depth, y + height/2),
            "rotation": (math.pi/2, 0, 0),
            "scale": (width, height, 1),
            "texture_idx": 1,
        },
        # Right wall
        {
            "location": (x + width, z + depth/2, y + height/2),
            "rotation": (math.pi/2, 0, -math.pi/2),
            "scale": (depth, height, 1),
            "texture_idx": 2,
        },
    ]

    for i, wall_info in enumerate(walls):
        bpy.ops.mesh.primitive_plane_add(size=1, location=wall_info["location"])
        wall = bpy.context.active_object
        wall.name = f"{name}_wall_{i}"
        wall.rotation_euler = wall_info["rotation"]
        wall.scale = wall_info["scale"]

        # Apply texture
        tex_idx = wall_info["texture_idx"]
        if tex_idx < len(wall_textures) and wall_textures[tex_idx]:
            mat = create_material_with_texture(
                f"{name}_wall_{i}_mat",
                wall_textures[tex_idx]
            )
            wall.data.materials.append(mat)

            # UV unwrap for proper texture mapping
            bpy.context.view_layer.objects.active = wall
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.reset()
            bpy.ops.object.mode_set(mode='OBJECT')

        move_to_collection(wall, collection)

    return collection


def create_label(
    text: str,
    position: tuple[float, float, float],
    size: float = 0.3,
) -> bpy.types.Object:
    """Create a floating text label above a room."""
    bpy.ops.object.text_add(location=position)
    text_obj = bpy.context.active_object
    text_obj.data.body = text
    text_obj.data.size = size
    text_obj.data.align_x = 'CENTER'
    text_obj.rotation_euler = (math.pi/2, 0, 0)  # Face forward

    # Convert to mesh for glTF export
    bpy.ops.object.convert(target='MESH')

    # Create simple material
    mat = bpy.data.materials.new(name=f"label_{text[:20]}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.9, 0.9, 0.9, 1.0)
    bsdf.inputs['Emission Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs['Emission Strength'].default_value = 0.5
    text_obj.data.materials.append(mat)

    return text_obj


def create_ground_plane(bounds_min: tuple, bounds_max: tuple) -> bpy.types.Object:
    """Create a large ground plane under all rooms."""
    center_x = (bounds_min[0] + bounds_max[0]) / 2
    center_z = (bounds_min[2] + bounds_max[2]) / 2
    width = bounds_max[0] - bounds_min[0] + 20
    depth = bounds_max[2] - bounds_min[2] + 20

    bpy.ops.mesh.primitive_plane_add(
        size=1,
        location=(center_x, center_z, -0.01)  # Slightly below room floors
    )
    ground = bpy.context.active_object
    ground.name = "ground"
    ground.scale = (width, depth, 1)

    # Dark ground material
    mat = bpy.data.materials.new(name="Ground")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.08, 0.08, 0.1, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.9
    ground.data.materials.append(mat)

    return ground


def setup_lighting():
    """Add ambient and directional lighting."""
    # Sun lamp for general illumination
    bpy.ops.object.light_add(type='SUN', location=(10, 10, 20))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 0.5

    # Set world background
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs['Color'].default_value = (0.02, 0.02, 0.03, 1.0)


def generate_scene(scene_data: dict, texture_dir: str):
    """Generate the full 3D scene from scene data."""
    clear_scene()

    rooms = scene_data.get("rooms", [])
    if not rooms:
        print("No rooms in scene data")
        return

    # Create shared materials
    floor_mat = create_floor_material()
    ceiling_mat = create_ceiling_material()

    # Track bounds
    all_positions = []

    # Create each room
    for room_data in rooms:
        name = room_data["filename"]
        position = tuple(room_data["position"])
        dimensions = tuple(room_data["dimensions"])

        # Build texture paths
        wall_textures = []
        for i in range(3):
            tex_name = f"{room_data['relative_path'].replace('/', '_').replace('.', '_')}_wall_{i}.png"
            tex_path = str(Path(texture_dir) / tex_name)
            wall_textures.append(tex_path)

        create_room(
            name=name,
            position=position,
            dimensions=dimensions,
            wall_textures=wall_textures,
            floor_mat=floor_mat,
            ceiling_mat=ceiling_mat,
        )

        # Add label above room
        label_pos = (
            position[0] + dimensions[0]/2,
            position[2],  # z in blender is y in our layout
            position[1] + dimensions[2] + 0.5
        )
        create_label(name, label_pos)

        all_positions.append(position)
        all_positions.append((
            position[0] + dimensions[0],
            position[1] + dimensions[2],
            position[2] + dimensions[1]
        ))

    # Calculate bounds and create ground
    if all_positions:
        bounds_min = (
            min(p[0] for p in all_positions),
            min(p[1] for p in all_positions),
            min(p[2] for p in all_positions),
        )
        bounds_max = (
            max(p[0] for p in all_positions),
            max(p[1] for p in all_positions),
            max(p[2] for p in all_positions),
        )
        create_ground_plane(bounds_min, bounds_max)

    setup_lighting()


def export_gltf(output_path: str):
    """Export scene to glTF/GLB format."""
    # Blender 5.0 changed some export parameters
    try:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            export_texcoords=True,
            export_normals=True,
            export_materials='EXPORT',
        )
    except TypeError:
        # Fallback for different Blender versions
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
        )
    print(f"Exported scene to: {output_path}")


def main():
    # Parse arguments after "--"
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Generate Code Park 3D scene")
    parser.add_argument("--input", required=True, help="Input JSON scene data file")
    parser.add_argument("--output", required=True, help="Output GLB file path")
    parser.add_argument("--textures", required=True, help="Directory containing wall textures")

    args = parser.parse_args(argv)

    # Load scene data
    with open(args.input, "r") as f:
        scene_data = json.load(f)

    # Generate scene
    generate_scene(scene_data, args.textures)

    # Export
    export_gltf(args.output)


if __name__ == "__main__":
    if BLENDER_AVAILABLE:
        main()
    else:
        print("This script must be run inside Blender:")
        print("  blender --background --python blender_gen.py -- --input scene.json --output scene.glb --textures ./textures")
