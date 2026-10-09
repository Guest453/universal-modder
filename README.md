<p align="center">
  <img src="docs/media/banner.png" alt="universal-modder" width="100%">
</p>

> **Fork note:** this fork replaces **fal** with **pollinations** (`gen.pollinations.ai`). Asset
> generation is now `um polli <recipe>` (image, sprite, edit, 3d, rmbg, upscale, sfx, music, voice,
> video), and the `fal-assets` skill is now `polli-assets`. Image + 3D run on the free tier; audio +
> video bill the paid wallet and are gated behind `--yes-spend` / `--max-pollen`. The `um fal` CLI
> group was removed (the module is kept only for the offline test suite). Key comes from
> `POLLINATIONS_API_KEY` or the `pollinations` entry in the opencode `auth.json`. The bundled MCP server
> is pollinations' hosted `https://mcp.pollinations.ai` instead of fal's; in Claude Code its key comes from
> `bin/polli-mcp-headers.py` (same lookup as `um polli`, so the opencode `auth.json` is enough).

<p align="center">
  <b>Skills, tools and a shared knowledge base that let any AI coding agent mod almost any PC game you own.</b><br>
  Works with Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, OpenCode, or anything that reads <code>AGENTS.md</code>.<br>
  The agent finds the game, works out the engine and the route, reads the real code, builds the mod, makes art, 3D and sound
  with <a href="https://pollinations.ai">pollinations</a>, tests it in the running game, cuts the video, and writes down what it learned for the next agent.
</p>

<p align="center">
  <a href="#install"><img alt="any agent" src="https://img.shields.io/badge/agents-Claude%20Code%20·%20Codex%20·%20Cursor%20·%20Gemini%20·%20Copilot-B6FF3B?labelColor=0A0D12"></a>
  <a href="knowledge/INDEX.md"><img alt="knowledge base" src="https://img.shields.io/badge/knowledge%20base-field%20notes-B6FF3B?labelColor=0A0D12"></a>
  <a href="https://pollinations.ai"><img alt="assets by pollinations" src="https://img.shields.io/badge/assets-pollinations-B6FF3B?labelColor=0A0D12"></a>
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-B6FF3B?labelColor=0A0D12"></a>
</p>

<p align="center">
  <img src="docs/media/teaser.gif" alt="A tactical nuke in Terraria and robotaxis in Age of Empires II, both built with universal-modder" width="560">
</p>

## Install

Pick your agent. Each gets the same skills (Agent Skills format), the pollinations MCP server, and the `um` CLI.

| Agent | Install |
|---|---|
| **Claude Code** | `/plugin marketplace add rehan-remade/universal-modder`, then `/plugin install universal-modder@universal-modder` |
| **Codex** | `codex plugin marketplace add rehan-remade/universal-modder`, then `codex plugin add universal-modder@universal-modder` |
| **Gemini CLI** | `gemini extensions install https://github.com/rehan-remade/universal-modder` |
| **VS Code / Copilot** | Enable `chat.plugins.enabled`, run **Chat: Install Plugin From Source**, and enter this repo's URL |
| **Cursor** | Cursor Marketplace, or clone (Cursor reads `AGENTS.md` and `.cursor/mcp.json`) |
| **Skills only** (any agent) | `npx skills add https://github.com/rehan-remade/universal-modder` |
| **Anything else** | `git clone https://github.com/rehan-remade/universal-modder` and start your agent inside it |

Inside a clone, each agent finds the skills where it looks for them: `.agents/skills` (Codex and friends),
`.claude/skills`, `.gemini/skills` and `.github/skills` all link to `skills/`. Instructions are in
`AGENTS.md`, which `CLAUDE.md` and `GEMINI.md` point to. MCP config is in `.mcp.json`, `.codex/config.toml`,
`.cursor/mcp.json` and `.vscode/mcp.json`.

**The `um` CLI.** Plugin installs and clones put it on PATH. Anywhere else:
```bash
uv tool install git+https://github.com/rehan-remade/universal-modder     # or: pipx install git+...
```
**For assets,** get a [pollinations API key](https://enter.pollinations.ai/keys) (`sk_...`). It powers both
the pollinations MCP server and `um polli`:
```bash
export POLLINATIONS_API_KEY=sk_...
```
You also need Python 3.10+ and ffmpeg. `uv` is recommended. Blender is needed for 3D → sprite renders.
Windows games are driven natively or from WSL.

## Try it
> Mod Terraria: add a homing missile launcher and a tactical nuke that craters the world. Make the sprites with pollinations.

> Make a new civilization for Age of Empires II with a unique unit rendered from 3D.

> Put real Minecraft inside GTA V story mode. Minecraft's camera should follow GTA's, and its TNT should blow up GTA cars.

> What engine is `C:\Games\Foo`, and has anyone modded it before?

The agent starts with the **mod-any-game** skill and runs the same loop every time:
1. search the knowledge base;
2. recon, then pick a route;
3. set up a safe lab (saves backed up);
4. read the actual code;
5. build one working slice;
6. generate assets;
7. verify in the real game;
8. record;
9. package;
10. write a field note for the next agent.

## A knowledge base that AIs write for AIs
[`knowledge/`](knowledge/) holds **field notes**: how specific games were actually modded, decompiled and
reverse-engineered. Each note gives:
- the exact versions that worked;
- the route, and why;
- what the engine really does;
- how it was verified;
- the gotchas (symptom → cause → fix).

**Every agent that finishes a mod can open a pull request with its note**, so the next agent starts where it
left off instead of rediscovering the same traps.

```bash
um kb search "grand theft auto"                 # before you start: prior art (works outside the repo too)
um kb new --game "Hades II" --title "A new boon god" --from-scan hades --agent "Codex (gpt-6)"
um kb check knowledge/games/hades-ii/a-new-boon-god.md
um kb pr knowledge/games/hades-ii/a-new-boon-god.md --yes    # after your human says OK: branch, push, PR
```
Browse [`knowledge/INDEX.md`](knowledge/INDEX.md). Contribution rules, for humans and AIs, are in
[`CONTRIBUTING.md`](CONTRIBUTING.md): no game files, no decompiled dumps, nothing that helps cheat online,
and an honest status and verification.

## What's inside

**Skills** (`skills/`, Agent Skills format)

| Skill | What it does |
|---|---|
| `mod-any-game` | The whole loop, hard safety rules, and **12 engine playbooks**: Unity, Unreal, .NET/XNA (Terraria, Stardew, Celeste), Godot, Source 1/2, Bethesda, Minecraft, AoE2/Genie, RE Engine/FromSoft/GTA/Cyberpunk/BG3, native C++, indie engines (GameMaker, RPG Maker, Ren'Py, Paradox, Doom, HTML5, LÖVE, Java), retro decomps |
| `game-recon` | Prior field notes, engine and version, managed or native, anti-cheat, loaders, save folders, community route → `MODDING_PLAN.md` |
| `reverse-engineering` | ILSpy / Cpp2IL / Vineflower / Ghidra and IDA over MCP / Cheat Engine / Frida / RenderDoc; reverse-engineer a file format and prove it with a round trip |
| `polli-assets` | Sprites and images, consistent variants and frames, background removal, upscaling, image-to-3D, SFX, music, voice, cutscene video (audio + video gated behind `--yes-spend`) |
| `asset-pipeline` | Art → engine-exact frames: cutout, nearest-neighbour fit, palettes, sheets, team-colour masks, 3D → 8/16-heading sprites |
| `game-automation` | Launch, screenshot (GPU-safe), click/type safely, windowed mode, crash-reporter cleanup, in-game agent bridges |
| `showcase-video` | Record the window with only the game's audio, pick moments, cut a styled video from an EDL |
| `mashup-mods` | Game inside a game: content ports, passthrough mods (worked example: Minecraft × GTA V), decomps as libraries, reimplementations |
| `publish-mod` | Lint, package per platform, credits, the post |
| `share-field-notes` | Search the knowledge base, write your own note, open the PR |

**The `um` CLI** (Python). Every command has `--help` with examples.

| | |
|---|---|
| `um scan` | Find Steam/Epic/Xbox installs; fingerprint engine and version, .NET vs native, anti-cheat, installed loaders, save folders, ranked routes |
| `um polli` | `image`, `sprite`, `edit`, `3d`, `rmbg`, `upscale`, `sfx`, `music`, `voice`, `video`, `balance`, `models`. Plain REST, with a manifest of every generation |
| `um sprite` | `cutout`, `fit`, `pixelate`, `palette`, `sheet`, `slice`, `frames`, `team-mask`, `seamless`, `preview` |
| `um render3d` | GLB → sprite frames from the game's camera (`aoe2`, `iso8`, `trueiso`, `topdown`, `side`, `turntable`) with Blender |
| `um win` | `shot`, `record` (gfxcapture + process-loopback audio), `drive` (input that only reaches the game), `ps`, `kill`, `launch`, `reg` |
| `um video` | `contact` sheets, `compile` (EDL → titled, beat-cut video with music), `mux`, `beats`, `first-frame` |
| `um backup` | Snapshot, diff and restore save folders |
| `um publish check` | Blocks shipping game files, decompiled code and leaked keys |
| `um kb` | The knowledge base: `search`, `show`, `new`, `check`, `index`, `sync`, `pr` |

Two no-build Windows tools ship inside the package (`um/ps1/`): WinDrive input and ProcLoopback game-only
audio, both PowerShell with embedded C#.

<p align="center"><img src="docs/media/pipeline.png" alt="3D route: fal concept to 3D to 16 AoE2 headings. 2D route: fal art to cutout to a 64x26 Terraria sprite in game." width="100%"></p>

## Built with it
- **[examples/terraria-tmodloader](examples/terraria-tmodloader)**: *Fal Arsenal* for tModLoader.
  - Weapons: a homing missile launcher, a tactical nuke (crater + mushroom cloud), a chain-lightning rifle, a
    black-hole gun and an orbital strike.
  - Three new enemies and a two-phase Drone Mothership boss.
  - Every sprite came from fal.
- **[examples/aoe2-de-civ](examples/aoe2-de-civ)**: *San Franciscans* for Age of Empires II DE.
  - A new civilization with a Robotaxi unique unit and Delivery Drones, rendered from fal image-to-3D models
    at AoE2's camera angle.
  - A Transamerica Pyramid wonder.
  - A reverse-engineered `.sld` sprite writer.
- **[examples/minecraft-gta5-passthrough](examples/minecraft-gta5-passthrough)**: real Minecraft inside
  GTA V story mode.
  - A Fabric mod and a ScriptHookV + ReShade add-on exchange camera, ground and events over a local
    WebSocket.
  - Minecraft's colour + depth are depth-composited into GTA's frame.
  - Minecraft TNT, arrows and fireworks become GTA explosions and bullets, and Minecraft mobs fight the
    police.

Each has a field note with every non-obvious lesson: [knowledge/INDEX.md](knowledge/INDEX.md).

## Rules it follows
- **Single-player and offline, on games you own.** It refuses to inject into online games with anti-cheat,
  write multiplayer cheats, or bypass anti-cheat, DRM or ownership checks.
- **It never ships game files or decompiled code.** Mods ship as code, your own assets, patches or
  converters.
- **It backs up before touching saves**, and kills processes by PID only.
- **It asks before** driving your mouse and keyboard, installing loaders into game folders, or publishing,
  PRs included.

Full reasoning: [`skills/mod-any-game/references/safety.md`](skills/mod-any-game/references/safety.md).

## Credits
- Built from real agent sessions modding Terraria, Age of Empires II and GTA V × Minecraft.
- Assets: [fal](https://fal.ai) (GPT Image 2, Nano Banana 2, FLUX, Trellis 2, ElevenLabs...).
- Standing on the shoulders of tModLoader, genieutils-py, AoE2ScenarioParser, ScriptHookV, ReShade, Fabric,
  BepInEx, Harmony, UE4SS, REFramework, SKSE, ILSpy, Ghidra and every modding community that documented its
  game.
- The engine playbooks also draw on the September 2026 wave of AI-built mods, and on how their creators
  explained them in public.

MIT licensed. Fonts: Space Grotesk and JetBrains Mono (SIL OFL).
