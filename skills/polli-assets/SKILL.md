---
name: polli-assets
description: Generate game assets with pollinations (gen.pollinations.ai) through the `um polli` CLI. Covers sprites and images, consistent variants and animation frames, background removal, upscaling, image-to-3D models (GLB), sound effects, music and voice lines. Image and 3D are free-tier by default; audio and video bill the paid wallet and are gated behind --yes-spend. Use whenever a mod needs new art, audio or 3D models, or the user mentions pollinations, generating sprites, textures, models, SFX or music for a game.
---

# Game assets with pollinations

pollinations (`gen.pollinations.ai`) runs text→image, image→3D, TTS, music and video models behind one key.
Use it whenever the mod needs something that doesn't exist yet: a weapon sprite, a boss, a unit rendered
from 16 angles, a tileable floor, a laser sound, boss music, a voiced line.

**Image and 3D are the defaults and run on the free tier** (no paid pollen). **Audio and video bill the paid
wallet**, so they are OFF by default and need an explicit `--yes-spend` plus a `--max-pollen` cap.

## Setup (check once per session)
- **Key.** `um polli` reads `POLLINATIONS_API_KEY` from the env, else the `pollinations` entry in the
  opencode `auth.json` (`~/.local/share/opencode/auth.json`, or `%APPDATA%\opencode\auth.json`). Never write
  the key into mod files; `um publish check` flags leaked keys.
- **Balance.** `um polli balance` shows pollen (free tier + paid). Budget is per-key, not per-wallet — a key
  with a low budget cap 402s even when the wallet has pollen.
- **Models.** `um polli models [--category image|3d|audio|video]` lists what is live. The catalog moves fast.

## Which interface
- **Anything that must land on disk** (every game asset): `um polli <recipe>`. It uploads local inputs where
  the API needs a URL, downloads the output and appends the model, prompt, seed and file to
  `<out>/polli_manifest.jsonl`, so every asset can be traced and regenerated.
- Free image processing (`rmbg`, `upscale`) needs no pollen and no key at all.

## Recipes (`um polli <recipe> --help` for options; `--model` overrides the model; `--set k=v` passes extras)

| Asset | Command | Default model | Cost |
|---|---|---|---|
| Sprite / icon | `um polli sprite "<subject, view, style>" --name x` | `openai/gpt-image-2` | free tier |
| Concept art, key art, backgrounds | `um polli image "<prompt>" --aspect 16:9` | `openai/gpt-image-2` | free tier |
| Consistent variants, extra frames, recolors | `um polli edit "<change>" --ref base.jpg` | `openai/gpt-image-2` | free tier |
| Image → textured 3D model (GLB) | `um polli 3d concept.jpg --name unit` | `microsoft/trellis-2` | free tier |
| Background removal → transparent PNG | `um polli rmbg in.jpg` | (bgeraser) | **free** |
| Upscale | `um polli upscale in.jpg` | (imgupscaler) | **free** |
| Sound effect | `um polli sfx "plasma rifle shot, punchy" --seconds 1.2 --yes-spend` | `elevenlabs/eleven-text-to-sound-v2` | **PAID** |
| Music | `um polli music "tense boss battle, chiptune, 150 bpm" --seconds 30 --yes-spend --max-pollen 0.2` | `elevenlabs/music-v2.5` | **PAID** |
| Voice line | `um polli voice "You dare challenge me?" --voice-id Adam --yes-spend` | `elevenlabs/eleven-v3` | **PAID** |
| Trailer / cutscene clip | `um polli video still.jpg "camera orbits the boss" --seconds 4 --yes-spend --max-pollen 0.5` | `bytedance/seedance-2.5` | **PAID** |

Image model aliases: `gpt-image-2` (default) and `gemini` / `gemini-3.1-flash-image` (= Nano Banana 2).
Other live image models: `google/gemini-3-pro-image`, `black-forest-labs/flux.2-pro`, `bytedance/seedream-5.0-pro`,
`qwen/qwen-image-3`, `recraft/recraft-v4.1-vector` (SVG). 3D: `microsoft/trellis-2` (default),
`hyper3d/rodin-2.5`, `nvidia/asset-harvester`.

## Spending rules (audio + video)
- **Always tell the user the rough cost before a paid batch** and let them decide.
- The gate refuses without `--yes-spend`. Add `--max-pollen <n>` so a request that costs more than you expect
  is refused before it is sent. Estimates: sfx ~0.002/s, music ~0.0025/s, video ~0.1/s of output.
- **Music duration is a trap:** the model may ignore `--seconds` and render a full ~180 s track (≈0.45 pollen).
  Set `--max-pollen` low when testing so a runaway render is refused.
- Video is the most expensive thing here and is almost never needed for a mod (only `showcase-video` trailers
  and cutscenes). Prefer stills + `um video` over generated video.

## Prompting game art that fits the game
- **Look at the game's own assets first:** pixel size, outline, palette, perspective, facing, how busy they
  are. Put that into a reusable style suffix. For Terraria: *"16-bit pixel art game sprite in the style of
  Terraria, crisp dark outline, limited palette, centered, plain flat white background, no shadow, no text"*.
- **Describe the view and orientation explicitly:** "perfectly horizontal side view with the muzzle pointing
  right" for held weapons, "seen from the side facing left" for enemies, "pointing straight down" for a
  falling bomb. Engines have conventions (Terraria items point right, NPCs face left) and fixing orientation
  afterwards costs quality.
- **Backgrounds:** pollinations returns JPEG, so there is no true alpha — ask for a flat, uniform background
  (white or a single colour), then `um polli rmbg` gives you the transparent PNG. Avoid gradients, scenery and
  ground shadows, or the cutout will keep them.
- **Consistency across a set:** generate one hero image, then derive the rest with `edit` and the hero as
  `--ref` ("same robot, now firing, muzzle flash"). Don't ask one prompt for a whole sprite sheet; grids come
  out uneven.
- **Many angles or frames of the same object:** go 3D. Take the concept, run `um polli 3d`, then `um render3d`
  from the game's camera (asset-pipeline skill). That's how the AoE2 robotaxi got 16 consistent headings.
- **No text or logos** in art unless wanted: models love to add them.

## Audio for engines
- The SFX and music endpoints return MP3. Convert to what the engine wants:
  - `ffmpeg -i x.mp3 -ar 44100 x.wav` (XNA/tModLoader, most engines);
  - `ffmpeg -i x.mp3 -c:a libvorbis -q:a 5 x.ogg` (Minecraft, Godot, Unity);
  - trim silence first: `-af silenceremove=start_periods=1:start_threshold=-50dB`.
- Keep SFX short (0.2-2 s) and normalize loudness (`-af loudnorm=I=-16`) so they sit with the game's own
  sounds.

## Reproducibility
- Keep `polli_manifest.jsonl` with the assets; it records prompts, models, seeds and files.
- In the mod's README, credit that assets were generated with pollinations and name the models.
