"""
Digital Evolution — entry point.
Initializes Pygame, sets up the world, runs the main loop.
"""
import sys
import pygame

from engine import World
from ui import UI
import config


def main() -> None:
pygame.init()
pygame.display.set_caption("Digital Evolution")

screen = pygame.display.set_mode(
    (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
    pygame.DOUBLEBUF,
)
clock = pygame.time.Clock()

world = World()
ui = UI(screen, world)

running = True
paused = False

while running:
    dt = clock.tick(config.TARGET_FPS) / 1000.0
    # cap dt so a freeze doesn't blow up the sim
    if dt > 0.1:
        dt = 0.1

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
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            ui.handle_click(event.pos)

    if not paused:
        world.update(dt)

    ui.draw(fps=clock.get_fps(), paused=paused)
    pygame.display.flip()

pygame.quit()
sys.exit(0)


if __name__ == "__main__":
main()
