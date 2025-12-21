def get_contrast_color(hex_color: str) -> str:
    if not hex_color:
        return "#000000"

    if hex_color.startswith('#'):
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