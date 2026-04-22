import os
import json
from dotenv import load_dotenv
from garminconnect import Garmin

# Load environment variables
load_dotenv()

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")
token_dir = ".garmin_tokens"

def get_client():
    """Initializes the Garmin client with session caching to avoid 429 errors."""
    client = Garmin(email, password)
    
    # Ensure the token directory exists
    os.makedirs(token_dir, exist_ok=True)
    
    try:
        # Attempt to load existing tokens from the directory
        if os.listdir(token_dir):
            print("Using cached session tokens...")
            client.login(token_dir)
        else:
            print("No cached session found. Logging in...")
            client.login()
            # Save the new session tokens
            client.garth.dump(token_dir)
            print("Session tokens cached.")
            
    except Exception as e:
        print(f"Session failed or expired, attempting fresh login. Error: {e}")
        # If tokens are invalid/expired, try a clean login
        client.login()
        client.garth.dump(token_dir)
    
    return client

try:
    # Initialize connection using the cache logic
    client = get_client()
    
    # Get your display name to confirm it works
    print(f"Connected as: {client.get_full_name()}")
    print("-" * 30)
    
    # Pull last 5 activities
    activities = client.get_activities(0, 5)
    for act in activities:
        # Extract data for Trophy Train
        date = act['startTimeLocal']
        act_type = act['activityType']['typeKey']
        dist_meters = act['distance']
        
        # Convert meters to something more readable for your 5k training
        dist_km = dist_meters / 1000
        
        print(f"Date: {date} | Type: {act_type:10} | Distance: {dist_km:.2f} km")

except Exception as e:
    print(f"Critical Error: {e}")