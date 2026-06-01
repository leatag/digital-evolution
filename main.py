"""
Digital Evolution — entry point.

Run: python main.py
Requires: pygame, numpy  (see requirements.txt)
"""
from __future__ import annotations

import sys

import pygame

import config
from engine import World
from ui import UI


def main() -> None:
pygame.init()
pygame.display.set_caption("Digital Evolution — a living neon ecosystem")
screen = pygame.display.set_mode(
    (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
)
clock = pygame.time.Clock()

world = World()
ui = UI(screen, world)

paused = False
running = True
while running:
    # cap dt so a long stall doesn't explode the sim
    dt_raw_ms = clock.tick(config.TARGET_FPS)
    dt = min(dt_raw_ms / 1000.0, 1.0 / 30.0)
    fps = clock.get_fps()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_r:
                world.reset()
                ui.selected_bot = None
            elif event.key == pygame.K_g:
                config.SHOW_GRID = not config.SHOW_GRID
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            ui.handle_click(event.pos)

    if not paused:
        world.update(dt)

    ui.draw(fps, paused)
    pygame.display.flip()

pygame.quit()
sys.exit(0)


if __name__ == "__main__":
main()
