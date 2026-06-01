# Digital Evolution 🧬

A beautiful neon **ALife (Artificial Life) ecosystem simulation** built in pure **Python + Pygame + NumPy**. No ML frameworks — every brain is a tiny `numpy` matrix.

Bots evolve via asexual reproduction with mutation. Their RGB color is mapped directly from their neural-network DNA, so evolving families share neon hues that drift across generations.

## ✨ Features

- **Tiny numpy brain** per bot: 6 → 8 → 3 feed-forward NN, `tanh` activations, weights = DNA.
- **Asexual reproduction** with configurable mutation rate and strength.
- **Spatial hashing** (3×3 cell neighborhood) for stable 60 FPS even with hundreds of bots.
- **DNA-mapped neon colors** — evolutionary lineages are visually trackable.
- **Beautiful neon HUD**:
- Sleek triangle bodies with anti-aliased polygons.
- Glowing energy rings & faint motion trails.
- Glowing food orbs that pulse.
- **Interactive observation mode**:
- Click any bot to track it.
- Translucent vision rays show exactly what its brain is currently sensing.
- Live sidebar: generation, age, energy bar, kills, food, brain inputs/outputs.

## 🚀 Quick start

```bash
pip install pygame numpy
python main.py
```

That's it. No data files, no checkpoints.

## 🎮 Controls

| Key / Mouse | Action |
|---|---|
| **LMB** | Select a bot |
| **SPACE** | Pause / resume |
| **R** | Reset the world |
| **ESC** | Quit |

## 🧠 Architecture

```
main.py       # event loop, FPS limiter, key handling
config.py     # all tunable parameters
entities.py   # Bot + Brain (numpy NN) + Food
engine.py     # World, SpatialHash, interactions, reproduction
ui.py         # neon rendering, HUD, vision rays
```

### Brain (DNA)
A pure-numpy 2-layer NN:

```
inputs (6) ── W1 ── tanh ── hidden (8) ── W2 ── tanh ── outputs (3)
```

Inputs:
1. Δx to nearest food (normalized)
2. Δy to nearest food (normalized)
3. Distance to nearest bot (normalized)
4. Current energy (normalized)
5. Age (tanh-normalized)
6. `sin(heading)`

Outputs:
1. **Acceleration** (−1..1)
2. **Rotation** (−1..1)
3. **Action**: > 0 → eat, < −0.3 → attack

### Reproduction
When a bot's energy crosses `BOT_REPRO_THRESHOLD`, it splits into two. The child inherits the parent's `numpy` weight matrices, with each weight independently perturbed by Gaussian noise at probability `MUTATION_RATE`.

### Performance
- The world uses a uniform-grid spatial hash. Bots only check entities in their own + 8 adjacent cells.
- All vector ops use numpy floats.
- One hash rebuild per frame.

## 🎛️ Tuning

Open `config.py` and tweak:
- `INITIAL_BOT_COUNT`, `MAX_BOTS`, `MAX_FOOD`
- `MUTATION_RATE`, `MUTATION_STRENGTH`
- `BOT_VISION_RANGE`, `BOT_REPRO_THRESHOLD`
- `BG_COLOR`, accent colors

## 📜 License

MIT — see `LICENSE`.
