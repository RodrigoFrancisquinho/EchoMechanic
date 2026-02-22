import os
import base64
import re

base_dir = "."
image_path = os.path.join(base_dir, "assets/images/neon-circle-logo.png")
target_file = os.path.join(base_dir, "forgot_password.html")

def get_base64_image(path):
    if not os.path.exists(path):
        print(f"Error: Image not found at {path}")
        return None
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"

def fix_forgot_password():
    if not os.path.exists(target_file):
        print(f"Error: {target_file} not found.")
        return

    base64_src = get_base64_image(image_path)
    if not base64_src:
        return

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match the lock icon div
    # It spans multiple lines, so we match carefully
    # The div starts with <div class="inline-flex p-3...
    # and ends with </div>
    # Inside is a span with lock_reset
    
    # Simple strategy: Find the specific text of the div and replace it.
    
    target_block_regex = r'<div\s+class="inline-flex p-3[^"]*text-primary mb-4[^"]*">\s*<span class="material-symbols-outlined text-3xl">lock_reset</span>\s*</div>'
    
    # New image tag with inline styles as requested
    new_img_tag = (
        f'<img src="{base64_src}" '
        'style="height: 120px !important; width: 120px !important; object-fit: contain !important; '
        'border-radius: 50%; display: block; margin: 0 auto 2rem auto;" '
        'class="rounded-full object-cover aspect-square">'
    )

    if re.search(target_block_regex, content):
        new_content = re.sub(target_block_regex, new_img_tag, content)
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Successfully replaced lock icon with logo in {target_file}")
    else:
        # Check if maybe it was already replaced or pattern didn't match
        if "data:image/png;base64" in content and "height: 120px !important" in content:
             print(f"Logo seems to be already present in {target_file}")
        else:
             print(f"Could not find the lock icon block to replace in {target_file}. Please check the file structure.")

if __name__ == "__main__":
    fix_forgot_password()
