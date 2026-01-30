import math
from PIL import Image
from collections import Counter

def get_contrast_color(hex_color: str) -> str:
    if not hex_color:
        return "#000000"
    if hex_color.startswith("#"):
        hex_color = hex_color[1:]
    if len(hex_color) != 6:
        return "#000000"
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        return "#000000"
    luminosity = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminosity > 128 else "#ffffff"

def hex_to_rgb(hex_col):
    hex_col = hex_col.lstrip('#')
    if len(hex_col) != 6: return (255, 255, 255)
    return tuple(int(hex_col[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def color_distance(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))

def extract_dominant_color(image_path, default="#ffffff"):
    try:
        img = Image.open(image_path)
        img = img.convert("RGBA")
        img = img.resize((50, 50)) 
        
        valid_pixels = []
        for r, g, b, a in img.getdata():
            if a < 128: continue
            if r > 250 and g > 250 and b > 250: continue
            if r < 15 and g < 15 and b < 15: continue
            valid_pixels.append((r, g, b))

        if not valid_pixels:
            return default

        most_common = Counter(valid_pixels).most_common(1)[0][0]
        return rgb_to_hex(most_common)
    except Exception as e:
        print(f"Fehler bei Farbanalyse: {e}")
        return default

def get_smart_color_for_source(image_path, existing_colors, threshold=40):
    """
    Analysiert das Bild und gibt eine Farbe zurück.
    Wenn die Farbe einer existierenden Farbe im Projekt sehr ähnlich ist (threshold),
    wird die existierende Farbe verwendet (verhindert 10x Gelb).
    """
    new_hex = extract_dominant_color(image_path)
    new_rgb = hex_to_rgb(new_hex)
    
    best_match = None
    min_dist = float('inf')
    
    for ex_hex in existing_colors:
        ex_rgb = hex_to_rgb(ex_hex)
        dist = color_distance(new_rgb, ex_rgb)
        if dist < min_dist:
            min_dist = dist
            best_match = ex_hex
            
    if best_match and min_dist < threshold:
        return best_match
    
    return new_hex