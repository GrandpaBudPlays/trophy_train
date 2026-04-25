import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from garminconnect import Garmin

# Load environment variables
load_dotenv()

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")
token_dir = ".garmin_tokens"
data_dir = "data"

def get_client():
    """Initializes the Garmin client with session caching to avoid 429 errors."""
    client = Garmin(email, password)
    
    os.makedirs(token_dir, exist_ok=True)
    limit_file = os.path.join(token_dir, "rate_limit.json")
    
    # 1. Try to load an existing session from cache
    token_files = [f for f in os.listdir(token_dir) if f != "rate_limit.json"]
    if token_files:
        try:
            print("Attempting to use cached session tokens...")
            client.login(token_dir)
            if os.path.exists(limit_file):
                os.remove(limit_file)
            return client
        except Exception as e:
            print(f"Cached session expired or invalid: {e}")

    # 2. Check for rate limit block before fresh login
    if os.path.exists(limit_file):
        try:
            with open(limit_file, 'r') as f:
                data = json.load(f)
                blocked_at = datetime.fromisoformat(data['blocked_at'])
                if datetime.now() < blocked_at + timedelta(hours=24):
                    remaining = (blocked_at + timedelta(hours=24)) - datetime.now()
                    print(f"\n[!] Rate limit block in effect until {blocked_at + timedelta(hours=24)}")
                    print(f"Time remaining: {remaining}")
                    return None
        except Exception:
            pass

    # 3. If no cache or cache failed, perform a fresh login
    print("No valid cached session found. Logging in fresh...")
    try:
        client.login()
        
        # Check if we actually have OAuth tokens to save
        # (Mobile login must succeed for garth to have tokens)
        if hasattr(client, 'garth') and client.garth.oauth2_token:
            client.garth.dump(token_dir)
            print("New session tokens cached.")
        else:
            print("\n[!] Warning: Logged in via Web fallback, but Mobile tokens were not generated.")
            print("    This usually means Garmin is rate-limiting your IP (429).")
            print("    Caching will be disabled until the Mobile API allows a fresh login.")
            # Record this as a block to protect your IP
            raise Exception("429: Mobile tokens missing")
            
    except Exception as e:
        if "429" in str(e) or "garth" in str(e):
            print(f"\n[!] ERROR: Rate Limited (429). Recorded block at {datetime.now()}.")
            with open(limit_file, 'w') as f:
                json.dump({'blocked_at': datetime.now().isoformat()}, f)
            print("Fresh login attempts are now disabled for 24 hours.")
        else:
            print(f"\n[!] Login failed: {e}")
        return None
    
    return client

def display_activity_details(client, activity_id, show_laps=True):
    """Fetches and prints the laps/splits for a specific activity."""
    os.makedirs(data_dir, exist_ok=True)
    cache_path = os.path.join(data_dir, f"activity_{activity_id}.json")
    details_cache_path = os.path.join(data_dir, f"activity_{activity_id}_details.json")

    # 1. Check local cache for Summary Data
    if os.path.exists(cache_path):
        print(f"Loading activity {activity_id} from local cache...")
        with open(cache_path, 'r') as f:
            details = json.load(f)
    else:
        if client is None:
            print(f"[Grandpa] Error: Activity {activity_id} not in cache and no API client available.")
            return

        print(f"[Grandpa] Fetching activity {activity_id} from Garmin API...")
        details = client.get_activity_splits(activity_id)
        with open(cache_path, 'w') as f:
            json.dump(details, f, indent=4)
        print(f"[Grandpa] Summary cached to {data_dir}/")
    
    # 2. Check local cache for Granular Time-Series Data (Interval Precision)
    if not os.path.exists(details_cache_path):
        if client:
            print(f"[Grandpa] Downloading time-series telemetry for Activity {activity_id}...")
            try:
                granular_details = client.get_activity_details(activity_id)
                with open(details_cache_path, 'w') as f:
                    json.dump(granular_details, f, indent=4)
                print(f"[Conrad] The skalds have recorded the precise rhythm of your stride.")
            except Exception as e:
                # Log the error but don't fail; we can fall back to lap data
                print(f"[Grandpa] Warning: Could not fetch granular details: {e}")
        else:
            print(f"[Grandpa] Granular data missing and no API connection. Falling back to summary.")
    else:
        print(f"[Grandpa] Detailed telemetry for {activity_id} found in archives.")
        print(f"[Conrad] The saga's fine details are already known.")

    # If we are just backfilling history, skip the console output
    if not show_laps:
        return

    print(f"\n--- Lap Details for Activity {activity_id} ---")
    print(f"{'Lap':<4} | {'Time(s)':<8} | {'Dist(m)':<8} | {'Pace(km)':<8} | {'Dist(mi)':<8} | {'Pace(mi)':<8}")
    print("-" * 65)
    
    # Consistency Check: Use same fallback keys as xp_calculator.py
    laps = details.get('lapDTOs') or details.get('lapSummaries') or details.get('laps') or []
    
    if not laps:
        print("No lap data (summaries or DTOs) found for this activity.")
        return

    for i, lap in enumerate(laps, 1):
        dist = lap.get('distance', 0)
        duration = lap.get('duration', 0)
        
        if dist > 0:
            # Metric Logic (KM)
            pace_min_km = (duration / 60) / (dist / 1000)
            min_km = int(pace_min_km)
            sec_km = int((pace_min_km - min_km) * 60)
            pace_km_str = f"{min_km}:{sec_km:02d}"
            
            # Imperial Logic (Miles)
            dist_mi = dist * 0.000621371
            pace_min_mi = (duration / 60) / dist_mi
            min_mi = int(pace_min_mi)
            sec_mi = int((pace_min_mi - min_mi) * 60)
            pace_mi_str = f"{min_mi}:{sec_mi:02d}"
        else:
            pace_km_str = "N/A"
            dist_mi = 0
            pace_mi_str = "N/A"
            
        print(f"{i:<4} | {duration:<8.1f} | {dist:<8.1f} | {pace_km_str:<8} | {dist_mi:<8.2f} | {pace_mi_str:<8}")

try:
    # Initialize connection using the cache logic
    client = get_client()
    
    if client is None:
        print("\n[!] Login failed or Rate Limited. Checking for archived data...")
        if os.path.exists(data_dir):
            archived_files = [f for f in os.listdir(data_dir) if f.startswith("activity_") and f.endswith(".json")]
            if archived_files:
                # Sort by file modification time to find the most recently saved activity
                latest_cache = max([os.path.join(data_dir, f) for f in archived_files], key=os.path.getmtime)
                archived_id = os.path.basename(latest_cache).replace("activity_", "").replace(".json", "")
                print(f"Found archived data for Activity {archived_id}.")
                display_activity_details(None, archived_id)
                sys.exit(0)
        
        print("No archived data found. Exiting.")
        sys.exit(1)
        
    # Get your display name to confirm it works
    print(f"Connected as: {client.get_full_name()}")
    print("-" * 30)
    
    # Fetch last 10 activities to ensure historical data is available for recalculations
    print(f"[Grandpa] Checking for recent raids and updating the Great Library...")
    activities = client.get_activities(0, 10)
    
    if activities:
        # 1. Process and display the latest activity
        latest = activities[0]
        print(f"Latest Activity: {latest['activityName']} ({latest['startTimeLocal']})")
        display_activity_details(client, latest['activityId'], show_laps=True)
        
        # 2. Silently backfill detailed metrics for historical activities
        # This ensures xp_calculator.py --restart has the data it needs for "Interval Precision"
        print(f"\n[Grandpa] Filling in detailed metrics for older raids...")
        for act in activities[1:]:
            display_activity_details(client, act['activityId'], show_laps=False)
    else:
        print("No activities found.")

except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)
