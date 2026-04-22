# Project: Viking 5k Saga (Tropy Train Engine)
**Role:** AI Context & System Architecture Definition
**Focus:** Gamification of 5k training via Garmin data, Valheim-style progression, and EverQuest-style stakes.

## 1. Technical Stack & Environment
- **OS:** Windows Subsystem for Linux (WSL) - Ubuntu
- **Language:** Python 3.10+
- **Environment:** VENV located at `./venv`
- **Primary Libraries:**
    - `garminconnect`: API Interaction (Mobile session emulation).
    - `python-dotenv`: Credential Management.
    - `pandas`: Data processing and skill tree math.
    - `streamlit`: LAN-based dashboard ("The Great Hall").
- **Automation:** Cron job running daily at 7:00 PM in WSL.
- **Notification:** Google Fi Email-to-SMS gateway (`[number]@msg.fi.google.com`).

## 2. Core Project Rules & Standards
- **Virtual Environment:** Always execute using the interpreter at `./venv/bin/python`.
- **API Resilience (Rate Limit Protocol):** - **Session Caching:** Use `get_client()` with token-based caching in `.garmin_tokens/`.
    - **429 Lockout:** If a `429 Too Many Requests` is encountered, record the timestamp in `rate_limit.json`. Prohibit fresh login attempts for 24 hours.
    - **Token Validation:** Verify `client.garth.oauth2_token` exists after login to ensure "Mobile" session establishment for persistent caching.
- **Offline Fallback:** If the API is unreachable or blocked, the system must scan the `data/` directory and use the most recent `activity_{id}.json` file for processing.
- **Data Security:** `.env` and `.garmin_tokens/` are strictly excluded from version control.

## 3. The "Viking 5k" Game Mechanics
The training cycle is modeled as a 40-level saga divided into Biomes, gated by "Boss Fights."

### A. Progression & Biomes
1. **The Meadows (Levels 1–10):** Base building. Boss: 1.5-mile non-stop run.
2. **The Black Forest (Levels 11–20):** Hills and intervals. Boss: 2-mile hill challenge.
3. **The Swamp/Mountains (Levels 21–30):** Endurance/Intensity. Boss: 3 miles at 5k target pace.
4. **The Plains (Level 30):** The 5k Race.
5. **Ashlands/Prestige (Levels 31–40):** Elite performance and placement markers.

### B. Leveling Math (The Power Law)
To mirror physiological diminishing returns, leveling is exponential.
- **Formula:** $XP_{Required} = Base \times Level^{1.5}$
- **Skills:** Level independently based on Garmin telemetry:
    - **Endurance:** Derived from total distance.
    - **Vitality:** Derived from Heart Rate Zones.
    - **Agility:** Derived from Pace and Cadence.

### C. The "EverQuest" Decay System
Status is separate from Skills and tracks consistency.
- **Scaling Decay:** Harsher penalties at higher levels: $Decay = Base\_Rate \times (1 + \frac{Current\_Level}{10})^2$
- **The Inn (Scheduled Rest):** Rest days are defined in `schedule.json`.
    - **At the Inn:** 0% Decay on scheduled rest days.
    - **Slacker Penalty:** 200% (2x) Decay for missing a scheduled run day.
    - **Active Recovery:** Light movement on rest days grants the "Well-Rested" buff (decay reduction).

## 4. Logic Layer & Implementation Flow

### 1. Authentication & Ingestion
The system follows the `get_client` flow: Cache Check -> Lockout Check -> Fresh Login -> Persistence. Once authenticated, it fetches the latest activity and saves it to `data/activity_{id}.json`.

### 2. Data Interpretation
The engine must parse `lapDTOs` or `lapSummaries` to extract:
- **Distance:** Calculate Metric (m/km) and Imperial (mi).
- **Pace:** `(duration / 60) / distance`.
- **Heart Rate:** Identify time spent in Peak vs. Aerobic zones.
- **Cadence:** Track average vs. max bursts for Agility XP.

### 3. State Management (`save_game.json`)
The source of truth for the character state.
- Tracks `current_level`, `skill_xp`, `current_biome`, and `boss_flags`.
- Updates daily based on the interaction between the Garmin JSON and the `schedule.json`.

## 5. Narrative Engine (Dual Personas)
Every update must be processed into a "Daily Saga" via an LLM using these specific definitions:

- **Conrad (The Viking):** Lore-heavy, atmospheric character. He views Olathe as the Meadows of Midgard. He describes physical exhaustion as "blood-price" and runs as "raids."
- **Grandpa (The Coach):** Technical, straightforward, and encouraging. He focuses on Garmin metrics (HR zones, cadence, recovery times) and software developer-style technical feedback.

## 6. Directory Structure
```text
~/dev/trophy_train/
├── trophy_train.py      # Core execution engine
├── .garmin_tokens/      # Session tokens and rate_limit.json
├── .env                 # API Credentials (GARMIN_EMAIL, GARMIN_PASSWORD)
├── schedule.json        # User-defined training/rest calendar
├── save_game.json       # Persistent character state
├── data/                # Raw activity JSON cache
└── narratives/          # History of generated Sagas
