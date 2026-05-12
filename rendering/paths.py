import os

import matplotlib


matplotlib.use("agg")

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "font")
SIMHEI_FONT = os.path.join(FONT_DIR, "simhei.ttf")
WIND_BOLD_FONT = os.path.join(FONT_DIR, "wind Bold.ttf")
WIND_FONT = os.path.join(FONT_DIR, "wind.ttf")

IMG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "imgs")
EMPTY_IMG = os.path.join(IMG_DIR, "empty.png")
RAIN_IMG = os.path.join(IMG_DIR, "rain.png")
SNOW_IMG = os.path.join(IMG_DIR, "snow.png")
LIGHT_IMG = os.path.join(IMG_DIR, "light.png")
LOGO_IMG = os.path.join(IMG_DIR, "logo.png")
