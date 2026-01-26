import json
import os
from app import create_app, db
from app.models import Trip, Response

def migrate():
    json_path = "trips.json"
    if not os.path.exists(json_path):
        print("No trips.json found.")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    app = create_app()
    with app.app_context():
        print(f"Migrating {len(data)} trips...")
        for trip_id, trip_data in data.items():
            if Trip.query.get(trip_id):
                print(f"Trip {trip_id} already exists, skipping.")
                continue

            # Create Trip
            t = Trip(
                id=trip_id,
                name=trip_data.get("name", "Untitled"),
                creator_name=trip_data.get("creator"),
                durations=trip_data.get("durations", []),
                seasons=trip_data.get("seasons", []),
                locations=trip_data.get("locations", []),
                location_details=trip_data.get("location_details", {})
            )
            db.session.add(t)
            
            # Create Responses
            for resp_data in trip_data.get("responses", []):
                r = Response(
                    trip_id=trip_id,
                    participant_name=resp_data.get("name"),
                    location=resp_data.get("location"),
                    duration=resp_data.get("duration"),
                    seasons=resp_data.get("seasons", []),
                    dates=resp_data.get("dates", [])
                )
                db.session.add(r)
        
        db.session.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
