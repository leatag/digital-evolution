"""
Entities: Food orbs and Bots (with NumPy-based neural-net DNA).
"""
from __future__ import annotations

import math
import random
from collections import deque
from typing import List, Optional, Tuple

import numpy as np

import config


def _tanh(x: np.ndarray) -> np.ndarray:
return np.tanh(x)


class Brain:
"""Tiny feed-forward NN: NN_INPUTS -> NN_HIDDEN -> NN_OUTPUTS.
Weights+biases are the bot's DNA.
"""

__slots__ = ("w1", "b1", "w2", "b2")

def __init__(
    self,
    w1: Optional[np.ndarray] = None,
    b1: Optional[np.ndarray] = None,
    w2: Optional[np.ndarray] = None,
    b2: Optional[np.ndarray] = None,
) -> None:
    if w1 is None:
        # He-ish init scaled small
        self.w1 = np.random.randn(config.NN_INPUTS, config.NN_HIDDEN).astype(np.float32) * 0.6
        self.b1 = np.random.randn(config.NN_HIDDEN).astype(np.float32) * 0.2
        self.w2 = np.random.randn(config.NN_HIDDEN, config.NN_OUTPUTS).astype(np.float32) * 0.6
        self.b2 = np.random.randn(config.NN_OUTPUTS).astype(np.float32) * 0.2
    else:
        self.w1 = w1
        self.b1 = b1
        self.w2 = w2
        self.b2 = b2

def forward(self, inputs: np.ndarray) -> np.ndarray:
    h = _tanh(inputs @ self.w1 + self.b1)
    out = _tanh(h @ self.w2 + self.b2)
    return out

def clone_mutated(self) -> "Brain":
    def mutate(arr: np.ndarray) -> np.ndarray:
        new = arr.copy()
        mask = np.random.rand(*arr.shape) < config.MUTATION_RATE
        if mask.any():
            noise = np.random.randn(*arr.shape).astype(np.float32) * config.MUTATION_STRENGTH
            new = new + mask * noise
        return new.astype(np.float32)

    return Brain(
        w1=mutate(self.w1),
        b1=mutate(self.b1),
        w2=mutate(self.w2),
        b2=mutate(self.b2),
    )

def color_signature(self) -> Tuple[int, int, int]:
    """Map DNA -> stable neon RGB color so families share a hue."""
    flat = np.concatenate([self.w1.ravel(), self.w2.ravel(), self.b1.ravel(), self.b2.ravel()])
    n = flat.size // 3
    r = float(np.tanh(flat[:n].mean() * 3.0))
    g = float(np.tanh(flat[n:2 * n].mean() * 3.0))
    b = float(np.tanh(flat[2 * n:3 * n].mean() * 3.0))
    # map -1..1 to a bright neon range 80..255
    def neon(v: float) -> int:
        return int(80 + (v * 0.5 + 0.5) * 175)
    return (neon(r), neon(g), neon(b))


class Food:
__slots__ = ("x", "y", "energy", "pulse")

def __init__(self, x: float, y: float, energy: float = config.FOOD_ENERGY) -> None:
    self.x = x
    self.y = y
    self.energy = energy
    self.pulse = random.random() * math.tau

def update(self, dt: float) -> None:
    self.pulse = (self.pulse + dt * 3.0) % math.tau


class Bot:
"""A creature with a NumPy brain. Triangle-shaped, neon-colored, evolving."""

__slots__ = (
    "x", "y", "vx", "vy", "heading",
    "energy", "age", "alive",
    "brain", "color",
    "generation", "food_eaten", "kills",
    "trail",
    "last_outputs", "last_inputs",
    "nearest_food_pos", "nearest_bot_pos",
)

def __init__(
    self,
    x: float,
    y: float,
    brain: Optional[Brain] = None,
    generation: int = 1,
) -> None:
    self.x = x
    self.y = y
    self.vx = 0.0
    self.vy = 0.0
    self.heading = random.uniform(0.0, math.tau)
    self.energy = config.BOT_START_ENERGY
    self.age = 0.0
    self.alive = True
    self.brain = brain if brain is not None else Brain()
    self.color = self.brain.color_signature()
    self.generation = generation
    self.food_eaten = 0
    self.kills = 0
    self.trail: deque = deque(maxlen=config.TRAIL_LENGTH)
    self.last_outputs = np.zeros(config.NN_OUTPUTS, dtype=np.float32)
    self.last_inputs = np.zeros(config.NN_INPUTS, dtype=np.float32)
    self.nearest_food_pos: Optional[Tuple[float, float]] = None
    self.nearest_bot_pos: Optional[Tuple[float, float]] = None

# ---- Sensing ----
def _build_inputs(self, nearest_food: Optional[Food], nearest_bot: Optional["Bot"]) -> np.ndarray:
    if nearest_food is not None:
        fdx = nearest_food.x - self.x
        fdy = nearest_food.y - self.y
        fdist = math.hypot(fdx, fdy)
        if fdist > 1e-6:
            fnx = fdx / config.BOT_VISION_RANGE
            fny = fdy / config.BOT_VISION_RANGE
        else:
            fnx, fny = 0.0, 0.0
        self.nearest_food_pos = (nearest_food.x, nearest_food.y)
    else:
        fnx, fny = 0.0, 0.0
        self.nearest_food_pos = None

    if nearest_bot is not None:
        bdx = nearest_bot.x - self.x
        bdy = nearest_bot.y - self.y
        bdist = math.hypot(bdx, bdy)
        bnorm = min(bdist / config.BOT_VISION_RANGE, 1.0)
        self.nearest_bot_pos = (nearest_bot.x, nearest_bot.y)
    else:
        bnorm = 1.0
        self.nearest_bot_pos = None

    energy_norm = min(self.energy / config.BOT_REPRO_THRESHOLD, 1.5)
    age_norm = math.tanh(self.age / 30.0)
    # 6 inputs
    inputs = np.array(
        [fnx, fny, bnorm, energy_norm, age_norm, math.sin(self.heading)],
        dtype=np.float32,
    )
    self.last_inputs = inputs
    return inputs

# ---- Step ----
def update(
    self,
    dt: float,
    nearest_food: Optional[Food],
    nearest_bot: Optional["Bot"],
) -> None:
    if not self.alive:
        return
    inputs = self._build_inputs(nearest_food, nearest_bot)
    out = self.brain.forward(inputs)
    self.last_outputs = out
    accel = float(out[0])      # -1..1
    turn = float(out[1])       # -1..1
    # action = out[2]  -> used externally by engine for eat/attack decisions

    # Update heading
    self.heading = (self.heading + turn * config.BOT_MAX_TURN * dt) % math.tau

    # Apply thrust
    thrust = max(accel, 0.0) * config.BOT_ACCEL
    self.vx += math.cos(self.heading) * thrust * dt
    self.vy += math.sin(self.heading) * thrust * dt

    # Drag
    self.vx -= self.vx * config.BOT_DRAG * dt
    self.vy -= self.vy * config.BOT_DRAG * dt

    # Clamp speed
    speed = math.hypot(self.vx, self.vy)
    if speed > config.BOT_MAX_SPEED:
        scale = config.BOT_MAX_SPEED / speed
        self.vx *= scale
        self.vy *= scale
        speed = config.BOT_MAX_SPEED

    # Move
    self.x += self.vx * dt
    self.y += self.vy * dt

    # World bounds (bounce softly inside world area, not sidebar)
    if self.x < config.BOT_RADIUS:
        self.x = config.BOT_RADIUS
        self.vx *= -0.5
    elif self.x > config.WORLD_WIDTH - config.BOT_RADIUS:
        self.x = config.WORLD_WIDTH - config.BOT_RADIUS
        self.vx *= -0.5
    if self.y < config.BOT_RADIUS:
        self.y = config.BOT_RADIUS
        self.vy *= -0.5
    elif self.y > config.WORLD_HEIGHT - config.BOT_RADIUS:
        self.y = config.WORLD_HEIGHT - config.BOT_RADIUS
        self.vy *= -0.5

    # Energy decay
    self.energy -= config.BOT_ENERGY_PASSIVE_LOSS * dt
    self.energy -= config.BOT_ENERGY_SPEED_LOSS * speed * dt
    self.age += dt

    # Track trail
    self.trail.append((self.x, self.y))

    if self.energy <= 0.0:
        self.alive = False

def reproduce(self) -> "Bot":
    self.energy -= config.BOT_REPRO_COST
    child_brain = self.brain.clone_mutated()
    # Spawn slightly offset
    offset_angle = random.uniform(0.0, math.tau)
    cx = self.x + math.cos(offset_angle) * (config.BOT_RADIUS * 2.2)
    cy = self.y + math.sin(offset_angle) * (config.BOT_RADIUS * 2.2)
    cx = min(max(cx, config.BOT_RADIUS), config.WORLD_WIDTH - config.BOT_RADIUS)
    cy = min(max(cy, config.BOT_RADIUS), config.WORLD_HEIGHT - config.BOT_RADIUS)
    child = Bot(cx, cy, brain=child_brain, generation=self.generation + 1)
    child.energy = config.BOT_START_ENERGY
    return child

def action_signal(self) -> float:
    """Returns the 3rd output: eat/attack tendency."""
    return float(self.last_outputs[2]) if self.last_outputs is not None else 0.0
