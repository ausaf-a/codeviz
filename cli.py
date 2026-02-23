#!/usr/bin/env python3
"""
CodeViz CLI - Generate 3D Code Park visualizations of codebases.

Usage:
    python cli.py generate --path /path/to/codebase --output scene.glb
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import click

from parser import walk_codebase
from layout import compute_layout
from layout.grid import LayoutConfig, get_spawn_point
from generator.textures import generate_wall_textures, save_texture


@click.group()
def cli():
    """CodeViz - 3D codebase visualization tool."""
    pass


@cli.command()
@click.option("--path", required=True, type=click.Path(exists=True), help="Path to codebase directory")
@click.option("--output", default="scene.glb", help="Output GLB file path")
@click.option("--max-files", default=50, help="Maximum number of files to process")
@click.option("--max-lines", default=200, help="Maximum lines per file")
@click.option("--texture-size", default=2048, help="Texture resolution (square)")
@click.option("--font-size", default=24, help="Font size for code text")
@click.option("--blender", default="blender", help="Path to Blender executable")
@click.option("--keep-temp", is_flag=True, help="Keep temporary files (textures, JSON)")
def generate(path, output, max_files, max_lines, texture_size, font_size, blender, keep_temp):
    """Generate a 3D Code Park scene from a codebase."""

    output_path = Path(output).resolve()
    temp_dir = output_path.parent / ".codeviz_temp"
    texture_dir = temp_dir / "textures"
    scene_json = temp_dir / "scene_data.json"

    # Create temp directory
    temp_dir.mkdir(parents=True, exist_ok=True)
    texture_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Scanning codebase: {path}")

    # Step 1: Walk codebase and collect files
    files = list(walk_codebase(
        path,
        max_files=max_files,
        max_lines=max_lines,
    ))

    if not files:
        click.echo("No code files found!", err=True)
        sys.exit(1)

    click.echo(f"Found {len(files)} files")

    # Step 2: Compute layout
    click.echo("Computing layout...")
    layouts = compute_layout(files, LayoutConfig())

    # Step 3: Generate textures for each file
    click.echo("Generating textures...")
    with click.progressbar(files, label="Rendering code textures") as bar:
        for file_info in bar:
            textures = generate_wall_textures(
                content=file_info["content"],
                filename=file_info["filename"],
                num_walls=3,
                texture_size=texture_size,
                font_size=font_size,
            )

            # Save textures
            for i, tex in enumerate(textures):
                tex_name = f"{file_info['relative_path'].replace('/', '_').replace('.', '_')}_wall_{i}.png"
                save_texture(tex, str(texture_dir / tex_name))

    # Step 4: Create scene data JSON
    click.echo("Creating scene data...")
    scene_data = {
        "rooms": [],
        "spawn_point": list(get_spawn_point(layouts)),
    }

    for layout, file_info in zip(layouts, files):
        scene_data["rooms"].append({
            "filename": layout.filename,
            "relative_path": layout.relative_path,
            "directory": layout.directory,
            "position": list(layout.position),
            "dimensions": list(layout.dimensions),
            "rotation": layout.rotation,
            "loc": file_info["loc"],
        })

    with open(scene_json, "w") as f:
        json.dump(scene_data, f, indent=2)

    # Step 5: Run Blender to generate GLB
    click.echo("Running Blender to generate 3D scene...")

    blender_script = Path(__file__).parent / "generator" / "blender_gen.py"

    cmd = [
        blender,
        "--background",
        "--python", str(blender_script),
        "--",
        "--input", str(scene_json),
        "--output", str(output_path),
        "--textures", str(texture_dir),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            click.echo("Blender error:", err=True)
            click.echo(result.stderr, err=True)
            sys.exit(1)

    except FileNotFoundError:
        click.echo(f"Blender not found at: {blender}", err=True)
        click.echo("Install Blender or specify path with --blender", err=True)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        click.echo("Blender timed out", err=True)
        sys.exit(1)

    # Cleanup
    if not keep_temp:
        shutil.rmtree(temp_dir)
        click.echo("Cleaned up temporary files")

    click.echo(f"Done! Scene saved to: {output_path}")

    # Also save spawn point for viewer
    spawn_file = output_path.with_suffix(".spawn.json")
    with open(spawn_file, "w") as f:
        json.dump({"spawn_point": scene_data["spawn_point"]}, f)
    click.echo(f"Spawn point saved to: {spawn_file}")


@cli.command()
@click.option("--path", required=True, type=click.Path(exists=True), help="Path to codebase directory")
@click.option("--output", default="scene_data.json", help="Output JSON file path")
@click.option("--max-files", default=50, help="Maximum number of files to process")
@click.option("--max-lines", default=200, help="Maximum lines per file")
def preview(path, output, max_files, max_lines):
    """Generate scene data JSON without textures or Blender (for testing)."""

    click.echo(f"Scanning codebase: {path}")

    files = list(walk_codebase(
        path,
        max_files=max_files,
        max_lines=max_lines,
    ))

    if not files:
        click.echo("No code files found!", err=True)
        sys.exit(1)

    click.echo(f"Found {len(files)} files")

    layouts = compute_layout(files, LayoutConfig())

    scene_data = {
        "rooms": [],
        "spawn_point": list(get_spawn_point(layouts)),
    }

    for layout, file_info in zip(layouts, files):
        scene_data["rooms"].append({
            "filename": layout.filename,
            "relative_path": layout.relative_path,
            "directory": layout.directory,
            "position": list(layout.position),
            "dimensions": list(layout.dimensions),
            "rotation": layout.rotation,
            "loc": file_info["loc"],
        })

    with open(output, "w") as f:
        json.dump(scene_data, f, indent=2)

    click.echo(f"Scene data saved to: {output}")


@cli.command()
@click.option("--scene", required=True, type=click.Path(exists=True), help="GLB scene file")
@click.option("--port", default=8080, help="Server port")
@click.option("--https", is_flag=True, help="Use HTTPS (required for WebXR on Quest)")
def serve(scene, port, https):
    """Start a local server to view the scene in WebXR."""
    import http.server
    import socketserver
    import os
    import webbrowser
    import socket
    import ssl

    scene_path = Path(scene).resolve()
    viewer_dir = Path(__file__).parent / "viewer"

    if not viewer_dir.exists():
        click.echo("Viewer directory not found!", err=True)
        sys.exit(1)

    # Copy scene to viewer directory (or symlink)
    scene_dest = viewer_dir / "scene.glb"
    if scene_dest.exists():
        scene_dest.unlink()
    shutil.copy(scene_path, scene_dest)

    # Copy spawn point if exists
    spawn_src = scene_path.with_suffix(".spawn.json")
    if spawn_src.exists():
        shutil.copy(spawn_src, viewer_dir / "spawn.json")

    os.chdir(viewer_dir)

    # Get local IP for Quest access
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"

    local_ip = get_local_ip()

    handler = http.server.SimpleHTTPRequestHandler

    if https:
        # Generate self-signed certificate
        cert_dir = Path(__file__).parent / ".certs"
        cert_dir.mkdir(exist_ok=True)
        cert_file = cert_dir / "cert.pem"
        key_file = cert_dir / "key.pem"
        config_file = cert_dir / "openssl.cnf"

        # Always regenerate if IP changed
        regen = not cert_file.exists() or not key_file.exists()
        if cert_file.exists():
            # Check if cert was made for different IP
            result = subprocess.run(
                ["openssl", "x509", "-in", str(cert_file), "-text", "-noout"],
                capture_output=True, text=True
            )
            if local_ip not in result.stdout:
                regen = True

        if regen:
            click.echo("Generating self-signed certificate...")

            # Create OpenSSL config for proper SAN support
            config_content = f"""
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
CN = {local_ip}

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment

[alt_names]
DNS.1 = localhost
IP.1 = {local_ip}
IP.2 = 127.0.0.1
"""
            with open(config_file, "w") as f:
                f.write(config_content)

            try:
                subprocess.run([
                    "openssl", "req", "-x509",
                    "-newkey", "rsa:2048",
                    "-keyout", str(key_file),
                    "-out", str(cert_file),
                    "-days", "365",
                    "-nodes",
                    "-config", str(config_file)
                ], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                click.echo("Failed to generate SSL certificate.", err=True)
                click.echo("Make sure openssl is installed.", err=True)
                sys.exit(1)

        # Create HTTPS server with Quest-compatible settings
        server = socketserver.TCPServer(("", port), handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(cert_file), str(key_file))
        server.socket = context.wrap_socket(server.socket, server_side=True)

        protocol = "https"
        click.echo(f"\nServing at {protocol}://localhost:{port}")
        click.echo(f"For Quest 3: {protocol}://{local_ip}:{port}")
        click.echo("\nNOTE: You'll need to accept the self-signed certificate warning in Quest browser")
        click.echo("      (Click 'Advanced' then 'Proceed' or similar)")
        click.echo("Press Ctrl+C to stop\n")

        webbrowser.open(f"{protocol}://localhost:{port}")
        server.serve_forever()
    else:
        with socketserver.TCPServer(("", port), handler) as httpd:
            click.echo(f"\nServing at http://localhost:{port}")
            click.echo(f"For Quest 3: http://{local_ip}:{port}")
            click.echo("\nWARNING: WebXR requires HTTPS on non-localhost.")
            click.echo("Use --https flag for Quest VR support.")
            click.echo("Press Ctrl+C to stop\n")

            webbrowser.open(f"http://localhost:{port}")
            httpd.serve_forever()


if __name__ == "__main__":
    cli()
