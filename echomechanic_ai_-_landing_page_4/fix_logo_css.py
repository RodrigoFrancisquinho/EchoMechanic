import os
import re

# Define styles
HEADER_STYLE = 'height: 50px !important; width: 50px !important; object-fit: contain !important; border-radius: 50%;'
AUTH_STYLE = 'height: 120px !important; width: 120px !important; object-fit: contain !important; border-radius: 50%; display: block; margin: 0 auto;'

# Define file groups
AUTH_FILES = [
    'index.html',
    'reset_password.html',
    'forgot_password.html'
]

HEADER_FILES = [
    'landing.html',
    'dashboard.html',
    'adicionar_maquina.html',
    'chat.html',
    'definicoes.html',
    'historico.html',
    'nova_analise.html'
]

BASE_DIR = r'c:\Users\rfran\Downloads\stitch_echomechanic_ai_landing_page\echomechanic_ai_-_landing_page_4'

def fix_logo_in_file(filename, style_string):
    file_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(file_path):
        print(f"File not found: {filename}")
        return

    print(f"Processing {filename}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find the logo img tag. 
    # Validating based on 'data:image/png;base64' presence
    # We look for <img ... src="data:image/png;base64..." ... >
    # We want to capture the FULL tag to replace it.
    
    # Pattern explanation:
    # <img\s+                          Match <img followed by whitespace
    # [^>]*?                           Match anything non-greedy (attributes before src)
    # src=["'](data:image/png;base64,[^"']+)["']  Match src="data:..." and capture content
    # [^>]*?                           Match anything non-greedy (attributes after src)
    # >                                Match closing >
    
    pattern = re.compile(r'(<img\s+[^>]*?src=["\'](data:image/png;base64,[^"\']+)["\'][^>]*?>)', re.IGNORECASE | re.DOTALL)
    
    matches = pattern.findall(content)
    
    if not matches:
        print(f"  No base64 logo found in {filename}")
        return

    # We expect usually one logo per file in these specific locations, but we'll replace all matches just in case
    # The replacement will reconstruct the tag using the captured base64 src
    
    def replacement(m):
        # m.group(1) is the full tag
        # m.group(2) is the base64 src
        src_content = m.group(2)
        new_tag = f'<img src="{src_content}" style="{style_string}" alt="EchoMechanic AI Logo" class="rounded-full">' 
        # Kept class="rounded-full" just for Tailwind utility consistency, but style !important overrides sizing.
        return new_tag

    new_content = pattern.sub(replacement, content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  Fixed logo in {filename}")
    else:
        print(f"  No changes made to {filename}")

def main():
    for f in AUTH_FILES:
        fix_logo_in_file(f, AUTH_STYLE)
    
    for f in HEADER_FILES:
        fix_logo_in_file(f, HEADER_STYLE)

if __name__ == "__main__":
    main()
