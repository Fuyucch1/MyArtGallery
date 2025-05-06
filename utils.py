from PIL import Image, ImageDraw, ImageFont
import math

# Add watermark to image
def add_watermark(image_path, output_path, watermark_text=None):
    try:
        # Open the original image
        img = Image.open(image_path)

        # Create a transparent overlay for the watermarks
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Try to load a font, use default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 36)
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
