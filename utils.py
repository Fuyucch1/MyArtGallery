from PIL import Image, ImageDraw, ImageFont, ImageChops
import math
import os, platform

# Get Fonts

def get_font(font_size):
    # Common font paths by platform
    font_paths = []

    system = platform.system()
    if system == "Windows":
        font_paths = [
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\verdana.ttf"
        ]
    elif system == "Darwin":  # macOS
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Verdana.ttf"
        ]
    else:  # Linux
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        ]

    # Try loading fonts in order of preference
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except IOError:
                continue

    # Fallback
    return ImageFont.load_default()

# Draw outline text on image
def draw_outline_text_hollow(base_img, position, text, font, outline_color, thickness=2):
    # Create a temporary image for drawing the outline
    txt = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt)

    x, y = position

    # Draw text multiple times for the outline
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

    # Draw the center text in transparent to "erase" it
    erase = Image.new('L', base_img.size, 0)
    erase_draw = ImageDraw.Draw(erase)
    erase_draw.text(position, text, font=font, fill=255)
    txt.putalpha(ImageChops.subtract(txt.getchannel('A'), erase))

    # Composite the outline onto the base image
    base_img.alpha_composite(txt)

# Create miniature version of image in webp format
def create_miniature(image_path, output_dir=None, max_size=300):
    try:
        # Open the original image
        img = Image.open(image_path)

        # Calculate new dimensions while maintaining aspect ratio
        width, height = img.size
        if width > height:
            new_width = min(width, max_size)
            new_height = int(height * (new_width / width))
        else:
            new_height = min(height, max_size)
            new_width = int(width * (new_height / height))

        # Resize the image
        img = img.resize((new_width, new_height), Image.LANCZOS)

        # Determine output path
        if output_dir is None:
            output_dir = os.path.dirname(image_path)

        # Get filename without extension
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)

        # Create miniature filename with _miniature suffix and .webp extension
        miniature_filename = f"{name}_miniature.webp"
        output_path = os.path.join(output_dir, miniature_filename)

        # Save as webp with good quality
        img.save(output_path, 'WEBP', quality=80)

        return miniature_filename
    except Exception as e:
        print(f"Error creating miniature: {e}")
        return None

# Add watermark to image
def add_watermark(image_path, output_path, watermark_text=None):
    try:
        img = Image.open(image_path)
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        base_font_size = 36
        base_image_width = 1000
        font_size = max(24, min(72, int(img.width * base_font_size / base_image_width)))
        font = get_font(font_size)

        if not watermark_text:
            watermark_text = "DO NOT USE FOR AI TRAINING"

        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        spacing_x = text_width * 3
        spacing_y = text_height * 2.5

        num_x = math.ceil(img.width / spacing_x) + 2
        num_y = math.ceil(img.height / spacing_y) + 6

        txt_img = Image.new('RGBA', (text_width * 2, text_height * 2), (0, 0, 0, 0))

        draw_outline_text_hollow(
            txt_img,
            (text_width // 2, text_height // 2),
            watermark_text,
            font,
            outline_color=(128, 128, 128, 128),
            thickness=2
        )

        rotated_txt_pos = txt_img.rotate(30, expand=1)
        rotated_txt_neg = txt_img.rotate(-30, expand=1)

        for i in range(num_y):
            for j in range(num_x):
                base_x = j * spacing_x - text_width
                y = i * spacing_y - (spacing_y * 3)

                x = int(base_x)
                overlay.paste(rotated_txt_pos, (x, int(y)), rotated_txt_pos)

                x = int(base_x + spacing_x // 3)
                overlay.paste(rotated_txt_neg, (x, int(y)), rotated_txt_neg)

                x = int(base_x + 2 * (spacing_x // 3))
                overlay.paste(rotated_txt_pos, (x, int(y)), rotated_txt_pos)

        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        watermarked = Image.alpha_composite(img, overlay)

        if watermarked.mode == 'RGBA':
            watermarked = watermarked.convert('RGB')

        watermarked.save(output_path)
        return True
    except Exception as e:
        print(f"Error adding watermark: {e}")
        return False