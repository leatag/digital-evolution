"""
World engine for the Digital Evolution ecosystem.

Features:
- Spatial hash for plants, corpses, bots
- Day/night cycle
- Food web: herbivores eat plants; carnivores eat bots & corpses
- Plants regrow over time (not just spawn)
- Population history for graphs
"""
from __future__ import annotations

import math
import random
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

import config
from entities import Bot, Corpse, Plant


class SpatialHash:
  def __init__(self, cell_size: int) -> None:
      self.cell_size = cell_size
      self.cells: Dict[Tuple[int, int], List] = defaultdict(list)

  def clear(self) -> None:
      self.cells.clear()

  def _key(self, x: float, y: float) -> Tuple[int, int]:
      return (int(x // self.cell_size), int(y // self.cell_size))

  def insert(self, obj, x: float, y: float) -> None:
      self.cells[self._key(x, y)].append(obj)

  def neighbors(self, x: float, y: float) -> List:
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
      self.plants: List[Plant] = []
      self.corpses: List[Corpse] = []

      self.bot_hash    = SpatialHash(config.CELL_SIZE)
      self.plant_hash  = SpatialHash(config.CELL_SIZE)
      self.corpse_hash = SpatialHash(config.CELL_SIZE)

      self.tick = 0
      self.elapsed = 0.0
      self._plant_spawn_acc = 0.0
      self.max_generation = 1

      # Pheromone field — purely visual ambience
      self.ph_w = config.WORLD_WIDTH // config.PHEROMONE_GRID_DOWNSCALE
      self.ph_h = config.WORLD_HEIGHT // config.PHEROMONE_GRID_DOWNSCALE
      self.pheromones = np.zeros((self.ph_h, self.ph_w), dtype=np.float32)

      # Population history (deques of ints)
      self.history_herb:  Deque[int] = deque(maxlen=config.HISTORY_LEN)
      self.history_carn:  Deque[int] = deque(maxlen=config.HISTORY_LEN)
      self.history_plants:Deque[int] = deque(maxlen=config.HISTORY_LEN)

      self.births_total = 0
      self.deaths_total = 0
      self.last_death_cause: Optional[str] = None

      self.reset()

  # ============================================================
  # Lifecycle
  # ============================================================
  def reset(self) -> None:
      self.bots.clear()
      self.plants.clear()
      self.corpses.clear()
      self.tick = 0
      self.elapsed = 0.0
      self._plant_spawn_acc = 0.0
      self.max_generation = 1
      self.births_total = 0
      self.deaths_total = 0
      self.last_death_cause = None
      self.history_herb.clear()
      self.history_carn.clear()
      self.history_plants.clear()
      self.pheromones.fill(0.0)

      for _ in range(config.INITIAL_HERBIVORES):
          self.bots.append(Bot(
              random.uniform(30, config.WORLD_WIDTH - 30),
              random.uniform(30, config.WORLD_HEIGHT - 30),
              species=Bot.HERBIVORE,
          ))
      for _ in range(config.INITIAL_CARNIVORES):
          self.bots.append(Bot(
              random.uniform(30, config.WORLD_WIDTH - 30),
              random.uniform(30, config.WORLD_HEIGHT - 30),
              species=Bot.CARNIVORE,
          ))
      for _ in range(config.INITIAL_PLANTS):
          self.plants.append(Plant(
              random.uniform(10, config.WORLD_WIDTH - 10),
              random.uniform(10, config.WORLD_HEIGHT - 10),
              grow=random.uniform(0.4, 1.0),
          ))

  # ============================================================
  # Day/night
  # ============================================================
  @property
  def day_phase(self) -> float:
      """0..1 progress through current day."""
      return (self.elapsed % config.DAY_LENGTH_SECS) / config.DAY_LENGTH_SECS

  @property
  def is_night(self) -> bool:
      # second half = night
      return self.day_phase > 0.5

  @property
  def day_brightness(self) -> float:
      """0 = full night, 1 = full noon. Smooth sin curve."""
      return 0.5 + 0.5 * math.sin(self.day_phase * math.tau - math.pi / 2)

  # ============================================================
  # Spatial hashing
  # ============================================================
  def _rebuild_hashes(self) -> None:
      self.bot_hash.clear()
      self.plant_hash.clear()
      self.corpse_hash.clear()
      for b in self.bots:
          if b.alive:
              self.bot_hash.insert(b, b.x, b.y)
      for p in self.plants:
          self.plant_hash.insert(p, p.x, p.y)
      for c in self.corpses:
          self.corpse_hash.insert(c, c.x, c.y)

  def _nearest_plant(self, b: Bot) -> Optional[Plant]:
      best: Optional[Plant] = None
      best_d2 = b.vision * b.vision
      for p in self.plant_hash.neighbors(b.x, b.y):
          d2 = (p.x - b.x) ** 2 + (p.y - b.y) ** 2
          if d2 < best_d2:
              best_d2 = d2
              best = p
      return best

  def _nearest_bot(self, b: Bot) -> Optional[Bot]:
      best: Optional[Bot] = None
      best_d2 = b.vision * b.vision
      for o in self.bot_hash.neighbors(b.x, b.y):
          if o is b or not o.alive:
              continue
          d2 = (o.x - b.x) ** 2 + (o.y - b.y) ** 2
          if d2 < best_d2:
              best_d2 = d2
              best = o
      return best

  def _nearest_corpse(self, b: Bot) -> Optional[Corpse]:
      best: Optional[Corpse] = None
      best_d2 = b.vision * b.vision
      for c in self.corpse_hash.neighbors(b.x, b.y):
          d2 = (c.x - b.x) ** 2 + (c.y - b.y) ** 2
          if d2 < best_d2:
              best_d2 = d2
              best = c
      return best

  # ============================================================
  # Plants
  # ============================================================
  def _spawn_plant(self) -> None:
      if len(self.plants) >= config.MAX_PLANTS:
          return
      self.plants.append(Plant(
          random.uniform(10, config.WORLD_WIDTH - 10),
          random.uniform(10, config.WORLD_HEIGHT - 10),
          grow=0.0,
      ))

  # ============================================================
  # Pheromones (visual only)
  # ============================================================
  def _deposit_pheromones(self) -> None:
      if not config.SHOW_PHEROMONES:
          return
      scale = config.PHEROMONE_GRID_DOWNSCALE
      for b in self.bots:
          if not b.alive:
              continue
          ix = int(b.x // scale)
          iy = int(b.y // scale)
          if 0 <= iy < self.ph_h and 0 <= ix < self.ph_w:
              self.pheromones[iy, ix] = min(
                  255.0, self.pheromones[iy, ix] + config.PHEROMONE_DEPOSIT
              )

  def _decay_pheromones(self) -> None:
      if not config.SHOW_PHEROMONES:
          return
      self.pheromones *= config.PHEROMONE_DECAY

  # ============================================================
  # Main step
  # ============================================================
  def update(self, dt: float) -> None:
      self.tick += 1
      self.elapsed += dt
      is_night = self.is_night

      # plants: regrow + spawn new
      for p in self.plants:
          p.update(dt)
      self._plant_spawn_acc += config.PLANT_REGROWTH_PER_SEC * dt
      while self._plant_spawn_acc >= 1.0:
          self._spawn_plant()
          self._plant_spawn_acc -= 1.0

      # corpses: decay
      for c in self.corpses:
          c.update(dt)
      self.corpses = [c for c in self.corpses if not c.expired]

      # rebuild spatial hashes
      self._rebuild_hashes()

      # bot sensing + movement
      for b in self.bots:
          if not b.alive:
              continue
          nf = self._nearest_plant(b)  if b.species == Bot.HERBIVORE else None
          no = self._nearest_bot(b)
          nc = self._nearest_corpse(b)
          b.update(dt, nf, no, nc, is_night)

      # interactions
      new_bots: List[Bot] = []
      new_corpses: List[Corpse] = []

      for b in self.bots:
          if not b.alive:
              continue
          action = b.action_signal()
          wants_eat    = action > 0.0
          wants_attack = action < -0.3

          if b.species == Bot.HERBIVORE:
              if wants_eat:
                  # eat plant
                  plant = self._nearest_plant(b)
                  if plant is not None:
                      d2 = (plant.x - b.x) ** 2 + (plant.y - b.y) ** 2
                      if d2 <= config.HERB_EAT_RANGE ** 2:
                          b.energy += plant.energy
                          b.plants_eaten += 1
                          try:
                              self.plants.remove(plant)
                          except ValueError:
                              pass
                  # starving herbivore can scavenge corpses
                  elif b.energy < 40.0:
                      corpse = self._nearest_corpse(b)
                      if corpse is not None:
                          d2 = (corpse.x - b.x) ** 2 + (corpse.y - b.y) ** 2
                          if d2 <= config.HERB_EAT_RANGE ** 2:
                              b.energy += corpse.energy * 0.4
                              try:
                                  self.corpses.remove(corpse)
                              except ValueError:
                                  pass
          else:
              # CARNIVORE
              if wants_attack:
                  prey = self._nearest_bot(b)
                  if prey is not None and prey.alive and prey.species == Bot.HERBIVORE:
                      d2 = (prey.x - b.x) ** 2 + (prey.y - b.y) ** 2
                      if d2 <= config.CARN_ATTACK_RANGE ** 2:
                          prey.energy -= config.CARN_ATTACK_DAMAGE
                          if prey.energy <= 0.0:
                              prey.alive = False
                              prey.cause_of_death = "predation"
                              b.kills += 1
                              b.energy += config.CARN_KILL_BONUS
                              new_corpses.append(Corpse(
                                  prey.x, prey.y,
                                  energy=config.CORPSE_ENERGY_BASE * (0.6 + prey.traits.size)
                              ))
              if wants_eat:
                  corpse = self._nearest_corpse(b)
                  if corpse is not None:
                      d2 = (corpse.x - b.x) ** 2 + (corpse.y - b.y) ** 2
                      if d2 <= config.HERB_EAT_RANGE ** 2:
                          b.energy += corpse.energy * 0.6
                          try:
                              self.corpses.remove(corpse)
                          except ValueError:
                              pass

          # reproduce
          if (
              b.can_reproduce()
              and len(self.bots) + len(new_bots) < config.MAX_BOTS
          ):
              child = b.reproduce()
              new_bots.append(child)
              if child.generation > self.max_generation:
                  self.max_generation = child.generation
              self.births_total += 1

      # Count deaths this frame, drop corpses
      for b in self.bots:
          if not b.alive:
              self.deaths_total += 1
              self.last_death_cause = b.cause_of_death

      # drop bodies for any newly-dead bots that don't already have a corpse
      # (predation already added a corpse; starvation/old age also should)
      for b in self.bots:
          if not b.alive and b.cause_of_death in ("starvation", "old age"):
              new_corpses.append(Corpse(
                  b.x, b.y,
                  energy=config.CORPSE_ENERGY_BASE * (0.4 + b.traits.size * 0.7),
              ))

      # remove dead, add new
      self.bots = [b for b in self.bots if b.alive]
      self.bots.extend(new_bots)
      self.corpses.extend(new_corpses)

      # extinction safety net: re-seed minimally so the world keeps living
      herb_count = sum(1 for b in self.bots if b.species == Bot.HERBIVORE)
      carn_count = sum(1 for b in self.bots if b.species == Bot.CARNIVORE)
      if herb_count == 0:
          for _ in range(10):
              self.bots.append(Bot(
                  random.uniform(30, config.WORLD_WIDTH - 30),
                  random.uniform(30, config.WORLD_HEIGHT - 30),
                  species=Bot.HERBIVORE,
              ))
      if carn_count == 0 and herb_count > 30:
          for _ in range(3):
              self.bots.append(Bot(
                  random.uniform(30, config.WORLD_WIDTH - 30),
                  random.uniform(30, config.WORLD_HEIGHT - 30),
                  species=Bot.CARNIVORE,
              ))

      # pheromones
      self._deposit_pheromones()
      self._decay_pheromones()

      # history
      self.history_herb.append(sum(1 for b in self.bots if b.species == Bot.HERBIVORE))
      self.history_carn.append(sum(1 for b in self.bots if b.species == Bot.CARNIVORE))
      self.history_plants.append(len(self.plants))

  # ============================================================
  # Selection
  # ============================================================
  def bot_at(self, px: float, py: float, radius_mult: float = 2.5) -> Optional[Bot]:
      self._rebuild_hashes()
      best: Optional[Bot] = None
      best_d2 = float("inf")
      for b in self.bot_hash.neighbors(px, py):
          if not b.alive:
              continue
          d2 = (b.x - px) ** 2 + (b.y - py) ** 2
          r2 = (b.radius * radius_mult) ** 2
          if d2 <= r2 and d2 < best_d2:
              best_d2 = d2
              best = b
      return best

  # ============================================================
  # Convenience counts
  # ============================================================
  @property
  def herbivore_count(self) -> int:
      return sum(1 for b in self.bots if b.species == Bot.HERBIVORE and b.alive)

  @property
  def carnivore_count(self) -> int:
      return sum(1 for b in self.bots if b.species == Bot.CARNIVORE and b.alive)
