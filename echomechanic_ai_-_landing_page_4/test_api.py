
import google.generativeai as genai
import os

# Key from main.py
GOOGLE_API_KEY = "AIzaSyBmPEa3XNAfuYErllpGYso1wG5vDWZOHgI"

print(f"Testing API Key: {GOOGLE_API_KEY[:5]}...{GOOGLE_API_KEY[-4:]}")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            
    print("\nAttempting generation with 'models/gemini-flash-latest'...")
    model = genai.GenerativeModel('models/gemini-flash-latest')
    response = model.generate_content("Hello, this is a test.")
    print(f"Success! Response: {response.text}")
    
except Exception as e:
    print(f"\nCRITICAL FAILURE: {e}")
