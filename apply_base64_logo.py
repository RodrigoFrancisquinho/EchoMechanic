import os
import base64
import re

# Configuration
base_dir = "echomechanic_ai_-_landing_page_4"
image_path = os.path.join(base_dir, "assets/images/neon-circle-logo.png")
files_to_update = [
    "landing.html",
    "index.html",
    "dashboard.html",
    "adicionar_maquina.html",
    "chat.html",
    "definicoes.html",
    "historico.html",
    "nova_analise.html",
    "reset_password.html",
    "forgot_password.html"
]

def get_base64_image(path):
    if not os.path.exists(path):
        print(f"Error: Image not found at {path}")
        return None
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"

def update_files():
    # 1. Get Base64 string
    base64_src = get_base64_image(image_path)
    if not base64_src:
        return

    # 2. Iterate and replace
    # Regex to match the img tag with the logo alt text or Base64 src
    # We look for img tags that likely contain our logo. 
    # Since we used specific alt text "EchoMechanic.AI" or context in previous steps, matching 'data:image/png;base64' is a strong signal if no other base64 images exist.
    # But safer to iterate line by line or find specific logo contexts.
    
    # Simple strategy: replace matching src attribute AND ensure classes
    # pattern: src="data:image/png;base64,..."
    
    for filename in files_to_update:
        file_path = os.path.join(base_dir, filename)
        if not os.path.exists(file_path):
            print(f"Skipping {filename} (not found)")
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # We will use re.sub to handle the replacement safely
            # We want to replace the src content inside the img tag
            
            # This regex captures the 'src' value for any base64 png
            # We assume the logo is the primary base64 png here.
            
            # Also need to inject classes: rounded-full object-cover aspect-square
            new_classes = "rounded-full object-cover aspect-square"
            
            # 1. Update SRC
            # Find any src="data:image/png;base64,..." and replace it with new base64
            # We use a lambda to replace just the group
            
            # Pattern for src
            src_pattern = r'src="data:image/png;base64,[^"]*"'
            replacement_src = f'src="{base64_src}"'
            
            if re.search(src_pattern, content):
                print(f"Updating Base64 in {filename}...")
                content = re.sub(src_pattern, replacement_src, content)
            else:
                # If not found, maybe it's the old path string? (Fallback from previous state if this wasn't fully applied or reverted)
                path_string = '/assets/images/neon-circle-logo.png'
                if path_string in content:
                    print(f"Updating Path -> Base64 in {filename}...")
                    content = content.replace(path_string, base64_src)
            
            # 2. Update Classes
            # We want to ensure the img tag containing this src also has the classes.
            # This is tricky with regex. 
            # Alternative: Find the tag specifically.
            
            # Let's verify if classes are present. If not, add them.
            # We'll look for the img tag with our base64 src
            
            img_tag_pattern = r'(<img[^>]*src="' + re.escape(base64_src) + r'"[^>]*>)'
            
            def add_classes_to_tag(match):
                tag = match.group(1)
                # Check if class attribute exists
                if 'class="' in tag:
                    # Append classes if not present
                    if 'rounded-full' not in tag:
                        tag = tag.replace('class="', f'class="{new_classes} ')
                else:
                    # Add class attribute
                    tag = tag.replace('<img', f('<img class="{new_classes}"'))
                return tag

            # Using regex to target the specific img tag is heavy. 
            # Simpler approach: Just search/replace the common class definitions we used?
            # We used 'size-10', 'size-8', 'w-10 h-10', 'size-12'.
            # We can replace 'class="size-10' with 'class="rounded-full object-cover aspect-square size-10' ?
            # But that might affect other elements.
            
            # Best approach: target the img with the base64 src we just injected.
            # Since we know the exact string of base64_src (it's long), we can find it.
            
            # But regex with very long string is slow/problematic.
            # Let's assume the user wants these classes on the logo.
            # We can search for the line containing the base64 src.
            
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if 'data:image/png;base64' in line:
                    # This line has the logo. Add classes if missing.
                    if 'rounded-full' not in line:
                        # Insert into class="..."
                         if 'class="' in line:
                             line = line.replace('class="', f'class="{new_classes} ')
                         else:
                             # Add class attribute
                             line = line.replace('<img', f'<img class="{new_classes}"')
                new_lines.append(line)
            
            final_content = '\n'.join(new_lines)
            
            if final_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                print(f"✓ CSS updated in {filename}")
            else:
                 print(f"  {filename} already up to date.")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    update_files()
