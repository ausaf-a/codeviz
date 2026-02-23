"""Generate syntax-highlighted code textures for 3D walls."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from parser.tokenizer import tokenize_to_lines


# VS Code Dark+ inspired color scheme
THEME = {
    "background": (30, 30, 30),        # #1e1e1e
    "text": (212, 212, 212),           # #d4d4d4
    "keyword": (86, 156, 214),         # #569cd6
    "keyword_type": (78, 201, 176),    # #4ec9b0
    "function": (220, 220, 170),       # #dcdcaa
    "class": (78, 201, 176),           # #4ec9b0
    "decorator": (220, 220, 170),      # #dcdcaa
    "builtin": (78, 201, 176),         # #4ec9b0
    "string": (206, 145, 120),         # #ce9178
    "string_escape": (215, 186, 125),  # #d7ba7d
    "string_interpol": (86, 156, 214), # #569cd6
    "regex": (215, 186, 125),          # #d7ba7d
    "number": (181, 206, 168),         # #b5cea8
    "operator": (212, 212, 212),       # #d4d4d4
    "punctuation": (212, 212, 212),    # #d4d4d4
    "comment": (106, 153, 85),         # #6a9955
    "preprocessor": (155, 155, 155),   # #9b9b9b
    "namespace": (78, 201, 176),       # #4ec9b0
    "variable": (156, 220, 254),       # #9cdcfe
    "attribute": (156, 220, 254),      # #9cdcfe
    "tag": (86, 156, 214),             # #569cd6
    "literal": (181, 206, 168),        # #b5cea8
    "whitespace": (30, 30, 30),        # same as background
}

# Line number gutter color
LINE_NUMBER_COLOR = (133, 133, 133)  # #858585


def get_monospace_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a monospace font, falling back to default if needed."""
    # Try common monospace fonts
    font_names = [
        "JetBrainsMono-Regular.ttf",
        "FiraCode-Regular.ttf",
        "SourceCodePro-Regular.ttf",
        "Menlo.ttc",
        "Monaco.ttf",
        "Consolas.ttf",
        "DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]

    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size)
        except (IOError, OSError):
            continue

    # Fallback to default
    return ImageFont.load_default()


def render_code_to_image(
    content: str,
    filename: str,
    width: int = 2048,
    height: int = 2048,
    font_size: int = 24,
    padding: int = 40,
    line_number_width: int = 60,
    show_line_numbers: bool = True,
    show_filename: bool = True,
) -> Image.Image:
    """
    Render syntax-highlighted code to an image.

    Args:
        content: Source code content
        filename: Filename for syntax detection
        width: Image width in pixels
        height: Image height in pixels
        font_size: Font size in points
        padding: Padding around content in pixels
        line_number_width: Width reserved for line numbers
        show_line_numbers: Whether to show line numbers
        show_filename: Whether to show filename header

    Returns:
        PIL Image with rendered code
    """
    # Create image
    img = Image.new("RGB", (width, height), THEME["background"])
    draw = ImageDraw.Draw(img)

    # Load font
    font = get_monospace_font(font_size)
    header_font = get_monospace_font(int(font_size * 1.2))

    # Calculate dimensions
    try:
        char_width = font.getbbox("M")[2]
        line_height = int(font_size * 1.5)
    except AttributeError:
        # Older Pillow versions
        char_width = font_size * 0.6
        line_height = int(font_size * 1.5)

    # Starting positions
    x_start = padding + (line_number_width if show_line_numbers else 0)
    y_start = padding

    # Draw filename header
    if show_filename:
        draw.text(
            (padding, y_start),
            filename,
            font=header_font,
            fill=THEME["text"],
        )
        y_start += int(line_height * 1.5)
        # Draw separator line
        draw.line(
            [(padding, y_start), (width - padding, y_start)],
            fill=(60, 60, 60),
            width=2,
        )
        y_start += int(line_height * 0.5)

    # Tokenize content
    lines = tokenize_to_lines(content, filename)

    # Calculate how many lines fit
    available_height = height - y_start - padding
    max_lines = available_height // line_height

    # Render lines
    y = y_start
    for line_num, line_tokens in enumerate(lines[:max_lines], start=1):
        # Draw line number
        if show_line_numbers:
            line_num_str = str(line_num).rjust(4)
            draw.text(
                (padding, y),
                line_num_str,
                font=font,
                fill=LINE_NUMBER_COLOR,
            )

        # Draw tokens
        x = x_start
        for token in line_tokens:
            value = token["value"]
            category = token["category"]
            color = THEME.get(category, THEME["text"])

            # Handle tabs
            value = value.replace("\t", "    ")

            draw.text((x, y), value, font=font, fill=color)

            # Advance x position
            try:
                text_width = font.getbbox(value)[2]
            except AttributeError:
                text_width = len(value) * char_width
            x += text_width

        y += line_height

    # Add "more lines" indicator if truncated
    if len(lines) > max_lines:
        remaining = len(lines) - max_lines
        indicator = f"... {remaining} more lines"
        draw.text(
            (x_start, y),
            indicator,
            font=font,
            fill=LINE_NUMBER_COLOR,
        )

    return img


def generate_wall_textures(
    content: str,
    filename: str,
    num_walls: int = 3,
    texture_size: int = 2048,
    font_size: int = 24,
) -> list[Image.Image]:
    """
    Generate multiple wall textures for a room, splitting content across walls.

    Args:
        content: Source code content
        filename: Filename for syntax detection
        num_walls: Number of walls to generate textures for
        texture_size: Size of each texture (square)
        font_size: Font size in points

    Returns:
        List of PIL Images, one per wall
    """
    lines = content.split("\n")
    total_lines = len(lines)

    # Estimate lines per wall based on texture size and font
    line_height = int(font_size * 1.5)
    header_space = int(line_height * 2.5)  # filename + separator
    available_height = texture_size - 80 - header_space  # padding
    lines_per_wall = available_height // line_height

    textures = []

    for wall_idx in range(num_walls):
        start_line = wall_idx * lines_per_wall
        end_line = min(start_line + lines_per_wall, total_lines)

        if start_line >= total_lines:
            # Empty wall
            wall_content = ""
            wall_filename = f"{filename} (empty)"
        else:
            wall_content = "\n".join(lines[start_line:end_line])
            if wall_idx > 0:
                wall_filename = f"{filename} (continued, lines {start_line + 1}-{end_line})"
            else:
                wall_filename = filename

        texture = render_code_to_image(
            wall_content,
            wall_filename,
            width=texture_size,
            height=texture_size,
            font_size=font_size,
        )
        textures.append(texture)

    return textures


def save_texture(image: Image.Image, output_path: str) -> None:
    """Save a texture image to disk."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG", optimize=True)


if __name__ == "__main__":
    # Test the texture generator
    test_code = '''def hello_world():
    """A simple greeting function."""
    message = "Hello, World!"
    print(message)
    return 42

class Calculator:
    def __init__(self):
        self.value = 0

    def add(self, x: int) -> int:
        # Add x to the current value
        self.value += x
        return self.value

if __name__ == "__main__":
    hello_world()
    calc = Calculator()
    calc.add(10)
'''

    img = render_code_to_image(test_code, "test.py")
    img.save("test_texture.png")
    print("Saved test_texture.png")
