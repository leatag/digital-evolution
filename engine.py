"""
World engine: spatial hashing, neighbor queries, food spawning, eat/attack/reproduce logic.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import config
from entities import Bot, Food


class SpatialHash:
"""Uniform grid spatial hash. Keeps neighbor queries O(local)."""

def __init__(self, cell_size: int) -> None:
    self.cell_size = cell_size
    self.cells: Dict[Tuple[int, int], List] = defaultdict(list)

def clear(self) -> None:
    self.cells.clear()

def _key(self, x: float, y: float) -> Tuple[int, int]:
    return (int(x // self.cell_size), int(y // self.cell_size))

def insert(self, obj, x: float, y: float) -> None:
    self.cells[self._key(x, y)].append(obj)

def query_neighbors(self, x: float, y: float) -> List:
    cx, cy = self._key(x, y)
    out: List = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            bucket = self.cells.get((cx + dx, cy + dy))
            if bucket:
                out.extend(bucket)
    return out


class World:
def __init__(self) -> None:
    self.bots: List[Bot] = []
    self.foods: List[Food] = []
    self.bot_hash = SpatialHash(config.CELL_SIZE)
    self.food_hash = SpatialHash(config.CELL_SIZE)
    self.tick = 0
    self.elapsed = 0.0
    self._food_spawn_acc = 0.0
    self.max_generation = 1
    self.reset()

# ---- Lifecycle ----
def reset(self) -> None:
    self.bots = []
    self.foods = []
    self.tick = 0
    self.elapsed = 0.0
    self._food_spawn_acc = 0.0
    self.max_generation = 1
    for _ in range(config.INITIAL_BOT_COUNT):
        self.bots.append(
            Bot(
                random.uniform(20, config.WORLD_WIDTH - 20),
                random.uniform(20, config.WORLD_HEIGHT - 20),
            )
        )
    for _ in range(config.INITIAL_FOOD_COUNT):
        self._spawn_food()

def _spawn_food(self) -> None:
    if len(self.foods) >= config.MAX_FOOD:
        return
    self.foods.append(
        Food(
            random.uniform(10, config.WORLD_WIDTH - 10),
            random.uniform(10, config.WORLD_HEIGHT - 10),
        )
    )

# ---- Hashing ----
def _rebuild_hashes(self) -> None:
    self.bot_hash.clear()
    self.food_hash.clear()
    for b in self.bots:
        if b.alive:
            self.bot_hash.insert(b, b.x, b.y)
    for f in self.foods:
        self.food_hash.insert(f, f.x, f.y)

# ---- Per-bot neighbor lookup ----
def _nearest_food(self, b: Bot) -> Optional[Food]:
    best: Optional[Food] = None
    best_d2 = config.BOT_VISION_RANGE * config.BOT_VISION_RANGE
    for f in self.food_hash.query_neighbors(b.x, b.y):
        dx = f.x - b.x
        dy = f.y - b.y
        d2 = dx * dx + dy * dy
        if d2 < best_d2:
            best_d2 = d2
            best = f
    return best

def _nearest_bot(self, b: Bot) -> Optional[Bot]:
    best: Optional[Bot] = None
    best_d2 = config.BOT_VISION_RANGE * config.BOT_VISION_RANGE
    for other in self.bot_hash.query_neighbors(b.x, b.y):
        if other is b or not other.alive:
            continue
        dx = other.x - b.x
        dy = other.y - b.y
        d2 = dx * dx + dy * dy
        if d2 < best_d2:
            best_d2 = d2
            best = other
    return best

# ---- Main step ----
def update(self, dt: float) -> None:
    self.tick += 1
    self.elapsed += dt

    # Food spawn accumulator
    self._food_spawn_acc += config.FOOD_SPAWN_PER_SEC * dt
    while self._food_spawn_acc >= 1.0:
        self._spawn_food()
        self._food_spawn_acc -= 1.0

    # Rebuild spatial hashes once per frame
    self._rebuild_hashes()

    # Update bots (sense + decide + move)
    for b in self.bots:
        if not b.alive:
            continue
        nf = self._nearest_food(b)
        nb = self._nearest_bot(b)
        b.update(dt, nf, nb)

    # Food update (visual pulse)
    for f in self.foods:
        f.update(dt)

    # Interactions: eat, attack, reproduce
    new_bots: List[Bot] = []
    dead_drops: List[Tuple[float, float]] = []

    for b in self.bots:
        if not b.alive:
            continue
        action = b.action_signal()  # -1..1
        wants_eat = action > 0.0
        wants_attack = action < -0.3

        # Eat: consume nearest food if in range and eat-leaning
        if wants_eat:
            near_food = self._nearest_food(b)
            if near_food is not None:
                dx = near_food.x - b.x
                dy = near_food.y - b.y
                if dx * dx + dy * dy <= config.BOT_EAT_RANGE * config.BOT_EAT_RANGE:
                    b.energy += near_food.energy
                    b.food_eaten += 1
                    try:
                        self.foods.remove(near_food)
                    except ValueError:
                        pass

        # Attack: damage nearest bot if in range and attack-leaning
        if wants_attack:
            other = self._nearest_bot(b)
            if other is not None and other.alive:
                dx = other.x - b.x
                dy = other.y - b.y
                if dx * dx + dy * dy <= config.BOT_ATTACK_RANGE * config.BOT_ATTACK_RANGE:
                    other.energy -= config.BOT_ATTACK_DAMAGE
                    if other.energy <= 0.0:
                        other.alive = False
                        b.kills += 1
                        b.energy += 20.0
                        dead_drops.append((other.x, other.y))

        # Reproduce
        if (
            b.alive
            and b.energy >= config.BOT_REPRO_THRESHOLD
            and len(self.bots) + len(new_bots) < config.MAX_BOTS
        ):
            child = b.reproduce()
            new_bots.append(child)
            if child.generation > self.max_generation:
                self.max_generation = child.generation

    # Drop food where bots died
    for dx, dy in dead_drops:
        if len(self.foods) < config.MAX_FOOD:
            self.foods.append(Food(dx, dy, energy=config.FOOD_ENERGY * 1.2))

    # Cull the dead
    self.bots = [b for b in self.bots if b.alive]
    self.bots.extend(new_bots)

    # Population safety net: if extinction, reseed lightly
    if not self.bots:
        for _ in range(8):
            self.bots.append(
                Bot(
                    random.uniform(20, config.WORLD_WIDTH - 20),
                    random.uniform(20, config.WORLD_HEIGHT - 20),
                )
            )

# ---- Selection ----
def bot_at(self, px: float, py: float, radius_mult: float = 2.5) -> Optional[Bot]:
    r2 = (config.BOT_RADIUS * radius_mult) ** 2
    # use hash for speed
    self._rebuild_hashes()
    for b in self.bot_hash.query_neighbors(px, py):
        dx = b.x - px
        dy = b.y - py
        if dx * dx + dy * dy <= r2 and b.alive:
            return b
    return None
