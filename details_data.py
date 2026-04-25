import math
import json
import argparse
from pathlib import Path

# Established paths from trophy_train environment
DATA_DIR = Path("/home/bud/dev/trophy_train/data")

def haversine_distance(lat1, lon1, lat2, lon2):
    # Earth radius in meters
    R = 6371000 
    
    # Convert degrees to radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    # Haversine calculation
    a = math.sin(dphi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c # Result in meters

def inspect_activity_details(activity_id):
    # Garmin detailed telemetry files usually follow this naming convention
    file_path = DATA_DIR / f"activity_{activity_id}_details.json"
    
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        return

    with open(file_path, "r") as f:
        raw_data = json.load(f)

    # Handle case where data might be wrapped in a list
    if isinstance(raw_data, list) and len(raw_data) > 0:
        raw_data = raw_data[0]

    # 1. Map Labels (Descriptors) to Indices
    # Expanded target keys to include the "Double Cadence" found in your specific device profile
    # Order here determines the column order in the display
    target_keys = ["sumElapsedDuration", "sumDistance", "directDoubleCadence", "directHeartRate", "directCadence", "directFractionalCadence"]
    
    descriptors = raw_data.get("metricDescriptors", [])
    metrics_entries = raw_data.get("activityDetailMetrics", [])
    
    # Identify which index each of our target metrics lives in
    mapping = {}
    for tk in target_keys:
        idx = next((d.get("metricsIndex") for d in descriptors if d.get("key", "").lower() == tk.lower()), -1)
        if idx != -1:
            mapping[tk] = idx

    if not mapping or not metrics_entries:
        available = [d.get("key") for d in descriptors]
        print(f"None of the target keys {target_keys} found.")
        print(f"Available keys in this file: {available}")
        return

    # 2. Print Header based on keys found
    header = f"{'Sample':<8}"
    for key in mapping.keys():
        header += f" | {key:<16}"
    print(header)
    print("-" * len(header))

    # 3. Output first 25 rows
    for row_idx, entry in enumerate(metrics_entries[:25]):
        sample = entry.get("metrics", [])
        row_str = f"{row_idx:<8}"
        for key, col_idx in mapping.items():
            val = sample[col_idx] if col_idx is not None and col_idx < len(sample) else "N/A"
            row_str += f" | {str(val):<16}"
        print(row_str)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect raw Garmin telemetry rows")
    parser.add_argument("id", help="The Garmin Activity ID (e.g., 22608417062)")
    args = parser.parse_args()
    
    inspect_activity_details(args.id)
