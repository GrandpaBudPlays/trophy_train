# 🛡️ Viking 5k Saga (Trophy Train Engine)

**"Train like a hero, record like a skald."**

The Viking 5k Saga is a gamified training engine that transforms raw Garmin telemetry into a Valheim-inspired progression system. This project moves beyond simple "miles logged" to evaluate the quality of your intervals, the intensity of your heart rate, and the consistency of your "raids" through the Meadows of Midgard (Olathe).

---

## 🏰 Current State: Version 1.1 (Interval Precision)

The engine has moved beyond simple lap averages. We now utilize high-resolution time-series telemetry to power our logic.

### ⚔️ Key Features
*   **Interval Precision Analysis:** Distinguishes between jogging and walking phases during interval training (e.g., 2/3 splits) by analyzing cadence samples in `activity_details.json`.
*   **The Conquest Multiplier:** A 1.25x XP boost applied when jogging distance (cadence > 135 SPM) exceeds walking distance.
*   **Multi-Persona Output:** Training reports are interpreted through two lenses:
    *   **Conrad (The Viking):** Atmospheric lore and "blood-price" summaries.
    *   **Grandpa (The Coach):** Technical breakdown of HR zones, cadence, and software stability.
*   **429 Protocol:** Industrial-grade session caching and rate-limit detection to prevent Garmin API lockouts.
*   **Power Law Leveling:** Experience requirements scale exponentially ($XP = Base \times Level^{2.2}$), mirroring physiological diminishing returns.

### 🧪 Technical Stack
*   **Runtime:** Python 3.10+ (WSL / Ubuntu)
*   **Core Logic:** `xp_calculator.py` (The leveling engine)
*   **Data Layer:** `garminconnect` + `trophy_train.py` (Ingestion & Caching)
*   **Persistence:** `save_game.json` (Character state and skill levels)

---

## 🌲 Progression Mechanics

### Skill Trees
| Skill | Metric | RPG Impact |
| :--- | :--- | :--- |
| **Endurance** | Total Distance | Determines Biome access and total Level. |
| **Vitality** | HR Intensity | Reflects cardiovascular efficiency. |
| **Agility** | Cadence/Pace | Earned through high-cadence "skirmish" windows. |
| **Strength** | Elevation Gain | Rewarded for hill climbs and resistance. |

### The Biomes (Roadmap)
1.  **The Meadows (Lvl 1-10):** Base building. *Boss: 1.0mi non-stop run.*
2.  **The Black Forest (Lvl 11-20):** Tempo work. *Boss: 1.5mi at target 5k pace.*
3.  **The Mountains (Lvl 21-30):** Hill intervals. *Boss: 2.0mi at target 5k pace.*
4.  **The Swamp (Lvl 31-40):** The 5k threshold. *Boss: 3.1mi Race.*

---

## 🛠️ Installation & Usage

### Setup
```bash
# Ensure you are in WSL
cd ~/dev/trophy_train
source venv/bin/activate

# Configure credentials
cp .env.example .env # Add GARMIN_EMAIL and GARMIN_PASSWORD
```

### Running a Raid (Ingest Data)
```bash
python trophy_train.py
```
This command fetches the latest activity, caches the summary and detailed telemetry JSONs to `data/`, and displays a technical lap breakdown.

### Recalculating the Saga
```bash
python xp_calculator.py --restart
```
Use this to zero out the `save_game.json` and re-process all cached activities using the latest logic (e.g., after adjusting XP thresholds).

---

## 🚀 Future State: The Great Hall

Planned features currently in development based on the `GEMINI.md` architecture:

### 1. The Great Hall (Streamlit Dashboard)
A LAN-based dashboard to visualize XP growth curves, biome progression, and recent raid narratives.

### 2. The "EverQuest" Decay System
Implementation of `schedule.json` to track consistency.
*   **The Inn:** Scheduled rest days stop XP decay.
*   **Slacker Penalty:** 2x decay for missing a scheduled run.
*   **Well-Rested Buff:** Active recovery on rest days grants a bonus to the next raid.

### 3. SMS Narrative Delivery
Integration with Google Fi Email-to-SMS gateway to receive Conrad's battle reports directly to your phone immediately after a run.

---

## 📜 Project Standards
*   **Offline First:** If the API is blocked, the engine falls back to local JSON caches in `data/`.
*   **Absolute Paths:** All automation (Cron) must use absolute paths to the WSL environment.
*   **State Integrity:** Never manually edit `save_game.json` unless performing a migration.

---
**"The skirmish is over, but the saga is just beginning."**
```

<!--
[PROMPT_SUGGESTION]Refactor xp_calculator.py to implement the Scaling Decay logic as defined in Section 3.C of GEMINI.md.[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Create a basic Streamlit app script for 'The Great Hall' dashboard to visualize current skill levels from save_game.json.[/PROMPT_SUGGESTION]
