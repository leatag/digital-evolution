"""
Central configuration for the Digital Evolution simulation.
Tweak these values to change world balance, performance, and visuals.
"""

# ---- Display ----
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800
SIDEBAR_WIDTH = 300
WORLD_WIDTH = SCREEN_WIDTH - SIDEBAR_WIDTH
WORLD_HEIGHT = SCREEN_HEIGHT
TARGET_FPS = 60

# ---- Colors (neon theme) ----
BG_COLOR = (10, 12, 24)
GRID_COLOR = (20, 24, 40)
SIDEBAR_BG = (16, 18, 32, 220)
PANEL_BORDER = (60, 80, 140)
ACCENT_CYAN = (80, 230, 255)
ACCENT_MAGENTA = (255, 90, 200)
ACCENT_GREEN = (90, 255, 160)
ACCENT_YELLOW = (255, 220, 90)
ACCENT_RED = (255, 90, 90)
TEXT_PRIMARY = (220, 230, 245)
TEXT_DIM = (140, 150, 170)
FOOD_CORE = (255, 240, 160)
FOOD_GLOW = (255, 180, 60)

# ---- Spatial hashing ----
CELL_SIZE = 60  # px per spatial-hash cell

# ---- World ----
INITIAL_BOT_COUNT = 60
MAX_BOTS = 220
INITIAL_FOOD_COUNT = 180
MAX_FOOD = 320
FOOD_SPAWN_PER_SEC = 22.0
FOOD_ENERGY = 28.0

# ---- Bot mechanics ----
BOT_RADIUS = 7.0
BOT_MAX_SPEED = 110.0
BOT_MAX_TURN = 4.5  # rad/s
BOT_ACCEL = 180.0
BOT_DRAG = 1.8
BOT_BASE_ENERGY = 100.0
BOT_START_ENERGY = 60.0
BOT_REPRO_THRESHOLD = 130.0
BOT_REPRO_COST = 60.0
BOT_ENERGY_PASSIVE_LOSS = 1.6   # per sec
BOT_ENERGY_SPEED_LOSS = 0.04    # per (unit speed * sec)
BOT_EAT_RANGE = 14.0
BOT_ATTACK_RANGE = 16.0
BOT_ATTACK_DAMAGE = 35.0
BOT_VISION_RANGE = 220.0

# ---- Neural net (DNA) ----
NN_INPUTS = 6
NN_HIDDEN = 8
NN_OUTPUTS = 3
MUTATION_RATE = 0.08       # probability a weight is perturbed
MUTATION_STRENGTH = 0.25   # std-dev of the perturbation

# ---- Visual polish ----
TRAIL_LENGTH = 8
GLOW_LAYERS = 3
SHOW_GRID = False
