import os
import sys
from PIL import Image, ImageDraw, ImageOps

# Ensure Pillow is installed
try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageOps

def process_logo():
    input_path = "Logotipo.jpg"
    # Update output path to be within the project structure
    output_dir = "echomechanic_ai_-_landing_page_4/assets/images"
    output_filename = "neon-circle-logo.png"
    output_path = os.path.join(output_dir, output_filename)

    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        img = Image.open(input_path).convert("RGBA")
        
        # Determine the shortest dimension to create a square crop (perfect circle fits in square)
        width, height = img.size
        size = min(width, height)
        
        # Center crop to a square
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        
        img = img.crop((left, top, right, bottom))
        
        # Create a circular mask (L mode - 8-bit pixels, black and white)
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        # Apply the mask to the alpha channel of the image
        result = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
        result.putalpha(mask)
        
        # Resize if necessary (optional, e.g., to 500x500 for optimization, but prompt said keep proportions)
        # keeping original high res is safer for quality, CSS will handle display size
        
        result.save(output_path, "PNG")
        print(f"Success: Processed logo saved to {output_path}")
        
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    process_logo()
