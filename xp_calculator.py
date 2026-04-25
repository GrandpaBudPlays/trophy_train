import argparse
import json
import math
from pathlib import Path

# Configuration based on GEMINI.md
BASE_XP = 100
SAVE_GAME_PATH = Path("/home/bud/dev/trophy_train/save_game.json")
DATA_DIR = Path("/home/bud/dev/trophy_train/data")
JOGGING_THRESHOLD = 135  # Revised from 140 for 2/3 interval training

def calculate_xp_requirement(level: int) -> int:
    """
    Applies the Power Law formula: XP_Required = Base * Level^2.2
    Calculates the threshold required to reach the next level.
    """
    if level < 1:
        return BASE_XP
    return math.floor(BASE_XP * math.pow(level, 2.2))

def _process_interval_telemetry(details_path):
    """Parses detailed telemetry to return (run_dist, walk_dist, agility_xp)."""
    try:
        with open(details_path, "r") as f:
            detailed_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

    if isinstance(detailed_data, list) and len(detailed_data) > 0:
        detailed_data = detailed_data[0]

    descriptors = detailed_data.get("metricDescriptors", [])
    metrics = detailed_data.get("activityDetailMetrics", [])

    # Priority Sorted Key Lookups
    cad_keys = ["directdoublecadence", "directstepcount", "cadence", "directruncadence", "runningcadence"]
    dist_keys = ["sumdistance", "distance", "totaldistance", "sum_distance"]
    dur_keys = ["sumelapsedduration", "sumduration", "elapsedduration"]

    cad_idx = -1
    for pk in cad_keys:
        idx = next((d.get("metricsIndex") for d in descriptors if d.get("key", "").lower() == pk), -1)
        if idx != -1:
            cad_idx = idx
            break

    dist_idx = next((d.get("metricsIndex") for d in descriptors if d.get("key", "").lower() in dist_keys), -1)
    dur_idx = next((d.get("metricsIndex") for d in descriptors if d.get("key", "").lower() in dur_keys), -1)

    if not metrics or cad_idx == -1 or dist_idx == -1 or dur_idx == -1:
        return None

    precise_run_dist = 0.0
    precise_walk_dist = 0.0
    precise_agility_xp = 0.0
    prev_d, prev_t = 0.0, 0.0

    for m in metrics:
        vals = m.get("metrics", [])
        if len(vals) > max(cad_idx, dist_idx, dur_idx):
            c, d, t = vals[cad_idx], vals[dist_idx], vals[dur_idx]
            
            if d is None or t is None:
                continue

            c_val = c or 0
            delta_d = d - prev_d
            delta_t = t - prev_t

            if delta_t <= 0 or delta_d < 0:
                prev_d, prev_t = d, t
                continue

            # Agility XP is awarded for all movement, scaled by cadence intensity.
            precise_agility_xp += (c_val / 180) * (delta_t / 60) * 10

            if c_val >= JOGGING_THRESHOLD:
                precise_run_dist += delta_d
            else:
                precise_walk_dist += delta_d
                
            prev_d, prev_t = d, t

    return {
        "run_dist": precise_run_dist,
        "walk_dist": precise_walk_dist,
        "agility_xp": int(precise_agility_xp),
        "descriptors": [d.get("key") for d in descriptors]
    }

def main():
    parser = argparse.ArgumentParser(description="Viking 5k XP Calculator")
    parser.add_argument("--restart", action="store_true", help="Zero out save game and reprocess all activities")
    args = parser.parse_args()

    # Load character state
    with open(SAVE_GAME_PATH, "r") as f:
        save_game = json.load(f)

    # Find activities in the data directory
    activity_files = [f for f in DATA_DIR.glob("activity_*.json") if "_details" not in f.name]
    
    if not activity_files:
        print(f"Error: No activity data found in {DATA_DIR}")
        return

    if args.restart:
        print("\n--- [!] RESTARTING SAGA: Zeroing out progress and recalculating all raids ---")
        save_game["current_level"] = 0
        save_game["processed_activities"] = []
        save_game["skills"] = {
            "endurance": {"level": 0, "xp": 0},
            "vitality": {"level": 0, "xp": 0},
            "agility": {"level": 0, "xp": 0},
            "strength": {"level": 0, "xp": 0}
        }
        if "status" in save_game:
            save_game["status"]["interval_success_count"] = 0
            save_game["status"]["streak_days"] = 0

        # Process all activities in order of creation/discovery
        activities_to_process = sorted(activity_files, key=lambda f: f.stat().st_mtime)
    else:
        # Only process the single latest activity
        latest_activity_path = max(activity_files, key=lambda f: f.stat().st_mtime)
        activities_to_process = [latest_activity_path]

    for activity_path in activities_to_process:
        # Extract activity ID and handle initialization
        activity_id_str = activity_path.stem.replace("activity_", "")
        if "processed_activities" not in save_game:
            save_game["processed_activities"] = []
        if "strength" not in save_game["skills"]:
            save_game["skills"]["strength"] = {"level": 0, "xp": 0}

        # Initialize new metrics block to prevent KeyError
        if "status" not in save_game:
            save_game["status"] = {}
        if "interval_success_count" not in save_game["status"]:
            save_game["status"]["interval_success_count"] = 0

        if activity_id_str in save_game["processed_activities"]:
            if not args.restart:
                print(f"Activity {activity_id_str} already processed. Skipping.")
            continue
        
        with open(activity_path, "r") as f:
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
        total_elevation_gain = 0.0

        # For weighted averages of HR and Cadence
        total_hr_sum_weighted = 0.0
        total_cadence_sum_weighted = 0.0
        total_duration_for_hr_avg = 0.0
        total_duration_for_cadence_avg = 0.0

        # For Run/Walk Dominance
        run_dist = 0.0
        walk_dist = 0.0

        # Attempt to extract data from lapDTOs first, as per GEMINI.md
        laps = activity.get("lapDTOs") or activity.get("laps") # Common keys for laps

        if laps and isinstance(laps, list):
            print(f"Aggregating data from laps for {activity_path.name}...")
            for lap in laps:
                lap_distance = float(lap.get("distance", 0.0)) # meters
                lap_duration = float(lap.get("duration", 0.0)) # seconds
                lap_avg_hr = float(lap.get("averageHR", 0.0)) # bpm
                lap_avg_cadence = float(lap.get("averageRunCadence", 0.0)) # steps per minute
                lap_max_hr = float(lap.get("maxHR", 0.0)) # bpm
                lap_elevation_gain = float(lap.get("elevationGain", 0.0)) # meters

                distance_m += lap_distance
                duration_s += lap_duration
                total_elevation_gain += lap_elevation_gain

                if lap_duration > 0:
                    if lap_avg_hr > 0:
                        total_hr_sum_weighted += lap_avg_hr * lap_duration
                        total_duration_for_hr_avg += lap_duration
                    if lap_avg_cadence > 0:
                        total_cadence_sum_weighted += lap_avg_cadence * lap_duration
                        total_duration_for_cadence_avg += lap_duration
                
                # Run/Walk Dominance Logic
                if lap_avg_cadence >= JOGGING_THRESHOLD:
                    run_dist += lap_distance
                else:
                    walk_dist += lap_distance
                
                max_hr_overall = max(max_hr_overall, lap_max_hr)
            
            # Calculate overall averages from aggregated data
            avg_hr = total_hr_sum_weighted / total_duration_for_hr_avg if total_duration_for_hr_avg > 0 else 0.0
            avg_cadence = total_cadence_sum_weighted / total_duration_for_cadence_avg if total_duration_for_cadence_avg > 0 else 0.0

        else:
            # Fallback to summaryDTO or root if no laps found
            print(f"No laps found for {activity_path.name}, falling back to summary data...")
            def _find_val_summary_fallback(keys):
                for k in keys:
                    if k in activity: return activity[k]
                    if "summaryDTO" in activity and k in activity["summaryDTO"]:
                        return activity["summaryDTO"][k]
                return 0.0

            distance_m = float(_find_val_summary_fallback(["distance", "sumDistance", "totalDistance"]))
            duration_s = float(_find_val_summary_fallback(["duration", "sumDuration", "elapsedDuration", "activeDuration"]))
            avg_hr = float(_find_val_summary_fallback(["averageHR", "avgHeartRate"]))
            avg_cadence = float(_find_val_summary_fallback(["averageRunCadence", "averageCadence", "avgCadence"]))
            max_hr_overall = float(_find_val_summary_fallback(["maxHR"]))
            total_elevation_gain = float(_find_val_summary_fallback(["elevationGain", "totalElevationGain"]))

        # 2. Skill XP Calculation Logic
        gains = { 
            "endurance": int(distance_m / 10),
            "vitality": int((avg_hr / 60) * (duration_s / 60)) if duration_s > 0 else 0,
            "agility": int((avg_cadence / 180) * (duration_s / 60) * 10) if duration_s > 0 else 0,
            "strength": int(total_elevation_gain * 0.1)
        }

        # 2b. Refined Analysis (Time-Series) if detailed data exists
        details_path = DATA_DIR / f"activity_{activity_id_str}_details.json"
        if details_path.exists():
            print(f"[Grandpa] Engaging Interval Precision analysis for activity {activity_id_str}...")
            results = _process_interval_telemetry(details_path)
            
            if results:
                print(f"[Grandpa] Interval Precision: Run Dist: {results['run_dist']:.0f}m | Walk Dist: {results['walk_dist']:.0f}m")
                print(f"[Conrad] The skalds confirm: {results['run_dist']:.0f} meters of jogging in this raid.")
                
                run_dist = results['run_dist']
                walk_dist = results['walk_dist']
                gains["agility"] = results['agility_xp']
                save_game["status"]["interval_success_count"] += int(run_dist // 400)
            else:
                print(f"[Grandpa] Warning: Critical telemetry metrics missing or corrupted in detailed file.")
                print(f"          Falling back to Lap summaries.")
        else:
            print(f"[Grandpa] Historical note: Detailed telemetry missing for raid {activity_id_str}. Utilizing Lap summaries.")

        # Apply Conquest Multiplier if run_dist > walk_dist
        conquest_multiplier = 1.0
        if run_dist > walk_dist:
            conquest_multiplier = 1.25
            print(f" [!] CONQUEST MULTIPLIER (1.25x) applied! Run dist ({run_dist:.0f}m) > Walk dist ({walk_dist:.0f}m).")
            for skill in gains:
                gains[skill] = int(gains[skill] * conquest_multiplier)
        
        print(f"--- Processing Raid: {activity_path.name} ---")
        print(f"Telemetry: {distance_m:.2f}m, {duration_s:.2f}s, Avg HR: {avg_hr:.2f}bpm, Avg Cadence: {avg_cadence:.2f}spm")
        
        # 3. Leveling Engine
        for skill, xp_gain in gains.items():
            skill_data = save_game["skills"][skill]
            skill_data["xp"] += xp_gain
            print(f"{skill.title()}: +{xp_gain} XP")

            while True:
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

        save_game["processed_activities"].append(activity_id_str) 

    # Save updated state back to save_game.json after processing is complete
    with open(SAVE_GAME_PATH, "w") as f:
        json.dump(save_game, f, indent=4)
    print("\nCharacter state saved to save_game.json")

if __name__ == "__main__":
    main()