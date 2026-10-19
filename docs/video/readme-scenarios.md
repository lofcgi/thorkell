# README video: scenarios

Short clips for the README that show Thorkell playing Valheim with a person, in English. Each clip is
one thing a first-time player would do with a friend, from the friend's screen. Thorkell is never
scripted: the leader only talks in game chat, and Thorkell reads his own screen, decides and acts.

Every scenario has a real-game test with the same lines (`thorkell scenario … --config
thorkell.play.en.toml`), where a harness leader says them in chat and the run checks the outcome in
the world (items in the bag, pieces built, the server's boss-defeated key). Results are at the end.

## Before recording

- Start a new world in English: the app's **English** and **새 월드** boxes (or
  `cd brain && uv run --env-file ../.env thorkell play --rehearsal thorkell-en --new --config thorkell.play.en.toml`).
  Both games load English in memory; the real game's settings are not touched.
- Use a world name you have not used with Korean (Thorkell's memory is kept per world).
- Record the leader's game window. Thorkell's own window (small, 640x360) works as a picture-in-picture:
  it is exactly what he sees. The app's log shows what he decides (`decision`) and says.
- Type in normal chat (Enter). Thorkell answers under his own name; when he is far he shouts.

## 1. Hello, Thorkell (about 1 minute)

Shows: a second player joins and understands plain English.

| Leader types | Thorkell |
|---|---|
| (Thorkell joins) | The game's own "I have arrived!" under his name |
| Thorkell, follow me | Says he's coming and walks over; keeps up as you walk off |
| Stop | Says he'll stop, and stands still |
| Follow me (after walking ~400 m away) | Finds you on the map (needs map sharing on) and comes |
| Hey Thorkell, how are you feeling today? | A short answer of his own, and no moving |

Test: `scenario talk` (steps `follow`, `follow_after_leader_walks_off`, `stop`, `far_follow`,
`small_talk_by_planner`).

## 2. An axe from nothing (2–3 minutes, speed up the middle)

Shows: he starts with empty hands in a new world and works out how to make a tool.

| Leader types | Thorkell |
|---|---|
| Thorkell, could you make us an axe first? There's wood and stone lying around | Picks up branches and stones, sees the axe appear in his crafting menu, makes a Stone Axe and says so |

Test: `scenario fresh` step `makes_an_axe_from_nothing`.

## 3. Wood, and a roof over our heads (3–4 minutes)

Shows: he decides how much is enough, asks before a big job, then builds.

| Leader types | Thorkell |
|---|---|
| Can you chop 20 wood for me? | Equips the axe, fells trees and picks up 20 Wood |
| We should build a house | Does not just start: suggests a size from what he has and asks |
| Yeah, keep it small. Just enough to keep the rain off | Builds a workbench, walls and a roof around it |

Test: `scenario fresh` steps `cuts_twenty_wood`, `answers_about_a_house`, `builds_a_small_shelter`.

## 4. Something to eat, and a deer (3–5 minutes)

Shows: open requests become his own plans; he learns that deer run and sneaks up on them.

| Leader types | Thorkell |
|---|---|
| I'm hungry. Can you find us something to eat? | Looks for food he can see (berries, mushrooms) or hunts |
| Go hunt a deer. We need its trophy | Hunts a deer (crouches and creeps up once he has seen them bolt) and picks up the trophy |

Test: `scenario fresh` steps `finds_something_to_eat`, `hunts_a_deer_for_its_trophy`.

## 5. Eikthyr, together (3–5 minutes)

Shows: the first boss. Nobody tells him how to fight; he looks at what came out and decides.

| Leader types | Thorkell |
|---|---|
| (offer the two deer trophies at the altar) | Notices the boss and its health bar at the top of the screen and says what he makes of it |
| Let's take him down together! I'll hold him up front, you shoot him with the bow from behind | Keeps his distance and shoots, backs off toward you when hurt, and after the fight says what he learned |

Test: `scenario boss --together` (the harness leader stands by the boss bare-handed in test-only god
mode; steps `offer_trophies`, `fight_and_reflect`, `eikthyr_defeated`).

## Test results
