import os
from typing import Optional

# Utilities for image processing. These functions are used by the dashboard to
# add watermarks and generate miniatures for faster browsing.
# They gracefully degrade if Pillow is not available.

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


def add_watermark(input_path: str, output_path: str, text: Optional[str]) -> bool:
    """
    Add a simple semi-transparent text watermark to the bottom-right of the image.
    If Pillow isn't available, this function copies the original image to output_path.

    Returns True on success, False otherwise.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not PIL_AVAILABLE:
            # Best-effort fallback: just copy the file
            with open(input_path, 'rb') as src, open(output_path, 'wb') as dst:
                dst.write(src.read())
            return True

        base = Image.open(input_path).convert('RGBA')
        txt_layer = Image.new('RGBA', base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        # Choose font size relative to image width
        W, H = base.size
        font_size = max(18, int(W * 0.03))

        try:
            # Try a common font; Pillow will fall back if not found
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        wm_text = text or "WATERMARK"
        text_bbox = draw.textbbox((0, 0), wm_text, font=font)
        tw = text_bbox[2] - text_bbox[0]
        th = text_bbox[3] - text_bbox[1]

        padding = max(10, int(W * 0.01))
        x = W - tw - padding
        y = H - th - padding

        # Draw shadow
        draw.text((x+1, y+1), wm_text, font=font, fill=(0, 0, 0, 128))
        # Draw main text
        draw.text((x, y), wm_text, font=font, fill=(255, 255, 255, 160))

        watermarked = Image.alpha_composite(base, txt_layer).convert('RGB')
        # Save as JPEG to ensure broad compatibility
        watermarked.save(output_path, format='JPEG', quality=90)
        return True
    except Exception as e:
        print(f"add_watermark error: {e}")
        return False

def resize_with_min_size(img: Image.Image, min_size: int) -> Image.Image:
    """
    Resize so that the smallest side becomes exactly min_size.
    Does not upscale: if smallest side >= min_size, returns original size.
    """
    w, h = img.size
    smallest = min(w, h)

    # no upscale allowed
    if smallest <= min_size:
        return img.copy()

    scale = min_size / smallest
    new_w = int(w * scale)
    new_h = int(h * scale)

    return img.resize((new_w, new_h), Image.LANCZOS)

def create_miniature(input_path: str, output_dir: str, max_size: int = 300) -> bool:
    """
    Create a smaller WebP miniature version of the image next to the original.
    The output file is named with the pattern: <original_name>_miniature.webp
    Returns True on success, False otherwise.
    """
    try:
        if not os.path.exists(input_path):
            return False

        dirname, filename = os.path.split(input_path)
        name, ext = os.path.splitext(filename)

        # Output beside the original, but allow overriding directory
        out_dir = output_dir if output_dir else dirname
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{name}_miniature.webp")

        if not PIL_AVAILABLE:
            # Fallback: just copy original as webp not possible; copy original bytes
            # This won't reduce size, but keeps references consistent
            with open(input_path, 'rb') as src, open(out_path, 'wb') as dst:
                dst.write(src.read())
            return True

        with Image.open(input_path) as img:
            img = img.convert('RGB')
            img = resize_with_min_size(img, max_size)
            img.save(out_path, format='WEBP', quality=80, method=6)

        return True
    except Exception as e:
        print(f"create_miniature error: {e}")
        return False
