"""
Rendering & UI: neon visuals, glowing bots, vision rays, sidebar HUD.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

import pygame
from pygame import gfxdraw

import config
from entities import Bot


def _lerp_color(c1, c2, t: float):
return (
    int(c1[0] + (c2[0] - c1[0]) * t),
    int(c1[1] + (c2[1] - c1[1]) * t),
    int(c1[2] + (c2[2] - c1[2]) * t),
)


class UI:
def __init__(self, screen: pygame.Surface, world) -> None:
    self.screen = screen
    self.world = world
    self.selected_bot: Optional[Bot] = None

    # Fonts
    self.font_xs = pygame.font.SysFont("consolas", 12)
    self.font_sm = pygame.font.SysFont("consolas", 14)
    self.font_md = pygame.font.SysFont("consolas", 16, bold=True)
    self.font_lg = pygame.font.SysFont("consolas", 22, bold=True)

    # Pre-rendered world surface (for glow blending)
    self.world_surf = pygame.Surface(
        (config.WORLD_WIDTH, config.WORLD_HEIGHT), pygame.SRCALPHA
    )
    self.glow_surf = pygame.Surface(
        (config.WORLD_WIDTH, config.WORLD_HEIGHT), pygame.SRCALPHA
    )

# ---- Input ----
def handle_click(self, pos) -> None:
    x, y = pos
    if x >= config.WORLD_WIDTH:
        return  # clicked sidebar
    clicked = self.world.bot_at(x, y)
    if clicked is None and self.selected_bot is not None:
        # tolerate near-misses
        clicked = self.world.bot_at(x, y, radius_mult=4.0)
    self.selected_bot = clicked

# ---- Drawing ----
def draw(self, fps: float, paused: bool) -> None:
    self.screen.fill(config.BG_COLOR)
    self.world_surf.fill((0, 0, 0, 0))
    self.glow_surf.fill((0, 0, 0, 0))

    if config.SHOW_GRID:
        self._draw_grid()

    self._draw_food()
    self._draw_bots()

    if self.selected_bot is not None and self.selected_bot.alive:
        self._draw_selection_overlay(self.selected_bot)
    elif self.selected_bot is not None and not self.selected_bot.alive:
        self.selected_bot = None

    # Composite world (glow under, sharp on top)
    self.screen.blit(self.glow_surf, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)
    self.screen.blit(self.world_surf, (0, 0))

    self._draw_sidebar(fps, paused)
    self._draw_topbar(paused)

# ---- Grid (optional) ----
def _draw_grid(self) -> None:
    for x in range(0, config.WORLD_WIDTH, config.CELL_SIZE):
        pygame.draw.line(self.world_surf, config.GRID_COLOR, (x, 0), (x, config.WORLD_HEIGHT))
    for y in range(0, config.WORLD_HEIGHT, config.CELL_SIZE):
        pygame.draw.line(self.world_surf, config.GRID_COLOR, (0, y), (config.WORLD_WIDTH, y))

# ---- Food ----
def _draw_food(self) -> None:
    for f in self.world.foods:
        pulse = 0.5 + 0.5 * math.sin(f.pulse)
        r_outer = 7 + int(pulse * 2)
        # outer glow
        glow_color = (*config.FOOD_GLOW, 60)
        gfxdraw.filled_circle(self.glow_surf, int(f.x), int(f.y), r_outer + 4, glow_color)
        gfxdraw.filled_circle(self.glow_surf, int(f.x), int(f.y), r_outer + 1, (*config.FOOD_GLOW, 100))
        # core
        gfxdraw.aacircle(self.world_surf, int(f.x), int(f.y), 3, config.FOOD_CORE)
        gfxdraw.filled_circle(self.world_surf, int(f.x), int(f.y), 2, config.FOOD_CORE)

# ---- Bots ----
def _draw_bots(self) -> None:
    for b in self.world.bots:
        if not b.alive:
            continue
        self._draw_bot(b)

def _draw_bot(self, b: Bot) -> None:
    # Trail
    if len(b.trail) > 1:
        for i in range(1, len(b.trail)):
            a, p = b.trail[i - 1], b.trail[i]
            t = i / len(b.trail)
            alpha = int(40 * t)
            col = (*b.color, alpha)
            pygame.draw.line(self.glow_surf, col, a, p, 2)

    # Glow ring (energy)
    energy_ratio = max(0.0, min(b.energy / config.BOT_REPRO_THRESHOLD, 1.0))
    glow_radius = int(config.BOT_RADIUS + 6 + energy_ratio * 4)
    glow_alpha = int(60 + 80 * energy_ratio)
    gfxdraw.filled_circle(
        self.glow_surf, int(b.x), int(b.y), glow_radius, (*b.color, glow_alpha // 3)
    )
    gfxdraw.filled_circle(
        self.glow_surf, int(b.x), int(b.y), glow_radius - 3, (*b.color, glow_alpha // 2)
    )

    # Body as a sleek triangle pointing along heading
    cx, cy = b.x, b.y
    r = config.BOT_RADIUS + 2
    h = b.heading
    p1 = (cx + math.cos(h) * r * 1.4, cy + math.sin(h) * r * 1.4)
    p2 = (cx + math.cos(h + 2.4) * r, cy + math.sin(h + 2.4) * r)
    p3 = (cx + math.cos(h - 2.4) * r, cy + math.sin(h - 2.4) * r)
    pts = [(int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (int(p3[0]), int(p3[1]))]
    # filled body
    gfxdraw.filled_polygon(self.world_surf, pts, b.color)
    gfxdraw.aapolygon(self.world_surf, pts, (255, 255, 255))

# ---- Selection overlay ----
def _draw_selection_overlay(self, b: Bot) -> None:
    # Ring
    for i in range(config.GLOW_LAYERS):
        r = config.BOT_RADIUS + 10 + i * 4
        alpha = 140 - i * 40
        gfxdraw.aacircle(self.world_surf, int(b.x), int(b.y), r, (*config.ACCENT_CYAN, alpha))
    # crosshair tick
    gfxdraw.aacircle(self.world_surf, int(b.x), int(b.y), int(config.BOT_RADIUS + 14), config.ACCENT_CYAN)

    # Vision rays
    if b.nearest_food_pos is not None:
        self._aa_dashed_line(self.world_surf, (b.x, b.y), b.nearest_food_pos, config.ACCENT_GREEN, alpha=130)
    if b.nearest_bot_pos is not None:
        self._aa_dashed_line(self.world_surf, (b.x, b.y), b.nearest_bot_pos, config.ACCENT_MAGENTA, alpha=130)

    # Heading indicator
    hx = b.x + math.cos(b.heading) * 28
    hy = b.y + math.sin(b.heading) * 28
    pygame.draw.line(self.world_surf, (*config.ACCENT_CYAN, 180), (b.x, b.y), (hx, hy), 1)

def _aa_dashed_line(self, surf, p1, p2, color, alpha=160, dash=8, gap=6) -> None:
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
        ex, ey = x1 + nx * min(d + dash, dist), y1 + ny * min(d + dash, dist)
        pygame.draw.line(surf, (*color, alpha), (sx, sy), (ex, ey), 1)
        d += dash + gap

# ---- HUD ----
def _draw_topbar(self, paused: bool) -> None:
    bar = pygame.Surface((config.WORLD_WIDTH, 28), pygame.SRCALPHA)
    bar.fill((0, 0, 0, 100))
    self.screen.blit(bar, (0, 0))
    info = f"Bots: {len(self.world.bots):3d}   Food: {len(self.world.foods):3d}   Gen max: {self.world.max_generation:3d}   t={self.world.elapsed:6.1f}s"
    surf = self.font_sm.render(info, True, config.TEXT_PRIMARY)
    self.screen.blit(surf, (12, 6))
    if paused:
        psurf = self.font_md.render("PAUSED  (SPACE to resume)", True, config.ACCENT_YELLOW)
        self.screen.blit(psurf, (config.WORLD_WIDTH - psurf.get_width() - 12, 4))

def _draw_sidebar(self, fps: float, paused: bool) -> None:
    x0 = config.WORLD_WIDTH
    panel = pygame.Surface((config.SIDEBAR_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
    panel.fill(config.SIDEBAR_BG)
    self.screen.blit(panel, (x0, 0))
    pygame.draw.line(self.screen, config.PANEL_BORDER, (x0, 0), (x0, config.SCREEN_HEIGHT), 1)

    y = 16
    title = self.font_lg.render("DIGITAL EVOLUTION", True, config.ACCENT_CYAN)
    self.screen.blit(title, (x0 + 14, y))
    y += 30
    subtitle = self.font_xs.render("neon alife // numpy brains", True, config.TEXT_DIM)
    self.screen.blit(subtitle, (x0 + 14, y))
    y += 22

    # Controls
    for line in [
        "[LMB]   Select bot",
        "[SPACE] Pause / Resume",
        "[R]     Reset world",
        "[ESC]   Quit",
    ]:
        self.screen.blit(self.font_sm.render(line, True, config.TEXT_DIM), (x0 + 14, y))
        y += 18
    y += 8
    pygame.draw.line(
        self.screen, config.PANEL_BORDER, (x0 + 12, y), (x0 + config.SIDEBAR_WIDTH - 12, y)
    )
    y += 10

    # World stats
    self.screen.blit(self.font_md.render("WORLD", True, config.ACCENT_MAGENTA), (x0 + 14, y))
    y += 22
    self.screen.blit(
        self.font_sm.render(f"FPS .......... {fps:5.1f}", True, config.TEXT_PRIMARY),
        (x0 + 14, y),
    )
    y += 18
    alive = sum(1 for b in self.world.bots if b.alive)
    self.screen.blit(
        self.font_sm.render(f"Population ... {alive}", True, config.TEXT_PRIMARY),
        (x0 + 14, y),
    )
    y += 18
    self.screen.blit(
        self.font_sm.render(f"Food ......... {len(self.world.foods)}", True, config.TEXT_PRIMARY),
        (x0 + 14, y),
    )
    y += 18
    self.screen.blit(
        self.font_sm.render(f"Max gen ...... {self.world.max_generation}", True, config.TEXT_PRIMARY),
        (x0 + 14, y),
    )
    y += 18
    self.screen.blit(
        self.font_sm.render(f"Time ......... {self.world.elapsed:6.1f}s", True, config.TEXT_PRIMARY),
        (x0 + 14, y),
    )
    y += 24
    pygame.draw.line(
        self.screen, config.PANEL_BORDER, (x0 + 12, y), (x0 + config.SIDEBAR_WIDTH - 12, y)
    )
    y += 10

    # Selected bot
    self.screen.blit(self.font_md.render("OBSERVATION", True, config.ACCENT_GREEN), (x0 + 14, y))
    y += 24
    b = self.selected_bot
    if b is None or not b.alive:
        self.screen.blit(
            self.font_sm.render("Click a creature.", True, config.TEXT_DIM), (x0 + 14, y)
        )
        return

    # Color swatch
    pygame.draw.rect(self.screen, b.color, (x0 + 14, y, 18, 18), border_radius=4)
    pygame.draw.rect(self.screen, (255, 255, 255), (x0 + 14, y, 18, 18), width=1, border_radius=4)
    self.screen.blit(
        self.font_sm.render(f"DNA color {b.color}", True, config.TEXT_PRIMARY),
        (x0 + 40, y + 2),
    )
    y += 28

    for label, value in (
        ("Generation", f"{b.generation}"),
        ("Age",        f"{b.age:6.1f}s"),
        ("Food eaten", f"{b.food_eaten}"),
        ("Kills",      f"{b.kills}"),
        ("Speed",      f"{(b.vx**2 + b.vy**2) ** 0.5:6.1f}"),
        ("Heading",    f"{(b.heading * 180.0 / math.pi):6.1f}°"),
    ):
        line = f"{label:<11}  {value}"
        self.screen.blit(self.font_sm.render(line, True, config.TEXT_PRIMARY), (x0 + 14, y))
        y += 18
    y += 6

    # Energy bar (gradient red -> yellow -> green)
    self.screen.blit(self.font_sm.render("Energy", True, config.TEXT_DIM), (x0 + 14, y))
    y += 18
    bar_w = config.SIDEBAR_WIDTH - 28
    bar_h = 14
    bar_x = x0 + 14
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
        (bar_x + bar_w + 4 - 70, y - 1),
    )
    y += 26

    # Brain readouts
    self.screen.blit(self.font_md.render("BRAIN OUTPUTS", True, config.ACCENT_CYAN), (x0 + 14, y))
    y += 22
    names = ("Accel", "Turn ", "Act  ")
    for i, name in enumerate(names):
        v = float(b.last_outputs[i])
        line = f"{name}  {v:+.3f}"
        self.screen.blit(self.font_sm.render(line, True, config.TEXT_PRIMARY), (x0 + 14, y))
        # mini bar
        mbar_x = x0 + 110
        mbar_w = config.SIDEBAR_WIDTH - 130
        mid = mbar_x + mbar_w // 2
        pygame.draw.line(self.screen, config.PANEL_BORDER, (mbar_x, y + 8), (mbar_x + mbar_w, y + 8), 1)
        pygame.draw.line(self.screen, config.TEXT_DIM, (mid, y + 4), (mid, y + 12), 1)
        end_x = int(mid + v * (mbar_w // 2))
        color = config.ACCENT_GREEN if v >= 0 else config.ACCENT_RED
        pygame.draw.line(self.screen, color, (mid, y + 8), (end_x, y + 8), 3)
        y += 20
    y += 6

    self.screen.blit(self.font_md.render("BRAIN INPUTS", True, config.ACCENT_MAGENTA), (x0 + 14, y))
    y += 22
    in_names = ("FoodX", "FoodY", "BotD ", "Energ", "Age  ", "Hsin ")
    for i, name in enumerate(in_names):
        v = float(b.last_inputs[i])
        line = f"{name}  {v:+.3f}"
        self.screen.blit(self.font_xs.render(line, True, config.TEXT_PRIMARY), (x0 + 14, y))
        y += 14
