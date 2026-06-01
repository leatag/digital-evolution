"""
Entities for the Digital Evolution ecosystem:
- Plant: grows over time, can be eaten by herbivores
- Corpse: decaying meat, can be eaten by carnivores (and starving herbivores)
- Bot: with a Brain (numpy NN DNA) and physical traits (size/speed/diet)
       Two species: herbivore + carnivore
"""
from __future__ import annotations

import math
import random
from collections import deque
from typing import Optional, Tuple

import numpy as np

import config


# ============================================================
# Brain (numpy NN as DNA)
# ============================================================
class Brain:
  __slots__ = ("w1", "b1", "w2", "b2")

  def __init__(self, w1=None, b1=None, w2=None, b2=None) -> None:
      if w1 is None:
          self.w1 = np.random.randn(config.NN_INPUTS, config.NN_HIDDEN).astype(np.float32) * 0.55
          self.b1 = np.random.randn(config.NN_HIDDEN).astype(np.float32) * 0.18
          self.w2 = np.random.randn(config.NN_HIDDEN, config.NN_OUTPUTS).astype(np.float32) * 0.55
          self.b2 = np.random.randn(config.NN_OUTPUTS).astype(np.float32) * 0.18
      else:
          self.w1, self.b1, self.w2, self.b2 = w1, b1, w2, b2

  def forward(self, inputs: np.ndarray) -> np.ndarray:
      h = np.tanh(inputs @ self.w1 + self.b1)
      return np.tanh(h @ self.w2 + self.b2)

  def clone_mutated(self) -> "Brain":
      def mut(arr: np.ndarray) -> np.ndarray:
          mask = (np.random.rand(*arr.shape) < config.MUTATION_RATE)
          if not mask.any():
              return arr.copy()
          noise = np.random.randn(*arr.shape).astype(np.float32) * config.MUTATION_STRENGTH
          return (arr + mask * noise).astype(np.float32)
      return Brain(mut(self.w1), mut(self.b1), mut(self.w2), mut(self.b2))

  def signature(self) -> Tuple[float, float, float]:
      """3 floats in -1..1 from DNA — used for color tint."""
      flat = np.concatenate([self.w1.ravel(), self.w2.ravel()])
      n = flat.size // 3
      return (
          float(np.tanh(flat[:n].mean() * 3.0)),
          float(np.tanh(flat[n:2 * n].mean() * 3.0)),
          float(np.tanh(flat[2 * n:3 * n].mean() * 3.0)),
      )


# ============================================================
# Plants & corpses
# ============================================================
class Plant:
  __slots__ = ("x", "y", "grow", "pulse")

  def __init__(self, x: float, y: float, grow: float = 0.0) -> None:
      self.x = x
      self.y = y
      self.grow = grow                 # 0..1
      self.pulse = random.random() * math.tau

  def update(self, dt: float) -> None:
      if self.grow < 1.0:
          self.grow = min(1.0, self.grow + dt / config.PLANT_GROW_TIME)
      self.pulse = (self.pulse + dt * 2.6) % math.tau

  @property
  def energy(self) -> float:
      # only ripe plants give full energy; saplings give partial
      return config.PLANT_ENERGY_FULL * (0.25 + 0.75 * self.grow)


class Corpse:
  __slots__ = ("x", "y", "energy", "age", "pulse")

  def __init__(self, x: float, y: float, energy: float) -> None:
      self.x = x
      self.y = y
      self.energy = energy
      self.age = 0.0
      self.pulse = random.random() * math.tau

  def update(self, dt: float) -> None:
      self.age += dt
      self.pulse = (self.pulse + dt * 1.5) % math.tau

  @property
  def expired(self) -> bool:
      return self.age >= config.CORPSE_DECAY_TIME

  @property
  def fade(self) -> float:
      return max(0.0, 1.0 - self.age / config.CORPSE_DECAY_TIME)


# ============================================================
# Traits — physical DNA separate from brain
# ============================================================
class Traits:
  __slots__ = ("size", "speed_mod", "vision_mod", "metabolism")

  def __init__(
      self,
      size: float = 0.5,
      speed_mod: float = 1.0,
      vision_mod: float = 1.0,
      metabolism: float = 1.0,
  ) -> None:
      # size 0..1 maps to radius
      self.size = float(np.clip(size, 0.0, 1.0))
      self.speed_mod = float(np.clip(speed_mod, 0.5, 1.5))
      self.vision_mod = float(np.clip(vision_mod, 0.6, 1.6))
      self.metabolism = float(np.clip(metabolism, 0.7, 1.4))

  def mutate(self) -> "Traits":
      s = config.TRAIT_MUTATION_STRENGTH
      return Traits(
          size      = self.size      + random.gauss(0, s),
          speed_mod = self.speed_mod + random.gauss(0, s),
          vision_mod= self.vision_mod+ random.gauss(0, s * 0.7),
          metabolism= self.metabolism+ random.gauss(0, s * 0.7),
      )

  @property
  def radius(self) -> float:
      return config.BOT_RADIUS_MIN + (config.BOT_RADIUS_MAX - config.BOT_RADIUS_MIN) * self.size


# ============================================================
# Bot
# ============================================================
class Bot:
  __slots__ = (
      "x", "y", "vx", "vy", "heading",
      "energy", "age", "alive", "cause_of_death",
      "brain", "traits", "species", "color",
      "generation", "plants_eaten", "kills", "births",
      "repro_cooldown",
      "trail",
      "last_outputs", "last_inputs",
      "nearest_plant_pos", "nearest_bot_pos", "nearest_corpse_pos",
  )

  HERBIVORE = "herbivore"
  CARNIVORE = "carnivore"

  def __init__(
      self,
      x: float,
      y: float,
      species: str = HERBIVORE,
      brain: Optional[Brain] = None,
      traits: Optional[Traits] = None,
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
      self.cause_of_death: Optional[str] = None
      self.species = species
      self.brain = brain if brain is not None else Brain()
      self.traits = traits if traits is not None else Traits(
          size=random.uniform(0.2, 0.7),
          speed_mod=random.uniform(0.9, 1.1),
          vision_mod=random.uniform(0.9, 1.1),
          metabolism=random.uniform(0.9, 1.1),
      )
      self.color = self._compute_color()
      self.generation = generation
      self.plants_eaten = 0
      self.kills = 0
      self.births = 0
      self.repro_cooldown = 0.0
      self.trail: deque = deque(maxlen=config.TRAIL_LENGTH)
      self.last_outputs = np.zeros(config.NN_OUTPUTS, dtype=np.float32)
      self.last_inputs  = np.zeros(config.NN_INPUTS, dtype=np.float32)
      self.nearest_plant_pos: Optional[Tuple[float, float]] = None
      self.nearest_bot_pos:   Optional[Tuple[float, float]] = None
      self.nearest_corpse_pos:Optional[Tuple[float, float]] = None

  # ----- visual color -----
  def _compute_color(self) -> Tuple[int, int, int]:
      sig = self.brain.signature()
      tint = config.HERB_COLOR_TINT if self.species == self.HERBIVORE else config.CARN_COLOR_TINT
      # map each sig component -1..1 to 80..255 bright neon
      def neon(v: float, base: int) -> int:
          mixed = (v * 0.5 + 0.5) * 200 + base * 0.3
          return int(max(70, min(255, mixed)))
      return (neon(sig[0], tint[0]), neon(sig[1], tint[1]), neon(sig[2], tint[2]))

  # ----- combat / metabolic stats from traits -----
  @property
  def radius(self) -> float:
      return self.traits.radius

  @property
  def max_speed(self) -> float:
      base = config.CARN_MAX_SPEED if self.species == self.CARNIVORE else config.HERB_MAX_SPEED
      # bigger = slower
      size_pen = 1.0 - (self.traits.size - 0.5) * 0.5
      return base * self.traits.speed_mod * max(0.55, size_pen)

  @property
  def accel(self) -> float:
      base = config.CARN_ACCEL if self.species == self.CARNIVORE else config.HERB_ACCEL
      return base * self.traits.speed_mod

  @property
  def vision(self) -> float:
      return config.BOT_VISION_RANGE * self.traits.vision_mod

  @property
  def passive_loss(self) -> float:
      # bigger = more upkeep
      return config.BOT_BASE_PASSIVE_LOSS * self.traits.metabolism * (0.7 + self.traits.size)

  # ----- sensing -----
  def _build_inputs(
      self,
      nearest_plant: Optional["Plant"],
      nearest_bot: Optional["Bot"],
      nearest_corpse: Optional["Corpse"],
      is_night: bool,
  ) -> np.ndarray:
      vrange = self.vision

      # plant
      if nearest_plant is not None:
          pdx = (nearest_plant.x - self.x) / vrange
          pdy = (nearest_plant.y - self.y) / vrange
          pgrow = nearest_plant.grow
          self.nearest_plant_pos = (nearest_plant.x, nearest_plant.y)
      else:
          pdx, pdy, pgrow = 0.0, 0.0, 0.0
          self.nearest_plant_pos = None

      # bot
      if nearest_bot is not None:
          bdx = (nearest_bot.x - self.x) / vrange
          bdy = (nearest_bot.y - self.y) / vrange
          # 1 if same species, -1 if different
          same = 1.0 if nearest_bot.species == self.species else -1.0
          bsize = nearest_bot.traits.size
          self.nearest_bot_pos = (nearest_bot.x, nearest_bot.y)
      else:
          bdx, bdy, same, bsize = 0.0, 0.0, 0.0, 0.0
          self.nearest_bot_pos = None

      # corpse
      if nearest_corpse is not None:
          cdx = (nearest_corpse.x - self.x) / vrange
          cdy = (nearest_corpse.y - self.y) / vrange
          self.nearest_corpse_pos = (nearest_corpse.x, nearest_corpse.y)
      else:
          cdx, cdy = 0.0, 0.0
          self.nearest_corpse_pos = None

      energy_norm = min(self.energy / config.BOT_REPRO_THRESHOLD, 1.5)
      night_flag = 1.0 if is_night else 0.0

      inputs = np.array(
          [pdx, pdy, bdx, bdy, same, energy_norm, pgrow, cdx, cdy, night_flag],
          dtype=np.float32,
      )
      self.last_inputs = inputs
      return inputs

  # ----- step -----
  def update(
      self,
      dt: float,
      nearest_plant: Optional["Plant"],
      nearest_bot: Optional["Bot"],
      nearest_corpse: Optional["Corpse"],
      is_night: bool,
  ) -> None:
      if not self.alive:
          return

      inputs = self._build_inputs(nearest_plant, nearest_bot, nearest_corpse, is_night)
      out = self.brain.forward(inputs)
      self.last_outputs = out
      accel_cmd = float(out[0])  # -1..1
      turn_cmd  = float(out[1])  # -1..1
      # out[2] = action (eat/attack), out[3] = reproduce desire

      # turn
      self.heading = (self.heading + turn_cmd * config.BOT_MAX_TURN * dt) % math.tau

      # thrust
      thrust = max(accel_cmd, 0.0) * self.accel
      self.vx += math.cos(self.heading) * thrust * dt
      self.vy += math.sin(self.heading) * thrust * dt

      # drag
      self.vx -= self.vx * config.BOT_DRAG * dt
      self.vy -= self.vy * config.BOT_DRAG * dt

      # clamp speed
      speed = math.hypot(self.vx, self.vy)
      max_s = self.max_speed
      if speed > max_s:
          self.vx *= max_s / speed
          self.vy *= max_s / speed
          speed = max_s

      # move
      self.x += self.vx * dt
      self.y += self.vy * dt

      # bounds
      r = self.radius
      if self.x < r:
          self.x = r
          self.vx *= -0.5
      elif self.x > config.WORLD_WIDTH - r:
          self.x = config.WORLD_WIDTH - r
          self.vx *= -0.5
      if self.y < r:
          self.y = r
          self.vy *= -0.5
      elif self.y > config.WORLD_HEIGHT - r:
          self.y = config.WORLD_HEIGHT - r
          self.vy *= -0.5

      # metabolism
      age_factor = 1.0
      if self.age > config.BOT_MAX_AGE * 0.7:
          age_factor = 1.0 + config.BOT_AGE_ENERGY_PENALTY
      passive = self.passive_loss * age_factor
      if is_night:
          passive += config.NIGHT_ENERGY_PENALTY
      self.energy -= passive * dt
      self.energy -= config.BOT_SPEED_ENERGY_LOSS * speed * dt

      self.age += dt
      if self.repro_cooldown > 0.0:
          self.repro_cooldown = max(0.0, self.repro_cooldown - dt)

      self.trail.append((self.x, self.y))

      if self.energy <= 0.0:
          self.alive = False
          self.cause_of_death = "starvation"
      elif self.age >= config.BOT_MAX_AGE:
          self.alive = False
          self.cause_of_death = "old age"

  # ----- decisions exposed to engine -----
  def action_signal(self) -> float:
      return float(self.last_outputs[2]) if self.last_outputs is not None else 0.0

  def reproduce_desire(self) -> float:
      return float(self.last_outputs[3]) if self.last_outputs is not None else 0.0

  def can_reproduce(self) -> bool:
      return (
          self.alive
          and self.energy >= config.BOT_REPRO_THRESHOLD
          and self.repro_cooldown <= 0.0
          and self.reproduce_desire() > 0.0
      )

  def reproduce(self) -> "Bot":
      self.energy -= config.BOT_REPRO_COST
      self.repro_cooldown = config.BOT_REPRO_COOLDOWN
      self.births += 1

      child_brain = self.brain.clone_mutated()
      child_traits = self.traits.mutate()

      # rare speciation (parent's offspring may flip diet)
      child_species = self.species
      if random.random() < config.SPECIATION_CHANCE:
          child_species = (
              Bot.CARNIVORE if self.species == Bot.HERBIVORE else Bot.HERBIVORE
          )

      offset_angle = random.uniform(0.0, math.tau)
      d = self.radius * 2.4
      cx = min(max(self.x + math.cos(offset_angle) * d, self.radius),
               config.WORLD_WIDTH - self.radius)
      cy = min(max(self.y + math.sin(offset_angle) * d, self.radius),
               config.WORLD_HEIGHT - self.radius)

      child = Bot(
          cx, cy,
          species=child_species,
          brain=child_brain,
          traits=child_traits,
          generation=self.generation + 1,
      )
      child.energy = config.BOT_START_ENERGY
      return child
