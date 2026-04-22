import json
import math
from pathlib import Path

# Configuration based on GEMINI.md
BASE_XP = 100
SAVE_GAME_PATH = Path("/home/bud/dev/trophy_train/save_game.json")
ACTIVITY_FILE = Path("/home/bud/dev/trophy_train/data/activity_22608417062.json")

def calculate_xp_requirement(level: int) -> int:
    """
    Applies the Power Law formula: XP_Required = Base * Level^1.5
    Calculates the threshold required to reach the next level.
    """
    if level < 1:
        return BASE_XP
    return math.floor(BASE_XP * math.pow(level, 1.5))

def main():
    if not ACTIVITY_FILE.exists():
        print(f"Error: Activity data not found at {ACTIVITY_FILE}")
        return

    # Load character state and activity data
    with open(SAVE_GAME_PATH, "r") as f:
        save_game = json.load(f)
    
    with open(ACTIVITY_FILE, "r") as f:
        activity = json.load(f)

    # If the JSON is a list, take the first activity
    if isinstance(activity, list):
        activity = activity[0]

    # Initialize aggregated values
    distance_m = 0.0
    duration_s = 0.0
    avg_hr = 0.0
    avg_cadence = 0.0
    max_hr_overall = 0.0 # To gather max HR

    # For weighted averages of HR and Cadence
    total_hr_sum_weighted = 0.0
    total_cadence_sum_weighted = 0.0
    total_duration_for_hr_avg = 0.0
    total_duration_for_cadence_avg = 0.0

    # Attempt to extract data from lapDTOs first, as per GEMINI.md
    laps = activity.get("lapDTOs") or activity.get("laps") # Common keys for laps

    if laps and isinstance(laps, list):
        print("Aggregating data from activity laps...")
        for lap in laps:
            lap_distance = float(lap.get("distance", 0.0))
            lap_duration = float(lap.get("duration", 0.0))
            lap_avg_hr = float(lap.get("averageHeartRate", 0.0))
            lap_avg_cadence = float(lap.get("averageRunningCadenceInStepsPerMinute", 0.0))
            lap_max_hr = float(lap.get("maxHeartRate", 0.0))

            distance_m += lap_distance
            duration_s += lap_duration # Total duration from all laps

            if lap_duration > 0:
                if lap_avg_hr > 0:
                    total_hr_sum_weighted += lap_avg_hr * lap_duration
                    total_duration_for_hr_avg += lap_duration
                if lap_avg_cadence > 0:
                    total_cadence_sum_weighted += lap_avg_cadence * lap_duration
                    total_duration_for_cadence_avg += lap_duration
            
            max_hr_overall = max(max_hr_overall, lap_max_hr)
        
        # Calculate overall averages from aggregated data
        avg_hr = total_hr_sum_weighted / total_duration_for_hr_avg if total_duration_for_hr_avg > 0 else 0.0
        avg_cadence = total_cadence_sum_weighted / total_duration_for_cadence_avg if total_duration_for_cadence_avg > 0 else 0.0

    else:
        # Fallback to summaryDTO or root if no laps found
        print("No laps found, falling back to summary data...")
        def _find_val_summary_fallback(keys):
            for k in keys:
                if k in activity: return activity[k]
                if "summaryDTO" in activity and k in activity["summaryDTO"]:
                    return activity["summaryDTO"][k]
            return 0.0

        distance_m = float(_find_val_summary_fallback(["distance", "sumDistance", "totalDistance"]))
        duration_s = float(_find_val_summary_fallback(["duration", "sumDuration", "elapsedDuration", "activeDuration"]))
        avg_hr = float(_find_val_summary_fallback(["averageHR", "averageHeartRate", "avgHeartRate"]))
        avg_cadence = float(_find_val_summary_fallback(["averageRunningCadenceInStepsPerMinute", "averageCadence", "avgCadence"]))
        max_hr_overall = float(_find_val_summary_fallback(["maxHR", "maxHeartRate"])) # Try to get max HR from summary too

    # 2. Skill XP Calculation Logic (Heuristics for progression)
    # Endurance: 1 XP per 10m run
    # Vitality: Based on HR effort intensity over duration
    # Agility: Based on Cadence efficiency (normalized to 180spm)
    gains = { # Ensure duration_s is not zero to avoid division by zero in XP calculation
        "endurance": int(distance_m / 10),
        "vitality": int((avg_hr / 60) * (duration_s / 60)) if duration_s > 0 else 0,
        "agility": int((avg_cadence / 180) * (duration_s / 60) * 10) if duration_s > 0 else 0
    }

    print(f"--- Processing Raid: {ACTIVITY_FILE.name} ---")
    print(f"Telemetry: {distance_m:.2f}m, {duration_s:.2f}s, Avg HR: {avg_hr:.2f}bpm, Max HR: {max_hr_overall:.2f}bpm, Avg Cadence: {avg_cadence:.2f}spm")
    
    # 3. Leveling Engine
    for skill, xp_gain in gains.items():
        skill_data = save_game["skills"][skill]
        skill_data["xp"] += xp_gain
        print(f"{skill.title()}: +{xp_gain} XP")

        while True:
            # Check if current XP exceeds the requirement for the NEXT level
            next_lv = skill_data["level"] + 1
            req = calculate_xp_requirement(next_lv)
            
            if skill_data["xp"] >= req:
                skill_data["level"] += 1
                skill_data["xp"] -= req
                print(f" >> [LEVEL UP] {skill.upper()} reached level {skill_data['level']}!")
            else:
                break

    # 4. Global Saga Level (Floor average of major skills)
    new_saga_level = sum(s["level"] for s in save_game["skills"].values()) // 3
    if new_saga_level > save_game["current_level"]:
        save_game["current_level"] = new_saga_level
        print(f"\n[!] YOUR SAGA GROWS: Saga Level {save_game['current_level']} reached.")

    # Save updated state back to the save_game.json
    with open(SAVE_GAME_PATH, "w") as f:
        json.dump(save_game, f, indent=4)
    print("\nCharacter state saved to save_game.json")

if __name__ == "__main__":
    main()