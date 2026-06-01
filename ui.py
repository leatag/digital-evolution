"""
Rendering & UI for the ecosystem:
- Day/night sky gradient
- Pheromone heatmap (faint trails of where life has been)
- Plants (sapling -> ripe), corpses (decay tint)
- Herbivores (sleek triangles) + Carnivores (sharper, larger, predator look)
- Sidebar: population, day phase, selected creature, brain readouts, mini-graph
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

import numpy as np
import pygame
from pygame import gfxdraw

import config
from entities import Bot


def _lerp(a, b, t):
  return a + (b - a) * t


def _lerp_color(c1, c2, t):
  return (
      int(_lerp(c1[0], c2[0], t)),
      int(_lerp(c1[1], c2[1], t)),
      int(_lerp(c1[2], c2[2], t)),
  )


class UI:
  def __init__(self, screen: pygame.Surface, world) -> None:
      self.screen = screen
      self.world = world
      self.selected_bot: Optional[Bot] = None

      self.font_xs = pygame.font.SysFont("consolas", 12)
      self.font_sm = pygame.font.SysFont("consolas", 14)
      self.font_md = pygame.font.SysFont("consolas", 16, bold=True)
      self.font_lg = pygame.font.SysFont("consolas", 22, bold=True)

      self.world_surf = pygame.Surface(
          (config.WORLD_WIDTH, config.WORLD_HEIGHT), pygame.SRCALPHA
      )
      self.glow_surf = pygame.Surface(
          (config.WORLD_WIDTH, config.WORLD_HEIGHT), pygame.SRCALPHA
      )

      # pre-computed surface for pheromone field (same scale as world)
      self.ph_surf = pygame.Surface(
          (config.WORLD_WIDTH, config.WORLD_HEIGHT), pygame.SRCALPHA
      )

  # ============================================================
  # Input
  # ============================================================
  def handle_click(self, pos) -> None:
      x, y = pos
      if x >= config.WORLD_WIDTH:
          return
      clicked = self.world.bot_at(x, y)
      if clicked is None and self.selected_bot is not None:
          clicked = self.world.bot_at(x, y, radius_mult=4.0)
      self.selected_bot = clicked

  # ============================================================
  # Draw root
  # ============================================================
  def draw(self, fps: float, paused: bool) -> None:
      self._draw_sky()
      self.world_surf.fill((0, 0, 0, 0))
      self.glow_surf.fill((0, 0, 0, 0))

      self._draw_pheromones()
      self._draw_plants()
      self._draw_corpses()
      self._draw_bots()

      if self.selected_bot is not None and self.selected_bot.alive:
          self._draw_selection_overlay(self.selected_bot)
      else:
          self.selected_bot = None if (self.selected_bot is not None and not self.selected_bot.alive) else self.selected_bot

      self.screen.blit(self.glow_surf, (0, 0))
      self.screen.blit(self.world_surf, (0, 0))

      self._draw_sidebar(fps, paused)
      self._draw_topbar(paused)

  # ============================================================
  # Sky (day/night gradient)
  # ============================================================
  def _draw_sky(self) -> None:
      brightness = self.world.day_brightness
      top = _lerp_color(config.BG_NIGHT, config.BG_DAY, brightness)
      # subtle vertical gradient
      bottom = (
          max(0, top[0] - 6),
          max(0, top[1] - 8),
          max(0, top[2] - 12),
      )
      # cheap gradient: 6 horizontal bands
      bands = 6
      bh = config.WORLD_HEIGHT // bands
      for i in range(bands):
          t = i / max(1, bands - 1)
          col = _lerp_color(top, bottom, t)
          pygame.draw.rect(
              self.screen, col,
              (0, i * bh, config.WORLD_WIDTH, bh + 2),
          )
      # right sidebar area gets the night-tinted color always
      pygame.draw.rect(
          self.screen, config.BG_NIGHT,
          (config.WORLD_WIDTH, 0, config.SIDEBAR_WIDTH, config.SCREEN_HEIGHT),
      )

  # ============================================================
  # Pheromones (faint life-trail heatmap)
  # ============================================================
  def _draw_pheromones(self) -> None:
      if not config.SHOW_PHEROMONES:
          return
      ph = self.world.pheromones
      if ph.max() < 1.0:
          return
      scale = config.PHEROMONE_GRID_DOWNSCALE
      # build a small RGBA array, then scale up
      h, w = ph.shape
      small = np.zeros((h, w, 4), dtype=np.uint8)
      v = np.clip(ph * 0.6, 0, 80).astype(np.uint8)  # alpha
      small[:, :, 0] = 80   # cyan-ish R
      small[:, :, 1] = 150  # G
      small[:, :, 2] = 220  # B
      small[:, :, 3] = v
      try:
          small_surf = pygame.image.frombuffer(small.tobytes(), (w, h), "RGBA")
          big = pygame.transform.smoothscale(
              small_surf, (w * scale, h * scale)
          )
          self.world_surf.blit(big, (0, 0))
      except Exception:
          pass

  # ============================================================
  # Plants
  # ============================================================
  def _draw_plants(self) -> None:
      for p in self.world.plants:
          grow = p.grow
          pulse = 0.5 + 0.5 * math.sin(p.pulse)
          if grow < 1.0:
              # sapling: small dim
              r = 2 + int(grow * 3)
              col = _lerp_color((90, 130, 100), config.PLANT_CORE, grow)
              gfxdraw.filled_circle(self.world_surf, int(p.x), int(p.y), r, col)
              gfxdraw.aacircle(self.world_surf, int(p.x), int(p.y), r, col)
          else:
              r_glow = 7 + int(pulse * 2)
              gfxdraw.filled_circle(
                  self.glow_surf, int(p.x), int(p.y), r_glow + 4, (*config.PLANT_GLOW, 50)
              )
              gfxdraw.filled_circle(
                  self.glow_surf, int(p.x), int(p.y), r_glow + 1, (*config.PLANT_GLOW, 90)
              )
              gfxdraw.aacircle(self.world_surf, int(p.x), int(p.y), 3, config.PLANT_CORE)
              gfxdraw.filled_circle(self.world_surf, int(p.x), int(p.y), 2, config.PLANT_CORE)

  # ============================================================
  # Corpses
  # ============================================================
  def _draw_corpses(self) -> None:
      for c in self.world.corpses:
          fade = c.fade
          pulse = 0.5 + 0.5 * math.sin(c.pulse)
          r_glow = 6 + int(pulse * 2)
          alpha_glow = int(70 * fade)
          gfxdraw.filled_circle(
              self.glow_surf, int(c.x), int(c.y), r_glow + 3,
              (*config.CORPSE_GLOW, alpha_glow),
          )
          core = (
              int(config.CORPSE_CORE[0] * (0.4 + 0.6 * fade)),
              int(config.CORPSE_CORE[1] * (0.4 + 0.6 * fade)),
              int(config.CORPSE_CORE[2] * (0.4 + 0.6 * fade)),
          )
          gfxdraw.filled_circle(self.world_surf, int(c.x), int(c.y), 4, core)
          gfxdraw.aacircle(self.world_surf, int(c.x), int(c.y), 4, core)

  # ============================================================
  # Bots
  # ============================================================
  def _draw_bots(self) -> None:
      for b in self.world.bots:
          if not b.alive:
              continue
          self._draw_bot(b)

  def _draw_bot(self, b: Bot) -> None:
      # trail
      if len(b.trail) > 1:
          pts = list(b.trail)
          for i in range(1, len(pts)):
              a, p = pts[i - 1], pts[i]
              t = i / len(pts)
              alpha = int(40 * t)
              col = (*b.color, alpha)
              pygame.draw.line(self.glow_surf, col, a, p, 2)

      # glow ring proportional to energy
      energy_ratio = max(0.0, min(b.energy / config.BOT_REPRO_THRESHOLD, 1.0))
      r = b.radius
      glow_radius = int(r + 6 + energy_ratio * 4)
      gfxdraw.filled_circle(
          self.glow_surf, int(b.x), int(b.y), glow_radius,
          (*b.color, 40),
      )
      gfxdraw.filled_circle(
          self.glow_surf, int(b.x), int(b.y), glow_radius - 3,
          (*b.color, 80),
      )

      # body shape differs by species
      cx, cy = b.x, b.y
      h = b.heading

      if b.species == Bot.HERBIVORE:
          # smooth triangle, slightly elongated
          front = (cx + math.cos(h) * (r * 1.5), cy + math.sin(h) * (r * 1.5))
          left  = (cx + math.cos(h + 2.5) * r,   cy + math.sin(h + 2.5) * r)
          right = (cx + math.cos(h - 2.5) * r,   cy + math.sin(h - 2.5) * r)
          pts = [
              (int(front[0]), int(front[1])),
              (int(left[0]),  int(left[1])),
              (int(right[0]), int(right[1])),
          ]
          gfxdraw.filled_polygon(self.world_surf, pts, b.color)
          gfxdraw.aapolygon(self.world_surf, pts, (255, 255, 255))
      else:
          # carnivore: sharper, with side fangs
          tip   = (cx + math.cos(h) * (r * 1.8),         cy + math.sin(h) * (r * 1.8))
          back_l= (cx + math.cos(h + 2.7) * (r * 1.1),   cy + math.sin(h + 2.7) * (r * 1.1))
          back_r= (cx + math.cos(h - 2.7) * (r * 1.1),   cy + math.sin(h - 2.7) * (r * 1.1))
          mid_l = (cx + math.cos(h + 1.8) * (r * 0.7),   cy + math.sin(h + 1.8) * (r * 0.7))
          mid_r = (cx + math.cos(h - 1.8) * (r * 0.7),   cy + math.sin(h - 1.8) * (r * 0.7))
          pts = [
              (int(tip[0]),    int(tip[1])),
              (int(mid_l[0]),  int(mid_l[1])),
              (int(back_l[0]), int(back_l[1])),
              (int(back_r[0]), int(back_r[1])),
              (int(mid_r[0]),  int(mid_r[1])),
          ]
          gfxdraw.filled_polygon(self.world_surf, pts, b.color)
          gfxdraw.aapolygon(self.world_surf, pts, (255, 220, 220))

  # ============================================================
  # Selection overlay
  # ============================================================
  def _draw_selection_overlay(self, b: Bot) -> None:
      r = b.radius
      for i in range(config.GLOW_LAYERS):
          rr = int(r + 10 + i * 4)
          alpha = 150 - i * 40
          gfxdraw.aacircle(self.world_surf, int(b.x), int(b.y), rr, (*config.ACCENT_CYAN, alpha))
      gfxdraw.aacircle(self.world_surf, int(b.x), int(b.y), int(r + 14), config.ACCENT_CYAN)

      # vision rays (translucent)
      if b.nearest_plant_pos is not None:
          self._dashed_line(self.world_surf, (b.x, b.y), b.nearest_plant_pos,
                            config.ACCENT_GREEN, alpha=130)
      if b.nearest_bot_pos is not None:
          self._dashed_line(self.world_surf, (b.x, b.y), b.nearest_bot_pos,
                            config.ACCENT_MAGENTA, alpha=130)
      if b.nearest_corpse_pos is not None:
          self._dashed_line(self.world_surf, (b.x, b.y), b.nearest_corpse_pos,
                            config.ACCENT_ORANGE, alpha=130)

      # heading indicator
      hx = b.x + math.cos(b.heading) * (r + 22)
      hy = b.y + math.sin(b.heading) * (r + 22)
      pygame.draw.line(self.world_surf, (*config.ACCENT_CYAN, 200), (b.x, b.y), (hx, hy), 1)

  def _dashed_line(self, surf, p1, p2, color, alpha=160, dash=8, gap=6) -> None:
      x1, y1 = p1
      x2, y2 = p2
      dx, dy = x2 - x1, y2 - y1
      dist = math.hypot(dx, dy)
      if dist < 1e-3:
          return
      nx, ny = dx / dist, dy / dist
      d = 0.0
      while d < dist:
          sx, sy = x1 + nx * d, y1 + ny * d
          ex_ = x1 + nx * min(d + dash, dist)
          ey_ = y1 + ny * min(d + dash, dist)
          pygame.draw.line(surf, (*color, alpha), (sx, sy), (ex_, ey_), 1)
          d += dash + gap

  # ============================================================
  # Topbar
  # ============================================================
  def _draw_topbar(self, paused: bool) -> None:
      bar = pygame.Surface((config.WORLD_WIDTH, 30), pygame.SRCALPHA)
      bar.fill((0, 0, 0, 110))
      self.screen.blit(bar, (0, 0))
      w = self.world
      info = (
          f"🌿 {len(w.plants):3d}  "
          f"🟢 herb {w.herbivore_count:3d}  "
          f"🔴 carn {w.carnivore_count:2d}  "
          f"💀 corpse {len(w.corpses):2d}  "
          f"gen {w.max_generation:3d}  "
          f"t {w.elapsed:6.1f}s"
      )
      surf = self.font_sm.render(info, True, config.TEXT_PRIMARY)
      self.screen.blit(surf, (12, 7))
      # day phase
      phase_lbl = "🌙 night" if w.is_night else "☀ day"
      psurf = self.font_sm.render(phase_lbl, True, config.ACCENT_YELLOW if not w.is_night else config.ACCENT_CYAN)
      self.screen.blit(psurf, (config.WORLD_WIDTH - psurf.get_width() - 90, 7))
      if paused:
          psurf2 = self.font_md.render("PAUSED", True, config.ACCENT_YELLOW)
          self.screen.blit(psurf2, (config.WORLD_WIDTH - psurf2.get_width() - 12, 4))

  # ============================================================
  # Sidebar
  # ============================================================
  def _draw_sidebar(self, fps: float, paused: bool) -> None:
      x0 = config.WORLD_WIDTH
      panel = pygame.Surface((config.SIDEBAR_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
      panel.fill(config.SIDEBAR_BG)
      self.screen.blit(panel, (x0, 0))
      pygame.draw.line(self.screen, config.PANEL_BORDER, (x0, 0), (x0, config.SCREEN_HEIGHT), 1)

      y = 14
      self.screen.blit(self.font_lg.render("DIGITAL EVOLUTION", True, config.ACCENT_CYAN), (x0 + 14, y))
      y += 26
      self.screen.blit(self.font_xs.render("a living neon ecosystem", True, config.TEXT_DIM), (x0 + 14, y))
      y += 18

      # controls
      for line in [
          "[LMB]   Select creature",
          "[SPACE] Pause / resume",
          "[R]     Reset world",
          "[G]     Toggle grid",
          "[ESC]   Quit",
      ]:
          self.screen.blit(self.font_sm.render(line, True, config.TEXT_DIM), (x0 + 14, y))
          y += 16
      y += 6
      pygame.draw.line(self.screen, config.PANEL_BORDER, (x0 + 12, y), (x0 + config.SIDEBAR_WIDTH - 12, y))
      y += 10

      # world stats
      self.screen.blit(self.font_md.render("WORLD", True, config.ACCENT_MAGENTA), (x0 + 14, y))
      y += 20
      w = self.world
      stats = [
          ("FPS",        f"{fps:5.1f}"),
          ("Plants",     f"{len(w.plants)}"),
          ("Herbivores", f"{w.herbivore_count}"),
          ("Carnivores", f"{w.carnivore_count}"),
          ("Corpses",    f"{len(w.corpses)}"),
          ("Max gen",    f"{w.max_generation}"),
          ("Births",     f"{w.births_total}"),
          ("Deaths",     f"{w.deaths_total}"),
          ("Time",       f"{w.elapsed:6.1f}s"),
      ]
      for label, value in stats:
          self.screen.blit(self.font_sm.render(f"{label:<11} {value}", True, config.TEXT_PRIMARY), (x0 + 14, y))
          y += 16

      y += 6
      # mini population graph
      self._draw_pop_graph(x0 + 14, y, config.SIDEBAR_WIDTH - 28, 70)
      y += 78
      pygame.draw.line(self.screen, config.PANEL_BORDER, (x0 + 12, y), (x0 + config.SIDEBAR_WIDTH - 12, y))
      y += 10

      # observation
      self.screen.blit(self.font_md.render("OBSERVATION", True, config.ACCENT_GREEN), (x0 + 14, y))
      y += 20
      b = self.selected_bot
      if b is None or not b.alive:
          self.screen.blit(self.font_sm.render("Click a creature.", True, config.TEXT_DIM), (x0 + 14, y))
          return

      species_label = "🟢 Herbivore" if b.species == Bot.HERBIVORE else "🔴 Carnivore"
      self.screen.blit(self.font_sm.render(species_label, True, config.TEXT_PRIMARY), (x0 + 14, y))
      y += 18

      pygame.draw.rect(self.screen, b.color, (x0 + 14, y, 18, 18), border_radius=4)
      pygame.draw.rect(self.screen, (255, 255, 255), (x0 + 14, y, 18, 18), width=1, border_radius=4)
      self.screen.blit(self.font_sm.render(f"DNA {b.color}", True, config.TEXT_PRIMARY), (x0 + 38, y + 2))
      y += 24

      rows = [
          ("Gen",      f"{b.generation}"),
          ("Age",      f"{b.age:6.1f}s"),
          ("Size",     f"{b.traits.size:.2f}"),
          ("Speed",    f"{(b.vx**2 + b.vy**2) ** 0.5:6.1f}"),
          ("Max spd",  f"{b.max_speed:6.1f}"),
          ("Vision",   f"{b.vision:6.0f}"),
          ("Plants",   f"{b.plants_eaten}"),
          ("Kills",    f"{b.kills}"),
          ("Births",   f"{b.births}"),
      ]
      for label, value in rows:
          self.screen.blit(self.font_sm.render(f"{label:<8} {value}", True, config.TEXT_PRIMARY), (x0 + 14, y))
          y += 15
      y += 4

      # energy bar
      self.screen.blit(self.font_sm.render("Energy", True, config.TEXT_DIM), (x0 + 14, y))
      y += 16
      bar_x = x0 + 14
      bar_w = config.SIDEBAR_WIDTH - 28
      bar_h = 14
      pygame.draw.rect(self.screen, (40, 44, 60), (bar_x, y, bar_w, bar_h), border_radius=4)
      ratio = max(0.0, min(b.energy / config.BOT_REPRO_THRESHOLD, 1.0))
      if ratio < 0.5:
          col = _lerp_color(config.ACCENT_RED, config.ACCENT_YELLOW, ratio * 2.0)
      else:
          col = _lerp_color(config.ACCENT_YELLOW, config.ACCENT_GREEN, (ratio - 0.5) * 2.0)
      pygame.draw.rect(self.screen, col, (bar_x, y, int(bar_w * ratio), bar_h), border_radius=4)
      pygame.draw.rect(self.screen, config.PANEL_BORDER, (bar_x, y, bar_w, bar_h), width=1, border_radius=4)
      self.screen.blit(
          self.font_xs.render(f"{b.energy:5.1f} / {config.BOT_REPRO_THRESHOLD:.0f}", True, config.TEXT_PRIMARY),
          (bar_x + bar_w - 70, y - 1),
      )
      y += 22

      # brain outputs
      self.screen.blit(self.font_md.render("BRAIN OUTPUT", True, config.ACCENT_CYAN), (x0 + 14, y))
      y += 18
      names = ("Accel", "Turn ", "Act  ", "Repro")
      for i, name in enumerate(names):
          v = float(b.last_outputs[i])
          self.screen.blit(self.font_sm.render(f"{name} {v:+.2f}", True, config.TEXT_PRIMARY), (x0 + 14, y))
          mbar_x = x0 + 110
          mbar_w = config.SIDEBAR_WIDTH - 130
          mid = mbar_x + mbar_w // 2
          pygame.draw.line(self.screen, config.PANEL_BORDER, (mbar_x, y + 8), (mbar_x + mbar_w, y + 8), 1)
          pygame.draw.line(self.screen, config.TEXT_DIM, (mid, y + 4), (mid, y + 12), 1)
          end_x = int(mid + v * (mbar_w // 2))
          color = config.ACCENT_GREEN if v >= 0 else config.ACCENT_RED
          pygame.draw.line(self.screen, color, (mid, y + 8), (end_x, y + 8), 3)
          y += 16

  # ============================================================
  # Population mini graph
  # ============================================================
  def _draw_pop_graph(self, x: int, y: int, w: int, h: int) -> None:
      pygame.draw.rect(self.screen, (20, 24, 38), (x, y, w, h), border_radius=4)
      pygame.draw.rect(self.screen, config.PANEL_BORDER, (x, y, w, h), width=1, border_radius=4)
      herb = list(self.world.history_herb)
      carn = list(self.world.history_carn)
      plants = list(self.world.history_plants)
      if not herb:
          return
      max_v = max(
          max(herb) if herb else 1,
          max(carn) if carn else 1,
          max(plants) if plants else 1,
          1,
      )

      def plot(series, color, alpha=255):
          if len(series) < 2:
              return
          pts = []
          for i, v in enumerate(series):
              px = x + int(i * (w - 4) / max(1, len(series) - 1)) + 2
              py = y + h - 2 - int((v / max_v) * (h - 4))
              pts.append((px, py))
          if len(pts) >= 2:
              pygame.draw.aalines(self.screen, color, False, pts)

      plot(plants, config.ACCENT_GREEN)
      plot(herb, (200, 255, 220))
      plot(carn, config.ACCENT_RED)

      # legend
      self.screen.blit(self.font_xs.render("plants", True, config.ACCENT_GREEN), (x + 4, y + 2))
      self.screen.blit(self.font_xs.render("herb",   True, (200, 255, 220)), (x + 48, y + 2))
      self.screen.blit(self.font_xs.render("carn",   True, config.ACCENT_RED), (x + 84, y + 2))
