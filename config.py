"""
Central configuration for the Digital Evolution ecosystem.
A rich ALife sim: herbivores, carnivores, plants, day/night, evolving traits.
"""

# ---- Display ----
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 860
SIDEBAR_WIDTH = 320
WORLD_WIDTH = SCREEN_WIDTH - SIDEBAR_WIDTH
WORLD_HEIGHT = SCREEN_HEIGHT
TARGET_FPS = 60

# ---- Colors (neon theme) ----
BG_DAY    = (16, 20, 38)
BG_NIGHT  = (6, 8, 18)
GRID_COLOR = (24, 28, 44)
SIDEBAR_BG = (12, 14, 26, 230)
PANEL_BORDER = (60, 80, 140)
ACCENT_CYAN    = (80, 230, 255)
ACCENT_MAGENTA = (255, 90, 200)
ACCENT_GREEN   = (90, 255, 160)
ACCENT_YELLOW  = (255, 220, 90)
ACCENT_RED     = (255, 90, 90)
ACCENT_ORANGE  = (255, 160, 70)
TEXT_PRIMARY = (220, 230, 245)
TEXT_DIM     = (140, 150, 170)

# Plants (food)
PLANT_CORE = (180, 255, 180)
PLANT_GLOW = (100, 220, 120)

# Corpse (meat) — different color from plants
CORPSE_CORE = (255, 200, 130)
CORPSE_GLOW = (220, 130, 80)

# ---- Spatial hashing ----
CELL_SIZE = 70

# ---- World population ----
INITIAL_HERBIVORES = 70
INITIAL_CARNIVORES = 12
MAX_BOTS = 320

INITIAL_PLANTS = 220
MAX_PLANTS = 420
PLANT_REGROWTH_PER_SEC = 26.0        # plants spawned per second when below cap
PLANT_GROW_TIME = 4.0                # secs from seed to full plant
PLANT_ENERGY_FULL = 26.0             # energy when fully grown

# Corpses
CORPSE_DECAY_TIME = 14.0             # secs until corpse disappears
CORPSE_ENERGY_BASE = 55.0

# ---- Day / night ----
DAY_LENGTH_SECS = 90.0               # full day = 90s of sim
NIGHT_ENERGY_PENALTY = 0.4           # extra passive energy drain at night

# ---- Bot mechanics (shared base) ----
BOT_RADIUS_MIN = 5.0
BOT_RADIUS_MAX = 11.0
BOT_MAX_TURN = 5.0                   # rad/s
BOT_DRAG = 1.7
BOT_VISION_RANGE = 230.0

BOT_START_ENERGY = 70.0
BOT_REPRO_THRESHOLD = 140.0
BOT_REPRO_COST = 65.0
BOT_REPRO_COOLDOWN = 5.0             # secs between births

BOT_MAX_AGE = 180.0                  # die of old age
BOT_AGE_ENERGY_PENALTY = 0.6         # multiplier on energy loss when old

BOT_BASE_PASSIVE_LOSS = 1.4          # per sec
BOT_SPEED_ENERGY_LOSS = 0.045        # per (speed * sec)

# Herbivore-specific
HERB_MAX_SPEED = 105.0
HERB_ACCEL = 200.0
HERB_EAT_RANGE = 14.0
HERB_COLOR_TINT = (90, 255, 160)     # base bias for herbivore neon palette

# Carnivore-specific
CARN_MAX_SPEED = 130.0
CARN_ACCEL = 240.0
CARN_ATTACK_RANGE = 18.0
CARN_ATTACK_DAMAGE = 38.0
CARN_KILL_BONUS = 28.0               # energy bonus on kill (separate from corpse)
CARN_COLOR_TINT = (255, 110, 130)    # base bias for carnivore palette

# ---- Neural net (DNA) ----
# Inputs: 10 — see entities._build_inputs
# Outputs: 4 — accel, turn, eat_action, reproduce_desire
NN_INPUTS  = 10
NN_HIDDEN  = 12
NN_OUTPUTS = 4

# Mutation
MUTATION_RATE     = 0.07
MUTATION_STRENGTH = 0.22
TRAIT_MUTATION_STRENGTH = 0.08       # size/speed trait drift

# Speciation: chance carnivore's offspring is herbivore (and vice versa) — rare
SPECIATION_CHANCE = 0.004

# ---- Visual polish ----
TRAIL_LENGTH = 12
GLOW_LAYERS  = 3
SHOW_GRID    = False
SHOW_PHEROMONES = True

# Pheromone field (cheap, decays over time) — used only for visual ambience
PHEROMONE_GRID_DOWNSCALE = 4         # field is WORLD/this per cell
PHEROMONE_DECAY = 0.92               # per frame multiplicative decay
PHEROMONE_DEPOSIT = 14.0             # per bot per frame

# ---- Stats history ----
HISTORY_LEN = 240                    # ~4s @ 60fps
