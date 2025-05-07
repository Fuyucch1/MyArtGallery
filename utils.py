from PIL import Image, ImageDraw, ImageFont
import math
import os

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
        # Open the original image
        img = Image.open(image_path)

        # Create a transparent overlay for the watermarks
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Calculate font size based on image dimensions
        # Use a base size of 36 for a 1000px wide image, and scale proportionally
        base_font_size = 36
        base_image_width = 1000

        # Calculate font size as a percentage of image width, with min and max limits
        font_size = max(24, min(72, int(img.width * base_font_size / base_image_width)))

        # Try to load a font with the calculated size, use default if not available
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        # Use provided watermark text or default
        if not watermark_text:
            watermark_text = "DO NOT USE FOR AI TRAINING"

        # Get text dimensions using textbbox (newer method) instead of textsize
        # textbbox returns (left, top, right, bottom)
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate spacing for the grid of watermarks - use smaller spacing for more consistent coverage
        # Scale spacing based on font size to maintain proper density of watermarks
        spacing_x = text_width * 3  # Increased to accommodate the new middle column
        spacing_y = text_height * 2.5  # Increased vertical spacing between watermarks

        # Calculate how many watermarks we need in each direction
        # Add extra watermarks to ensure full coverage
        num_x = math.ceil(img.width / spacing_x) + 2
        num_y = math.ceil(img.height / spacing_y) + 6  # Further increased to ensure full height coverage including top

        # Create rotated text images for better performance
        # Create temporary images to draw the rotated texts
        txt_img = Image.new('RGBA', (text_width * 2, text_height * 2), (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(txt_img)

        # Draw the text in the center of the temporary image
        # Use 128 for alpha to make it exactly half see-through (50% opacity)
        txt_draw.text((text_width // 2, text_height // 2), watermark_text, fill=(255, 255, 255, 128), font=font)

        # Create rotated text images at 30° and -30°
        rotated_txt_pos = txt_img.rotate(30, expand=1)
        rotated_txt_neg = txt_img.rotate(-30, expand=1)

        # Draw the watermark grid
        for i in range(num_y):
            for j in range(num_x):
                # Calculate position for a uniform grid pattern
                # Start from negative offset to ensure coverage of the edges
                base_x = j * spacing_x - text_width
                y = i * spacing_y - text_height

                # Create three columns of watermarks with alternating rotations
                # First column (30° rotation)
                x = int(base_x)
                overlay.paste(rotated_txt_pos, (x, int(y)), rotated_txt_pos)

                # Middle column (-30° rotation)
                x = int(base_x + spacing_x // 3)
                overlay.paste(rotated_txt_neg, (x, int(y)), rotated_txt_neg)

                # Third column (30° rotation)
                x = int(base_x + 2 * (spacing_x // 3))
                overlay.paste(rotated_txt_pos, (x, int(y)), rotated_txt_pos)

        # Convert the original image to RGBA if it's not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Composite the overlay onto the original image
        watermarked = Image.alpha_composite(img, overlay)

        # Convert back to RGB if needed and save
        if watermarked.mode == 'RGBA':
            watermarked = watermarked.convert('RGB')

        watermarked.save(output_path)
        return True
    except Exception as e:
        print(f"Error adding watermark: {e}")
        return False
