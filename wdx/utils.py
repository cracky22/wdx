import math
from PIL import Image
from collections import Counter

from wdx_logger import get_logger

logger = get_logger(__name__)


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


def hex_to_rgb(hex_col: str) -> tuple:
    hex_col = hex_col.lstrip("#")
    if len(hex_col) != 6:
        return (255, 255, 255)
    return tuple(int(hex_col[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def color_distance(c1: tuple, c2: tuple) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def extract_dominant_color(image_path: str, default: str = "#ffffff") -> str:
    try:
        img = Image.open(image_path)
        img = img.convert("RGBA")
        img = img.resize((50, 50))

        valid_pixels = []
        for r, g, b, a in img.getdata():
            if a < 128:
                continue
            if r > 250 and g > 250 and b > 250:
                continue
            if r < 15 and g < 15 and b < 15:
                continue
            valid_pixels.append((r, g, b))

        if not valid_pixels:
            logger.debug("Keine verwertbaren Pixel in %s — Standardfarbe verwendet", image_path)
            return default

        most_common = Counter(valid_pixels).most_common(1)[0][0]
        result = rgb_to_hex(most_common)
        logger.debug("Dominante Farbe aus %s: %s", image_path, result)
        return result

    except FileNotFoundError:
        logger.warning("Bilddatei nicht gefunden: %s", image_path)
        return default
    except OSError as exc:
        logger.warning("Bilddatei nicht lesbar (%s): %s", image_path, exc)
        return default
    except Exception as exc:
        logger.error("Unerwarteter Fehler bei Farbanalyse (%s): %s", image_path, exc)
        return default


def get_smart_color_for_source(
    image_path: str, existing_colors: set, threshold: int = 40
) -> str:
    new_hex = extract_dominant_color(image_path)
    new_rgb = hex_to_rgb(new_hex)

    best_match = None
    min_dist = float("inf")

    for ex_hex in existing_colors:
        try:
            ex_rgb = hex_to_rgb(ex_hex)
            dist = color_distance(new_rgb, ex_rgb)
            if dist < min_dist:
                min_dist = dist
                best_match = ex_hex
        except Exception as exc:
            logger.debug("Farbvergleich fehlgeschlagen für '%s': %s", ex_hex, exc)

    if best_match and min_dist < threshold:
        logger.debug(
            "Smart-Color: bestehende Farbe wiederverwendet %s (Distanz %.1f)",
            best_match, min_dist,
        )
        return best_match

    logger.debug("Smart-Color: neue Farbe %s", new_hex)
    return new_hex