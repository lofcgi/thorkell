# The Thorkell journey

How Thorkell came to be: what we were aiming for, what we built, what broke in the real game, and why
each decision went the way it did. Written 2026-10-20 from the repository docs, the commit history and
the development sessions. The working notes behind it are mostly in Korean; this is the English account.

Numbers in this document come from the sources named next to them: commit messages, `docs/`,
`AGENTS.md`, the handoff notes in `.claude/handoffs/`, and local run reports
(`artifacts/native/<scenario>-<backend>-<time>/report.json`, which are gitignored). Where something has not
been measured or not been run, it says so.

## Contents

1. [What Thorkell is](#1-what-thorkell-is)
2. [Timeline](#2-timeline)
3. [Architecture and why](#3-architecture-and-why)
4. [Information parity](#4-information-parity)
5. [Who decides what: body, model, memory](#5-who-decides-what-body-model-memory)
6. [Models: what we use, what we measured, what we dropped](#6-models-what-we-use-what-we-measured-what-we-dropped)
7. [How Thorkell learns](#7-how-thorkell-learns)
8. [Attempts and lessons, in order](#8-attempts-and-lessons-in-order)
9. [What is verified, and where](#9-what-is-verified-and-where)
10. [Known limitations and open problems](#10-known-limitations-and-open-problems)
11. [Where to read more](#11-where-to-read-more)

---

## 1. What Thorkell is

Thorkell is a companion for Valheim who joins your world **as a real second player**, with his own
character, his own camera and the same rules you play by. He is meant to play like a person who has
never played the game before: look around, work out what things are, decide, act, talk in chat, make
mistakes and learn from them.

**The goal** (set by the user on 2026-10-17): the user starts a world with Thorkell, they play together,
and they clear the first boss, Eikthyr, without Thorkell getting the user killed or stuck. Along the way
Thorkell should handle open requests the way a friend would: asked to "build a house", he asks how big
or proposes something he can build with what he has; asked to "bring a boar", he asks what that is or
goes looking; when something attacks him mid-task, or he is hungry or hurt, he deals with it and then
goes back to what he was doing, without losing the long-term goal.

**The core principle is information parity.** Thorkell's brain gets only what a person would know if they
were controlling Thorkell's character and looking at Thorkell's screen. Not the human's screen, and not
the game's internals. The reason is the user's: give him the same amount and kind of information a
person gets, and he has a chance to judge like a person. Section 4 explains what that means in practice.

## 2. Timeline

| Date | What happened |
|---|---|
| 2026-09 (earlier project) | "Eira", an earlier companion attempt on Valheim 0.221.12. Its lessons shaped Thorkell (section 8.1) |
| 2026-10-01 | Feasibility research: is a self-directed Valheim companion possible, and with what models? (`docs/research/2026-10-01-thorkell-feasibility.md`) |
| 2026-10-02 | User decisions (real player bot, hybrid models, vanilla game, crossplay, isolated clones). Protocol, body, brain and simulator built. First real-game runs: the bot joins a Steam host and a crossplay host, and the brain drives it. Real API contracts measured. First rehearsal with the user exposed chat, naming and planner problems |
| 2026-10-11, 10-17 | Survey of game-playing AI and lightweight decision models (`docs/research/reports/`). The architecture conclusion did not change |
| 2026-10-16/17 | Steam updated Valheim to 1.0.20 (network version 41). Thorkell moved to it. The Eikthyr goal started: crafting, building, bow, hunting, cooking |
| 2026-10-17 | The user pointed out that fight tactics were being tuned as code constants. Fight judgment moved to the model, learning moved to Thorkell's memory |
| 2026-10-18 | Eleven solo boss runs and five co-op runs in the real game. Eikthyr cleared together on the 4th and 5th co-op runs. A rehearsal with the user led to pixel vision ("eyes"), doors, portals and the "a big thing may not be a foe" change. New-world-from-nothing runs (`fresh`) |
| 2026-10-19/20 | English play for a README video: both games, the leader, the planner, the eyes and Thorkell's speech in English. English `talk` passed; English `fresh` runs found broken axes, too-hard trees, unreachable logs and missing flat ground. The English co-op boss run was started and its result is not recorded yet |

## 3. Architecture and why

```
The user's Valheim (isolated host clone + Thorkell.Host plugin) ──PlayFab crossplay── friends
   │  127.0.0.1 Steam loopback listener (+ crossplay shim)
   ▼
Bot Valheim client (isolated clone + Thorkell.Body plugin, small 640x360 window, muted)
   │  TCP NDJSON on 127.0.0.1, HMAC handshake
   ▼
brain (Python, asyncio)
   ├─ controller: goals, arbitration, skills          (code)
   ├─ fast typed decisions: Jev (laya later)          (model, sub-second)
   ├─ planning, fight judgment, reflection: gemini-3.8-flash
   ├─ eyes: Thorkell's own frames read by gemini-3.5-flash-lite
   ├─ memory: SQLite facts, places, fight episodes, lessons
   └─ voice: gemini-3.8-live (built, not used in play yet)
```

| Layer | Rate | Where |
|---|---|---|
| Body: perception, actions, reflexes | every frame | `plugin/Thorkell.Body` (BepInEx, C#) |
| Host side: loopback listener, crossplay shim, chat relay, chat names, HUD | per event | `plugin/Thorkell.Host` |
| Shared game API handles, version gate, isolation | at start | `plugin/Thorkell.Compat` |
| Protocol DTOs, codec, HMAC; pure logic (reflex arbitration, hysteresis, gate) | | `plugin/Thorkell.Wire`, `plugin/Thorkell.Core` |
| Brain: controller, skills, planner, tactics, memory, talk, ops CLI | events + a few Hz | `brain/thorkell/` |
| Simulator | | `brain/thorkell/sim/world.py` |

### 3.1 A real player, not an NPC

Thorkell is a second Valheim client logged into the world as a normal `Player`. The alternatives were
rejected for concrete reasons:

- **A creature NPC inside the host** (the first thing Eira tried, a Dverger) does not get hunger, stamina,
  recipe discovery or building rules; they have to be faked, and the prefab has to be registered on every
  client. A "first-time player" experience is not possible with faked rules.
- **A second `Player` in the same client** is destroyed by the game: `Player.FixedUpdate` removes any
  locally owned player that is not `m_localPlayer`. This was true in 0.221.12 and is still true in 1.0.16
  (`docs/api/1.0.16.md`, end of the Eira section).

A real player loads its own zones (so it can explore on its own), has its own camera (which later made
pixel vision possible), and plays by exactly the rules the human plays by. The price is running two games
on one Mac.

### 3.2 Getting a same-account client into a crossplay game

Both games run under the user's one Steam account. Two processes on the same account cannot meet over
Steam P2P (learned in Eira), so the host plugin opens a **Steam IP listener on 127.0.0.1** and the bot
connects to it. On a crossplay (PlayFab) host this needs more:

- The host creates a loopback-only host socket rather than calling `StartHost()`, which would also open a
  P2P listener and widen the attack surface.
- `ZNet.RPC_PeerInfo` decides how to authenticate a peer from the server's online backend. A **transpiler
  shim** replaces exactly two loads of `ZNet.m_onlineBackend` with a call that answers "Steam" for the
  loopback peer only. If it does not find exactly two, the patch is refused and the listener stays closed
  (fail-closed). A prefix/finalizer version was rejected because it briefly corrupts the player list for
  PlayFab friends (`docs/api/1.0.16.md` A3).
- The bot is given the game's long connection timeout (90 s, the value the game itself uses for crossplay
  joins). One run lost the bot after 30 s because world generation on the client took 44 s while the Mac
  was busy (commit `c3ba468`, `docs/api/1.0.16.md` A5).

Several things only showed up when the user tried it (section 8.3): the human's chat never reaches a
loopback peer, the chat window printed Thorkell's lines under the human's name, and a far-away leader is
not loaded on the bot's side. Each needed a host-side fix.

### 3.3 Body and brain

The body is a BepInEx plugin in the bot client. It drives the character through the same controls a
player uses (`Player.SetControls`, virtual input), perceives what a player would see, and runs
**deterministic reflexes** (defence, self-preservation, getting unstuck) that react within a frame. The
brain is a Python process that sends commands and receives state, scenes and events.

- **TCP NDJSON, not UDP.** Eira streamed 20 Hz UDP JSON. Thorkell's motor control is frame-by-frame in
  C#, and the brain only sends occasional commands, but events and results must never be lost, so an
  ordered, reliable stream fits better (`protocol/PROTOCOL.md`). `state` comes at 10 Hz, `scene` at 2 Hz,
  events as they happen.
- **HMAC-SHA256 handshake** on a loopback-only port (`brain/thorkell/body/auth.py`,
  `plugin/Thorkell.Wire/Auth.cs`, test vectors in `protocol/v1/hmac_vectors.json`).
- **The game's own Newtonsoft.Json** instead of Unity's `JsonUtility`, which dropped nested fields in Eira.
- **One contract, two languages.** Every message type has a fixture in `protocol/v1/fixtures/`; C# and
  Python tests both decode and re-encode the same files and must produce identical JSON.
- **Every action verifies its result in the world**: wood counted by inventory increase, a chop by the
  tree's HP falling, a hand-over by the receiver's inventory, a building by the piece existing. "The swing
  was accepted" is never progress (an Eira lesson, kept as a rule in `AGENTS.md`).
- **Instant commands** (`say`, `equip`, `unequip`, `eat`) do not use the motor, so the brain can change
  weapon or eat while a reflex holds the body. In the simulator, Thorkell died because the brain could
  not switch weapons during a reflex.

### 3.4 Never touching the user's game

Hard rule 1 in `AGENTS.md`: nothing writes to the real game install, its saves or its preferences unless
the user agrees at that moment. This turned out to need more than careful code:

- All runtimes (bot, test hosts, the user's rehearsal host) are **APFS clones** of the game under
  `~/Library/Application Support/Thorkell/`, with their own save folders.
- Unity writes to the shared preferences file natively at start and at exit; Harmony cannot stop it, and
  `CFFIXED_USER_HOME` does not move preferences. So bot and test runtimes run inside a **`sandbox-exec`
  deny profile** that blocks the user's preferences, saves, logs and real install (`ops/runtime.py`).
- Cloud-save and save-path checks run just before the game initialises save storage, because a plugin's
  `Awake` runs before platform initialisation.
- Every scenario fingerprints the user's saves, Steam Cloud folder and preferences before and after and
  reports any change as a violation. Bots are killed with SIGKILL so a graceful Unity shutdown cannot write
  preferences.
- `thorkell backup` copies the user's saves (Steam Cloud included) and preferences with sha256 checksums;
  rehearsals run on a copy.

The handoff notes record no change to the user's preferences or saves in the runs they describe.

### 3.5 A simulator that speaks the same protocol

`brain/thorkell/sim/world.py` is a small 2D stand-in for the body and the game. It is not a Valheim model;
it has just enough (walking, trees to logs to wood, pickups, food, creatures, weapons with hidden damage
multipliers, day and night, later bows that wear out, portals, wind-ups before attacks) and follows the
same command and event contracts. It exists so that the brain can be tested in seconds without two game
windows. The rule in `AGENTS.md` is that when the body's behaviour rules change, the simulator changes
with them. Many real-game failures in section 8 were first reproduced in the simulator as a failing test,
then fixed.

### 3.6 Version gate

The body arms only on builds listed in `plugin/Thorkell.Compat/tested-versions.json` (by assembly hash),
and every private member it uses through reflection is listed in `RequiredApi.json` and checked offline by
`thorkell verify-api`. When Steam updated the game to 1.0.20 mid-project, the gate refused the new build
as designed; 1.0.20 was added only after the connection scenarios passed on it (commit `beb3aaf`).

## 4. Information parity

The brain receives what Thorkell's own screen would tell a person, and nothing else.

The user corrected one misreading on 2026-10-17. An early design note said Thorkell would get "the
information on the human player's screen". The user said that was not the idea. Thorkell should get, from
his own play, the amount and kind of information a human would get playing that character, in the hope
that he then judges like a human. The only thing that comes from the human's game is the chat the human
types, because a person also reads a friend's chat (`docs/design/eikthyr-companion.md`).

What that means concretely:

| Information | What Thorkell gets | Why |
|---|---|---|
| Creature names | Only when the game would show a name tag: the creature is aimed at by the camera ray and within 30 m (`EnemyHud` rules). Otherwise "an unknown creature" plus what it looks like (height) | A person learns a name by looking at it |
| Big creatures | Seen up to 100 m with a line of sight; a noticed boss's health bar at the top of the screen (`boss_bars`), even when trees hide the boss | A person sees a 3 m deer beyond 40 m and always sees the boss bar |
| Recipes | Only once they appear in the crafting or hammer menu, which happens when the materials have been picked up | That is how the game teaches recipes |
| Attacks | The moment a seen creature starts an attack animation (`creature_attacking`) | Animations are synced; a person sees the wind-up |
| Kills | A body falling, or the centre-screen "... is slain" message | A target that is no longer visible is not dead |
| Scene | Thorkell's own camera frames, read by a vision model (since 2026-10-18) | A list of objects is not a scene (section 8.8) |
| Never sent | Prefab names, tool tiers, AI internals; localisation tokens such as `$enemy_...` are used as keys but never put in a prompt | A person cannot see them |

The planner may only name things the game has shown or the leader has said; the validator enforces it. This also limits how much the model's prior knowledge of Valheim leaks into play,
although the model still knows the game and the leak has not been measured.

## 5. Who decides what: body, model, memory

This is the part that changed most, and every change came from the user looking at how Thorkell behaved.

| Kind of thing | Like a person's | Lives in |
|---|---|---|
| Moving, aiming, swinging, placing, opening doors, rolling | hands on keyboard and mouse | code (body skills) |
| Flinching, blocking, getting unstuck | spinal reflexes | code (body reflexes, with hysteresis) |
| Seeing | eyes | state read under the parity rules, plus pixel vision of his own screen |
| "Is that a boss? Should I fight it? From how far?" | judgment | the model, from perception and memory |
| "Lightning reaches 26 m" | experience | Thorkell's memory, as text lessons he checks |

The changes that got us here:

1. **"A real player, not an NPC"** (2026-10-02). The body is a second client, so the rules are the game's.
2. **Known commands skip the planner** (2026-10-02). In the first rehearsal, "follow me" went to the planner,
   which set a stop condition of `hp_below = 10.0` (it should be a 0 to 1 fraction), so Thorkell said he
   was too hurt to come. Fixed commands ("follow me", "wait", "stop", "chop N wood", "take this") now
   start tested skills at once; the planner handles only new requests and judgment.
3. **"Learning must not end up as code"** (2026-10-17). After a day of boss runs the user asked why lessons
   were being kept as code. Boss fights had been getting better because the developer kept changing
   constants (distance 16 to 24 m, back off at 35% HP, eat to three food slots first, don't go back alone
   after dying), not because Thorkell had learned anything. Nothing stayed with Thorkell. The user also
   asked for common sense to come from the start: a person seeing something huge thinks "boss", nobody
   starts with "boss means 24 m". Tactics moved to the model, learning to memory (section 7).
4. **"Don't go to extremes"** (2026-10-17). When pixel vision was first proposed for this, the user said a
   computer can read the state of the moment, which is its version of eyes, as long as it is limited to
   what a person could see. The capture code was removed and perception stayed state-based, with
   human-level descriptions (height, the bar at the top of the screen) instead of code labels such as
   `size: large`.
5. **"Adding safety rules makes a deterministic NPC"** (2026-10-18). In a rehearsal Thorkell attacked the
   user's summoned creature, because code started a fight with anything big that had noticed him and only
   asked the model *how* to fight. When a safety rule was suggested as the fix, the user rejected it.
   Whether to fight is now a judgment: the tactic can be `leave`, and the leader's words during a fight
   trigger a new judgment.
6. **"Actions in code, perception by pixel vision, judgment by the model"** (2026-10-18). The same rehearsal
   showed that a list of named objects is not a scene: Thorkell could not see a portal in front of the
   leader, took the summon for a monster, and could not find the way into a house. The proposed
   alternative was more structured text (all named things, a summary of buildings, where the leader is
   looking). The user chose instead to have every needed action implemented in code and perception done
   by pixel vision of Thorkell's own screen, if it was fast enough. It was: about 1 to 3 s per look
   (section 6), so the eyes serve slow judgment and the state still drives fast reactions.

## 6. Models: what we use, what we measured, what we dropped

### 6.1 What each model does

| Role | Model | Used for | Notes |
|---|---|---|---|
| Planning, fight judgment, reflection | `gemini-3.8-flash`, thinking `low` | Open requests, asking back, plans checked by a validator, fight tactics, post-fight lessons | Called on events, never per frame |
| Eyes | `gemini-3.5-flash-lite`, low resolution, thinking `minimal` | Reading Thorkell's own 640x360 frames before answering the leader and before judging a fight | Off unless `[vision]` is set |
| Fast typed decisions | Jev `jev-1.13.0` (TypeSafe "System One") | `threat_response` when something hits him, with a 0.6 s deadline | laya (local, open weights) is the planned replacement; not trained yet |
| Voice | `gemini-3.8-live` | Spoken conversation with tools that delegate to the controller | Built and tested against a fake session and a live contract; play uses game chat only |

`brain/thorkell.play.toml` (and `thorkell.play.en.toml` for English) is the configuration used for play
and for the real-game scenarios. Without `--config`, Thorkell runs on rules and understands only the
fixed commands.

### 6.2 Why this mix

- **Not one model that looks at pixels and does everything.** The feasibility research (section 1.3 of
  `docs/research/2026-10-01-thorkell-feasibility.md`) found the pixel-to-action game agents either closed
  (SIMA 2, Game-TARS), unreleased, non-commercial or Windows-only, or self-described as basic visual
  movement rather than gameplay. Products that worked (PUBG Ally, for instance) split a fast deterministic
  layer from a slower model layer. Valheim mods can read state and call the game's own actions, which is
  faster and more reliable.
- **Not a local LLM for planning.** With two Valheim clients on a 24 GB Mac, about 4B parameters is the
  local ceiling, and Eira's 1.7B model could not decompose goals (section 8.1).
- **The user named the models**: Gemini 3.8, Jev and laya.
- **Later surveys** (2026-10-11 and 10-17, `docs/research/reports/`) looked at lightweight and
  decision-only models (several Jev-compatible endpoints now exist) and did not change the conclusion:
  execution in code, choices by models, cost controlled by session design.

### 6.3 Measured numbers

Real API contracts, 2026-10-02, one run each (`docs/research/2026-10-02-api-costs-and-keys.md` §7):

| Model | Check | Result | What we did |
|---|---|---|---|
| `gemini-3.8-flash` | thinking `minimal` | **Refused with 400** ("not supported for this model") | Removed from the config; reading it is a `ConfigError` |
| | thinking `low` | 2.24 s, schema-valid JSON | Planner default |
| | thinking `medium` | **40.42 s** (once) | Kept off the real-time path |
| Jev `jev-1.13.0` | 10 `threat_response` calls | 0 errors, **p50 188 ms, p95 292 ms** | Fits the 600 ms deadline |
| | tendency | At 72% HP with a Greydwarf 3 m away: `retreat_to_leader` 0.57 to 0.64, `fight` 0.24 to 0.29 | More cautious than the rules |
| `gemini-3.8-live` | first audio | **1.19 s** after a question, 0.69 s after a tool response | Within the 2.0 s target |
| | tool call | Called `ask_status` for "what are you doing?" | |

Vision (2026-10-18):

| Measurement | Result | Source |
|---|---|---|
| `gemini-3.8-flash` on a 640x360 JPEG | about 2.5 to 3 s (290 input tokens at low resolution, 553 at medium) | session measurement |
| `gemini-3.5-flash-lite` on one 640x360 frame | about 1.2 s | `brain/thorkell/config.py`, `world/sight.py` |
| In game, four frames all round | rendered in 0.4 s, read in about 2.2 s | commit `b0a459d` |
| In game, English run 2026-10-19 | two readings of 3.0 s and 3.3 s | `sight` report |

Prices noted on 2026-10-02 (official pricing pages, estimates marked as such in the costs doc): Flash
$0.75 / $3.75 per 1M tokens input/output until 2026-12-31 (double from 2027), Flash-Lite $0.30 / $2.50,
Jev $0.042 per 1M input tokens with free output. The doc estimates about $9 a month for 60 hours of
chat-only play with planner and Jev, and warns that Live re-bills the whole accumulated context on every
turn, so voice cost depends on session design more than on minutes.

### 6.4 What was refused, rejected or changed

| What happened | Change |
|---|---|
| Flash refused thinking `minimal` with 400 | `low` is the default; `minimal` is rejected at config load |
| The free tier allowed 20 Flash requests a day. In the first rehearsal a greeting hit 429, the SDK retried three times about 30 s apart, and Thorkell was silent for 91 s | 429 is not retried; Thorkell says he hit the planning model's limit and that fixed commands still work. Only 5xx is retried once; requests time out at 60 s. Real play moved to a paid tier |
| Known commands sent to the planner were 20 s slower and came back with a wrong stop condition (`hp_below` 10.0) | Known commands start verified skills directly; the validator checks units (`hp_below` is a 0 to 1 fraction) |
| The plan schema with menu enums, numeric bounds and descriptions was refused as too complex (400) | Bounds live in the validator, which asks once more with a hint and otherwise rejects; no fallback |
| The model cited what it saw ("visible: ...") instead of fact ids, and left out gather counts | Such assumptions become hypotheses, a missing argument comes back with a hint, gather without a count takes what is in sight (commit `f561cc0`) |
| "How are you feeling today?" matched the status phrase | Small talk goes to the planner, which may answer with words only |
| The vision model first described a portal that was behind Thorkell | The prompt says to describe only what is in the picture; named things that are not visible are left out |
| In English play the vision model answered in Korean, because the schema's field names ended in `_ko` | The schema is renamed to `_en` at the model boundary and back (`lang.schema_for_model`, commit `7b648e8`) |
| The validator rejected "boars" because the game says "Boar" | Names the leader said match in any case and singular/plural |
| Model API errors (503 and similar) ended silently | They become `ModelError` and Thorkell says so |

## 7. How Thorkell learns

### 7.1 Facts

Memory is SQLite per world (`brain/thorkell/mind/store.py`). Each fact has a source (observed, game UI,
told, inferred) and a status:

- `hypothesis`: told by someone or inferred, not yet seen;
- `supported`: seen at least once and not contradicted more often;
- `verified`: seen three times, or told and then seen;
- `refuted`: contradicted at least twice and more often than supported.

Examples: a creature's name from its tag, weak and resistant damage types from the colour of the damage
numbers, what a bush gives when picked, that deer run away. If the leader says "Greydwarves are weak to
blunt weapons", that is a hypothesis until a fight confirms it, and then Thorkell says the leader was right.
Weakness learning only counts hits on the intended target (`damage_dealt.on_target`), because one swing
also hits the bush next to the tree.

### 7.2 Fights

```
something big notices or hits Thorkell / a fight ends / Thorkell dies      (code decides WHEN to think)
  → describe what his screen shows: height, the bar at the top, his food slots and weapons,
    his own health, what the leader said in the last few minutes, earlier fights, standing lessons
  → tactic (gemini-3.8-flash): what it seems to be; ranged / melee / keep_away / leave;
    keep and close distances, when to back off, whether to eat first, whether to retreat toward
    the leader, how close a wind-up must be to roll; which lessons it follows
  → the fight skill carries that out and records it
  → episode: hits taken (when, how much, from how far, by what), arrows fired, the foe's health bar
    over time, his own health over time, how many seconds went on shooting, backing off, rolling, waiting
  → reflection (gemini-3.8-flash): in time order, what worked and what did not; new lessons with the
    numbers behind them; a verdict on every lesson shown (held / did not hold)
  → after a death: go back to the tombstone alone or with the leader
```

The code in `brain/thorkell/plan/tactics.py` and `control/fight.py` holds no creature-specific tactic.

**Why not code constants.** Because then the developer learns and Thorkell does not, which is the user's
point from 2026-10-17. Text lessons also stay readable: you can see what he concluded and why. Fine-tuning
a small model (laya) would need thousands of logged decisions; the decision log format exists but has not
been used for training.

**Does it work?** In the real game, yes, with limits. After the first solo attempt the model wrote "lightning
reaches 26 m, backing off alone doesn't avoid it", and later fights cited and verified it. From timed
records it drew "don't roll blindly" and "backing off too long only lets the boss heal" (the record showed
health 7.5 to 8.5 in 33 s of backing off while the boss went from 78% back to 80%). It chose to roll from
wind-ups within 8 m on first sight and 16 m once it had learned the lightning's reach. Dry runs with the
real model on a copy of the memory moved its keep/close distances from 35/20 m to 32/16 m to 32/15 m. It
has still not won alone (section 9).

**What the record must contain is what a person remembers.** Several wrong lessons came from bad
records, not bad reasoning (section 8.6). For instance, the food count was taken before eating, and the
model concluded "don't fight on one food slot" from a fight that had three. Bug-made episodes were removed
or corrected by hand, with backups, and the corrections are recorded in `.claude/handoffs/2026-10-17_23-58.md`
so real learning can be told apart from repaired data.

## 8. Attempts and lessons, in order

Each item: what happened, what changed, why. Commit hashes point to the full explanation.

### 8.1 Eira, the earlier attempt (September 2026, Valheim 0.221.12)

Eira already used a second client as a real player, controlled by a BepInEx plugin over 20 Hz UDP JSON,
with one local model (Ollama `qwen3:1.7b`). It passed basic actions, chopping, repairing, hunting and
cooking runs and a 20-minute evaluation (70 wood, 788 decisions), but that evaluation used a scripted
partner and an already-debugged seed.

- **31 runs, 23 failures.** The biggest causes were navigation stalls at water, coast and around shelters
  (6), being unable to find meat or a blocked food chain (about 5), empty tool calls from the model,
  being crushed by a falling log, the leader dying, and a delivery mismatch (the bot counted 50 dropped,
  the host received 10, because `DropItem` throws where the body faces, not where it looks). On an unseen
  seed, the first run never reached the workbench.
- **The model was not deciding much.** Over 2,405 decisions (p50 0.53 s), 33% offered only one option:
  a hand-written state machine did the goal decomposition and the model mostly picked targets.
- Not built: crafting, building, general combat, voice, vision, long-term knowledge, proactive speech,
  play with a real person.

What Thorkell kept as rules (`AGENTS.md`): a separate client; loopback IP instead of same-account P2P;
graphics on (with `-nographics` world time stops and cooking never finishes); no `JsonUtility`; raycasts
instead of `Collider.ClosestPoint` on non-convex meshes; enter/exit hysteresis instead of one retreat
threshold; progress measured by target HP and the receiver's inventory; face the receiver before dropping;
follow waypoints instead of straight lines; the planner's reach must not be stricter than the executor's
(Eira had 2.9 m against 3 m); never tune on holdout seeds; goal decomposition by a planning model and
arithmetic by code.

### 8.2 Research and foundations (2026-10-01/02)

The research concluded the project was feasible as a layered system (body, reflexes, fast typed decisions,
slow planning and learning, voice), not as one pixel model. The user then fixed five decisions: a real
player bot; hybrid models; vanilla game plus the Thorkell plugins only (mods were broken by the 1.0
release); crossplay on, because that is how the user plays with friends; and isolated host clones.

The protocol, body, brain, simulator and decision runner were built and tested against the simulator and
fake models before anything ran in the game. Decision backends (rules, Jev, laya) are chosen per decision
point in config and never switch on their own; a missed deadline is logged as "left to reflexes" with no
hidden default action.

### 8.3 First real-game runs and the first rehearsal (2026-10-02)

The connection scenarios passed: S0 (Steam host) and S0b (crossplay host with the shim), with zero changes
to the user's preferences and saves, then S1, where the brain made the bot equip, eat, walk, pick up, chop
a standing tree (HP drop confirmed), look at the leader and talk. Getting there fixed:

| Found in game | Change | Why |
|---|---|---|
| The plugin's `Awake` runs before platform initialisation; the cloud check crashed | Checks moved to just before save storage initialises | Isolation must be verified before anything boots |
| Unity writes shared preferences natively at start | `sandbox-exec` deny profile; any preference change is a violation | Harmony cannot block native writes |
| The game auto-picks up items within 2 m | Gathering progress is counted by inventory increase | Picking up explicitly raced the game |
| "Arrived but can't reach" | Arrival, reach and swing range use one measure (nearest collider surface, height included) | Different measures disagreed |
| `StartAttack` returned true without a swing | A swing counts only when the attack animation starts | Accepting is not doing |
| One swing hit the tree and a bush 1.3 m away | Bodies report `on_target` from the actual hit point; learning uses only those | Otherwise the wrong thing gets blamed |
| A placed log rolled into the sea | Fixtures go down after terrain loads, lifted above the ground, 5 m from the leader; chopping tests use standing trees | Test fixtures, not production behaviour |

Then the user tried playing with Thorkell for the first time and reported, in short, that it was a mess
and had clearly not been tested in the game. The findings:

| Symptom | Cause | Change |
|---|---|---|
| "Follow me" got "I'm too hurt" | Planner set `hp_below = 10.0` | Known commands skip the planner; units validated |
| No answers to in-game chat | The human's chat never reaches a loopback peer (platform permission check returns Error); normal chat also drops beyond 15 m | The host plugin relays the leader's chat to the brain; Thorkell shouts when the leader is beyond 14 m |
| Thorkell's lines appeared under the human's character name | The chat window looks up names by platform ID, and both players share one Steam account | The host prints loopback peers' lines under Thorkell's name |
| Thorkell seemed not to exist | He spawned at the start temple, far away, and the body armed only when the leader's character was loaded | Arm when the leader is connected; both share map positions; "follow me" from far away walks toward the map position |
| The game's "I have arrived!" went to the brain as the leader's words | The game shouts it on first spawn | Filtered out |
| Silence for 91 s | Free tier 429 plus SDK retries | See section 6.4 |
| The bot's game made sound | The game resets the volume | Muted every frame |

The new `talk` scenario (a harness leader talks in chat, walks off, goes 260 to 320 m away, makes small
talk) came out of this, so that conversation is checked in the real game, not only in the simulator.
The user also asked for a launcher, then a GUI; `Thorkell.app` (SwiftUI, `tools/gui`) talks to
`thorkell play --ui jsonl`.

### 8.4 The game updates, and the Eikthyr goal begins (2026-10-16/17)

Steam moved the game to 1.0.20; 1.0.20 friends could no longer join a 1.0.16 host, and the gate refused the
new build. After `peer` and `primitives` passed on 1.0.20 it was added to the gate (`beb3aaf`).

The user set the goal of section 1 and asked for real play videos to be studied. Ten videos of first-time
players up to Eikthyr (`docs/research/2026-10-17-valheim-human-play-observations.md`) showed, for example,
that first-time players took about 1.5 to 3 hours to reach the first boss and were stuck longest on not
knowing about the hammer. The early-game mechanics are in `docs/api/early-game.md`.

New body actions: craft, place (through the game's own hammer placement), use an item, drop, shoot with a
bow (ballistic aim), dodge. New brain skills: gather, craft, build, hunt, search, cook, give, go to, recover a
tombstone, sleep. Real-game findings along the way:

| Found in game | Change |
|---|---|
| Walking ran at 1 m/s: the path follower kept turning back to corners it had passed | Passed corners are skipped (2.7 m/s walk, 7 m/s run) (`f30d51a`) |
| Name tags did not appear when Thorkell "looked" at a creature | The game's aim is a **camera ray** from behind and above the head, not the eyes; looking aims the camera ray and sets pitch too, because `SetLookDir` only turns left and right (`cf4ebb3`) |
| Walls and the cooking rack landed 0.6 to 1.6 m off | Buildings report their `center` besides the approach point |
| Pieces floated on bushes or the workbench | Placement aims at terrain, checks the preview sits where aimed, and nudges like a player moving the crosshair |
| Commands timed out while a reflex held the body | They are refused at once (`preempted`); fight commands take the body over from the defence reflex |

The `skills` scenario passed twice in a row in the real game: roof a workbench, craft arrows, hunt a boar
with the bow, cook the meat over a fire. With the real model, the open requests (build a house, bring a
boar, we need food, small talk) passed `thorkell judge`.

### 8.5 From code tactics to model and memory (2026-10-17)

The first boss runs used tactics in code (`size == large` meant a boss fight, with hand-tuned distances
and health thresholds). Best result: Eikthyr at 76%. Two real-game lessons from this phase stayed:

- `creature_died` comes from the ragdoll appearing, so a kill is something seen, not a target that went
  out of sight.
- The defence reflex charged Eikthyr with a bow in hand and died to three antler hits. Big attackers and
  bow fights are now left to the brain.

Then the user's question about learning (section 5, item 3) led to commit `e781cb8`: code decides only
when to think, the model decides what the creature is and how to fight it, and lessons go to memory. On
the first test with the real model, it called Eikthyr "something like the lord of this land" from the bar at
the top of the screen, chose to keep its distance with the bow and eat first, and on a second try cited
both of its lessons.

### 8.6 Solo boss runs 1 to 11 (2026-10-18)

The same memory file was carried across runs. In these runs the harness leader said it would only watch,
so Thorkell fought alone. Summary from `.claude/handoffs/2026-10-17_23-58.md` and the commits:

| Run | What happened | What changed, and why |
|---|---|---|
| 1 | The model chose to keep away at 25 m and eat first, and shouted for the leader. Hit by lightning 7 times at 6 to 26 m in 212 s, no arrows fired; ran 230 m straight away from the leader into the Black Forest and died. The record said one food slot (counted before eating to three), so the reflection drew a wrong lesson about food | Records keep the food the fight was entered with; backing off leans toward the leader (`35e808c`). Also: during the reflex's one quiet second the body chased a destroyed attacker and threw 177 exceptions, stalling the link (`8eea13c`) |
| 2 | Backing off toward the leader dragged the boss to the non-fighting harness leader, who died. The leader's ragdoll next to the boss was read as Eikthyr falling, and Thorkell said he had won | A player's ragdoll is not a creature falling, with tests in Core (`0615020`). Whether to retreat toward the leader became the model's call (`retreat_to_leader`), informed by the leader's recent words, which were not being kept in memory before (`77b6219`) |
| 3 | 141 s, 3 arrows, boss at 96%. The plan "eat, offer trophies" failed with "no runner for plan skill offer" | Every library skill runs as a plan step, with a test keeping them together; time spent backing off is recorded (`82d9c81`) |
| 4 | Thorkell's own plan offered and fought, then noticing the boss started a second fight; two fight loops drove one body. The same orphaned step kept chopping wood after "stop" | A plan's step is cancelled with the plan (`b72004b`) |
| 5 | The planner's "stop if hurt" guard cut the fight at half health, and fights run as plan steps were never remembered | Plan fights are remembered; the tactic's retreat health decides, not the plan guard; the health bar over time is recorded (`aa0001e`) |
| 6 | Boss to 78% in 98 s, then backed off for 65 s while his own health barely rose and the boss healed to 80%. The reflection learned only "keep further away" | Reflection asks for the fight in time order and what did and did not work (`ce480df`) |
| 7 | A boar hit him during the boss fight; the defence goal paused the boss plan, he died, and the fight was never recorded | A plan on a fight step counts as survival in arbitration (`c5ccfd7`) |
| 8 | Died to a boar (8 hits, 52% to 0%) while shooting Eikthyr; the record held only the boss's hits, so the reflection blamed the boss. The model asked to "dodge when you see the attack motion", which Thorkell could not see | The body reports attack wind-ups (`creature_attacking`); the tactic chooses `dodge_within_m`; other attackers are recorded and dealt with first (`99ff59b`) |
| 9 | Saw 11 wind-ups and rolled 11 times, dealt with a boar twice; 3 arrows, boss 95% | Nobody could tell where the time went |
| 10 | 183 s: 27 back-offs (98 s), 36 rolls (35 s), 3 shots (8 s) | Time per activity is recorded (`428a73f`). The rule "roll every round when close" was mine, from before Thorkell could see wind-ups; now he rolls only on a seen wind-up (`482a294`) |
| 11 | 128 s backing off, one arrow; the distance lessons he actually followed were never judged because the tactic did not cite them | Reflection judges every lesson shown; the tactic question explains how the body moves (`8e64ac3`) |

The pattern the user's direction predicted held: each run exposed a gap in perception or in the record,
not a missing tactic. Those gaps are listed in `AGENTS.md`: the boss's attack animation, big creatures
beyond 40 m, the boss bar, the centre-screen kill message; all things a person sees.

### 8.7 Co-op runs 1 to 5: Eikthyr cleared together (2026-10-18)

The goal is to clear the boss *together*, so `boss --together` was added (`904224a`). The harness leader
says "let's take him together, I'll hold him in front" and stands by Eikthyr bare-handed. Because the
harness leader cannot really fight, it is invulnerable in this test only.

| Run | Result | What changed |
|---|---|---|
| 1 | Over after 37 s with "lost him": Thorkell kept 32 m away and the boss, busy with the leader, flickered across the 40 m perception edge | Big creatures perceived to 100 m, boss bars always shown when noticed (`904224a`) |
| 2 | 30 arrows, no hits taken, boss down to 2%. Then the bow broke; a bow with durability 0 still counted as a bow, so he tried 41 more shots, and a 400-round cap ended the fight | A broken bow is not a bow; he says so and rethinks; fights end after 120 s without progress instead of after a fixed number of rounds (`f4c5dac`). Out of 406 s only 146 s were shooting; rounds now reuse the newest scene and don't re-equip (`8f5da1a`) |
| 3 | Boss to 13%, then the bow broke and the model chose to close in with a club, and he died | (a model judgment, left as is) |
| 4 | **Cleared** (server key `defeated_eikthyr`), shot from 99% to about 1%, never hit by the boss. But he said "lost him": no body fell in his sight, while the game had printed the kill in the centre of the screen. He also retried 55 shots blocked by a tree | The centre-screen kill message ends a fight as a win; a blocked shot is followed by a few steps sideways (`828c848`) |
| 5 | **Cleared**, no hits taken, "I beat Eikthyr!", picked up the drops | |

What the record cannot tell: who struck the last 1% (the bare-handed leader or Thorkell). The earlier
98% looks like Thorkell's arrows.

### 8.8 A rehearsal with the user: eyes, non-foes, doors and portals (2026-10-18)

The user played on a copy of their own late-game world and reported that Thorkell suddenly went quiet.
The only record was the app's technical log, so each play run now writes `brain.log` (`78a80e5`). Every
question Thorkell asked came out twice (`f246000`). Then the bigger problems:

| Seen in the rehearsal | Change |
|---|---|
| Could not see the portal the leader stood at; took the leader's summoned root for a monster; could not get into the house | Eyes: the body renders Thorkell's camera (640x360 JPEG, one frame or four all round, motion blur off), and the vision model says what is there, tied to the ids the game has named. Anything that shows a name when aimed at is now in the scene (`b0a459d`) |
| Code started a fight with the summon every 30 s; the leader's "I summoned that" waited two minutes behind the fight | Thorkell looks before planning an answer (toward where the leader faces) and before judging a fight; a tactic can be `leave`; the leader's words during a fight cause a new judgment (`e391692`). The real model, told it was a summon: "the leader says they summoned it and it isn't attacking the leader, so it seems to be on our side", leave |
| Could not get into the house; did not know "go through the portal and you're home" | Walking opens closed doors on the way; portals are their own kind with their tag and whether they are connected; `use_portal` confirms by the jump in position; a leader who vanishes at a portal is followed through it (`892062d`). The `travel` scenario passed first time: one door opened in 6.6 s, came out of a portal 38.9 m away |

The user's late-game world had long since lost its first boss, so `play --rehearsal NAME --new` was added
to start a fresh world with its own memory (`bd51b3a`).

### 8.9 A new world from nothing: `fresh` (2026-10-18)

The harness leader only talks: make an axe from what lies around, chop 20 wood, "we should build a house",
"keep it small", find food, hunt a deer for its trophy.

| Found | Change |
|---|---|
| Picking a branch "gave nothing", the request failed, and Thorkell stood still for 9 minutes | A failed step goes back to the model with what was tried and what happened; it picks another way, asks or explains (`cea8c7a`) |
| The axe recipe only appears once wood and stone are in hand, so no plan can get all the way | A plan can say it only gets partway (`think_again_after`) |
| A cap of 5 plans per request cut off an axe that was nearly made | Planning continues while there is progress (up to 12) and stops after 3 failures in a row (`88b68bb`) |
| A long branch drops its wood out of auto-pickup reach | Walk over and pick it up; wait for the inventory (scenes come twice a second) |
| An answer to a query arrived after the brain stopped waiting, and the exception killed the body's link handler | Late answers to abandoned queries are dropped (`9668809`) |
| Walking to a tree with no axe to fail with "I have no tool to cut trees" | Without an axe, wood comes from branches |
| Deer outrun a running player | Thorkell crouches and creeps up (the crouch key is a toggle) once he has learned that a creature runs, or when a chase fails; loot is picked where the creature fell |

The third Korean run passed the axe (113 s, four rethinks), 20 wood and the house question ("a small
shelter around a workbench, or bigger?"); a later run built the shelter in 105 s (hammer, workbench, walls,
roof).

### 8.10 English play for the README video (2026-10-19/20)

The user asked for English scenarios for a README video, tested in the real game, and later for the
project to be published. Playing in English meant more than translating lines:

- Both games load English in memory only; the real game's settings are not touched (`e8c3267`).
- Everything the controller, skills, memory, planner, fight judgment, eyes and voice persona say or match
  has an English counterpart; Korean play is unchanged (`81653ad`, `7b648e8`, `4475720`, `bc85637`,
  `b2f7a5d`). Skills match the English game's exact strings (Wood, Workbench, Cooking Station, "is
  slain").
- English facts are read by verb ("are weak to", "resist") and plural names are mapped to the game's
  singular name.
- Real model, English `judge`: 11 of 12 on the first try; the miss was the "boars" versus "Boar" case,
  fixed in the validator.

Real-game English runs:

| Run | Result | What changed |
|---|---|---|
| `talk`, first try | Failed: the harness waited for "Okay, I'll follow you." but the game shows shouts in capitals ("OKAY, I'LL FOLLOW YOU.") | The harness reads shouts in any case (`5abf0c1`) |
| `talk`, second try | **Passed** in 225 s: follow (acknowledged in 0.2 s), follow after the leader walks off, stop, far follow found via the map from about 266 m (arrived in 85 s), small talk answered by the planner in 3.2 s, every line under Thorkell's name | |
| `fresh` 1 | Axe from nothing in 99 s. Then the stone axe wore out halfway through "chop 20 wood" and Thorkell tried to pick it up again every six seconds; the wood step timed out | A broken tool (shown red, durability 0) is not usable; he says it broke and the request goes back to the planner with what was tried; with two of a name the body holds the working one (`2cc6238`) |
| `fresh` 2 | Axe (99 s), **20 wood (64 s), asked about the house size ("a few walls and a roof around a workbench would take about 30 wood; build that, or bigger?"), built the shelter (229 s)**; the food step timed out | The validator refused "gather mushrooms, go to the leader, give them" because the mushrooms were not in the bag yet; items from earlier steps now count (`1d16c3c`) |
| `fresh` 3 | The axe broke and he made a new one by himself ("My axe broke! I'll craft a new stone axe..."); wood and the house question passed; the shelter timed out after he walked at one unreachable log for about ten minutes | Anything that blocks the approach twice is left for another, as a person would (`66ad5f2`) |
| `fresh` 4 | 85 of 103 axe hits were "too hard": the stone axe kept hitting a tree it cannot cut, and two axes wore out. After the second axe broke, "make another axe, chop the wood, bring it" was refused by the validator | Wood from a chopping step can be handed over (`661f65d`); after a round of only too-hard hits the tree is left, and trees of that name are skipped for that tool, as a person does after seeing "too hard" (`c8ee19b`) |
| `fresh` 5 | Stopped early to restart with the "too hard" fix | |
| `fresh` 6 | Axe, wood (a second axe broke and he made another), house question; the shelter failed because no 6x5 m flat site was within 24 m of the leader or Thorkell | Search up to the body's 40 m before asking where to build (`b962255`) |
| `boss --together` (English) 1 | Thorkell answered "Got my bow ready... Coming right behind you!" and followed; the harness then waited for the request to end, but the plan ended in "follow", which never ends | The harness leader now asks him to call the boss out once he has answered, as a person would |
| `boss --together` (English) 2 | **Passed** in 497 s: he offered the trophies when asked, read the boss ("That massive stag has lightning in its horns and a health bar taking over the sky!"), chose the bow at 16 m backing off toward the leader, and **Eikthyr was defeated** (server key `defeated_eikthyr`, Eikthyr Trophy and Hard Antler in his bag) | |

Filming (2026-10-20) ran the scenes again with recording and turned up more problems, each fixed:

| Run | What happened | What changed |
|---|---|---|
| `boss` 3 (filming) | Thorkell died; the reflection drew numbered lessons (lightning reaches 26 m, clear the small adds first, roll more) | |
| `boss` 4 | With those lessons he chose 18 m, but half his shots were blocked by trees, the boss stayed at 68% and the fight was dropped after 120 s without progress | A stalled fight is rethought once, with this fight so far (blocked shots shown), before it ends (`2788530`) |
| `boss` 5 | He cited the lesson ("medium range where my shots won't get blocked"), brought the boss to 42%, then the rethink ran while the boss was behind trees and ended the fight as "I can't see Eikthyr" | The stall rethink only happens with the foe in view (`566d7d1`) |
| `boss` 6 | **Passed**: his bow broke mid-fight, he switched to the club, backed off to recover, and Eikthyr fell ("By the gods, we felled the great beast! Next time I need a fuller belly…") | He had said "I'm low on health, backing off" every 20 s while backing off; now once per retreat |
| `fresh` (filming) | After a greyling fight he took up a waiting "follow" and forgot the 20 wood the leader had asked for | A suspended goal that matters more than the best waiting one resumes first (`e02fca7`) |
| `fresh` (filming) | The flattest ground was the start temple's platform, where the game forbids building; then no flat site within 40 m | Sites skip no-build zones (`f0a6779`), and he looks 50 m out in eight directions before asking where to build (`ffb6675`). The shelter step still failed in the last filmed run |
| `fresh` (filming) | The recordings and a joined copy filled the disk | Pieces are read in place, the recorder writes 4 Mbps |

After publishing, more English `fresh` runs (7 to 14) turned up and fixed: no flat 6x5 m site within
50 m of the spawn hill (now a second, slightly uneven pass, `43b9e37`); requests ended for good when the
plan's own "stop if badly hurt / at dusk" fired (now set aside and taken up again when healed or in the
morning, also while following, `430c201`); trees beyond the 48 nearest things not reported, so "I don't see any
trees" next to a forest (`2b7a94c`); stuck in a hollow by a fallen log, side-stepping only (now also
backing away and hopping forward); looking for trees and for deer only around where he stood (now
spiralling outward, and walking up to far unnamed creatures); trying to draw an axe while swimming; and
"I don't see any trees" when the only trees were across water (now said as such). **Run 14 passed every
step in English** in 1248 s: axe 101 s, 20 wood 350 s (an axe broke and he made another), the house
question, the shelter 379 s, food 55 s, and the deer trophy 203 s.

With those fixes in, three first attempts at `boss --together` in English, each with a fresh memory,
**all killed Eikthyr** (495 s, 755 s and 605 s).

Before them, in English, `boss --together` won 2 of 5 fights in 6 runs (the first run stopped before the fight on a harness bug; one win is filmed for this README), and `fresh`
passes the axe, 20 wood and the house question reliably, with the shelter, food and deer steps still not
passing in one English run.

Recording for the README went through three versions on 2026-10-20. In-game JPG frames of Thorkell's
camera (no UI) were replaced at the user's request by a real recording of his game window. The first
version recorded the window's *area of the screen* and caught the user's own windows lying over the game;
it was stopped at once and the file deleted. The recorder now uses ScreenCaptureKit to capture the game
window's own content only (`tools/record/window-recorder.swift`), continues in a new file when the system
drops the stream, and `thorkell video` cuts captioned clips and GIFs from it. The bot's own chat window also
showed his lines under the leader's name (same Steam account); it now uses his character name.

## 9. What is verified, and where

"Real game" means a native scenario run with two real Valheim clients, checked by world changes (items in
the bag, pieces built, HP, the server's boss-defeated key). "Real model" means `thorkell judge` with the
real Gemini model on simulated situations. "Simulator" means pytest scenarios against `sim/world.py`.

| Capability | Status |
|---|---|
| Joining a Steam host and a crossplay host as a second player, without changing the user's saves or preferences | Real game (S0, S0b; repeated in every scenario) |
| Brain drives the body: equip, eat, walk, pick up, chop, look, talk | Real game (S1 `primitives`) |
| Chat conversation, follow, stop, far follow via the map, small talk | Real game (`talk`, Korean and English) |
| Craft, build, use items, shoot, hand over | Real game (`actions`) |
| Shelter, arrows, bow hunting a boar, cooking | Real game (`skills`, twice in a row) |
| Seeing with his own screen (portal, sign, leader) | Real game (`sight`) |
| Doors and portals | Real game (`travel`) |
| Axe from nothing, 20 wood, asking how big a house, building a small shelter, food, a deer trophy | Real game (`fresh`, Korean and English; every step in one English run on 2026-10-20, not every run) |
| Finding food in a new world, hunting a deer for its trophy | Real game once (English `fresh`, 2026-10-20); in earlier runs the food step timed out before a validator fix, and the deer step was not reached |
| Eikthyr with the leader | Real game: cleared on co-op runs 4 and 5 (Korean), on 2 of 5 English fights, then 3 of 3 English first attempts after the fixes (2026-10-20), with a test-only invulnerable bare-handed harness leader |
| Eikthyr alone | Not cleared: more than 15 attempts with one memory; best boss health 78% |
| Eikthyr with a leader who can die | Real game, 3 runs (2026-10-20, `--mortal-leader`): the harness leader (fed, club, no blocking or dodging) fell within about a minute each time; after the body fix Thorkell notices ("The leader is down!") and re-decides, but fought on alone and lost (boss at 59%, 58%, 29%). A second attempt with the same memory cited both lessons from the first and lost at 27%, with 19 of 44 shot attempts blocked by line of sight. After the body learned to find a nearby spot with a clear shot, two more runs lost at 72% and 37% (blocked 12 of 30, then 7 of 24, each time moving to the spot the body found). With wind-ups remembered next to the hits that followed them, the first attempt (31%) left a lesson citing the distances (hits after wind-ups at 4–15 m he had not rolled from) and the second attempt cited it and rolled from 16 m instead of 5 m, but was hit three times right after rolling and lost at 61% |
| Fight judgment, reflection, following lessons, leaving a summon alone | Real model (`judge`) and real game |
| Open requests: house, boar, food, small talk | Real model (`judge`) and partly real game |
| Sleeping in a bed when the leader does | Simulator only |
| Jev `threat_response` | Contract measured; configured for play; its decisions in the game have not been evaluated |
| Voice with `gemini-3.8-live` | Contract measured and a fake session tested; not used in play |
| laya | Not trained (log format only) |
| The user playing with Thorkell from a new world to the first boss | **Not done yet.** This is the goal's finish line |

## 10. Known limitations and open problems

- **The goal is not met yet.** The user has not yet played a new world with Thorkell through to Eikthyr.
  The co-op boss clears used a harness leader who cannot die.
- **Solo boss fights.** Thorkell fires too few arrows (in solo runs, roughly one try every 5 s where a
  person shoots every second or two), and distance lessons can keep him backing off from a boss that keeps
  chasing. Shots blocked by trees (35 to 55 in some runs) and bow durability (one crude bow lasts about
  six minutes of fighting) also limit him.
- **Food and deer in a new world** have passed in the real game only once (English `fresh`, 2026-10-20).
- **Thresholds still in code**: when to eat (`food_to_eat`), the defend skill's back-off at 30% health, the
  reflex thresholds and the bow-strafing constants. Following the user's "don't go to extremes", they
  move to judgment only when a failure shows they should; the last is a body skill and may stay.
- **Vision is slow** (about 1 to 3 s per look), so it serves judgment, not reaction. Fast reactions still
  run on the parity-filtered state.
- **Model prior knowledge.** The models know Valheim. Validators restrict what plans may name, but
  knowledge can still leak into free text, and the leak has not been measured.
- **Jev and laya** have barely been exercised in the game; distillation to laya has not started.
- **Voice** is not in play; game chat only. The costs doc warns that Live re-bills accumulated context
  every turn.
- **Platform**: macOS only (Apple Silicon needs Rosetta), one Steam account for both games, two game
  clients on one Mac, and one real-game scenario at a time because they share ports and the Steam
  session.
- **Version churn.** The game went from 1.0.16 to 1.0.20 in three weeks; each new build has to pass the
  connection scenarios before the gate lets Thorkell arm.
- **Memory is per world.** Korean and English play should use different worlds so memories do not mix.
- **Eira's main failure, water and coast navigation, has no dedicated real-game scenario in the repo yet.**

## 11. Where to read more

| Topic | File |
|---|---|
| Working rules, hard rules, lessons learned in the game | `AGENTS.md` |
| Feasibility research, Eira, the original design | `docs/research/2026-10-01-thorkell-feasibility.md` |
| Model prices, keys, measured API contracts, free-tier limits | `docs/research/2026-10-02-api-costs-and-keys.md` |
| Game-AI surveys (Korean) | `docs/research/reports/` |
| How first-time humans play to Eikthyr (video study) | `docs/research/2026-10-17-valheim-human-play-observations.md` |
| Game API notes, isolation, real-game findings (section G) | `docs/api/1.0.16.md` |
| Early-game mechanics on 1.0.20 | `docs/api/early-game.md` |
| The Eikthyr companion design and stages | `docs/design/eikthyr-companion.md` |
| Boss runs, run by run | `.claude/handoffs/2026-10-17_23-58.md` |
| Bridge protocol | `protocol/PROTOCOL.md`, `protocol/v1/fixtures/` |
| README video scenarios | `docs/video/readme-scenarios.md` |
| Fight judgment and reflection | `brain/thorkell/plan/tactics.py`, `brain/thorkell/control/fight.py` |
| Memory: facts, episodes, lessons | `brain/thorkell/mind/store.py` |
| Eyes | `brain/thorkell/world/sight.py` |
| Simulator | `brain/thorkell/sim/world.py` |
