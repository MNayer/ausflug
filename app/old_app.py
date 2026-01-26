import os
import json
import uuid
from typing import Dict, Any, List, Tuple

import folium
from flask import Flask, render_template, request, redirect, url_for, abort, flash


"""
This Flask application powers a simple trip planning tool.  It allows a user to
create a new trip with configurable options (locations, durations and
seasons).  Once a trip is created the application generates a unique URL for
that trip which can be shared with friends.  Visitors using the link can
select their preferences (destination, trip length, preferred seasons and
available dates).  All trip definitions and responses are persisted to a
JSON file on disk so the information survives restarts.

The frontend uses plain HTML templates with Tailwind/Flowbite for styling
instead of frameworks like React.  JavaScript is only used where strictly
necessary (for the date picker and copy‑to‑clipboard functionality).
"""

# Create the Flask application
app = Flask(__name__)

# Enable the Flask message flashing system.  A secret key is required.
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

# Path to the JSON file used for persisting trips and responses.  It's
# created inside the application root directory so it survives across runs.
DATA_FILE = os.path.join(os.path.dirname(__file__), "trips.json")

# Definition of available cities.  Each entry contains a human friendly
# name as well as the path to an HTML file holding a small interactive map.
# These HTML files are stored in the static folder under "images".
# Predefined cities remain here for backwards compatibility.  They are not
# shown on the trip creation page but may still exist in older trips.
CITIES = {
    "paris": {
        "code": "paris",
        "name": "Paris",
        "src": "images/paris.html",
        "alt": "Map of Paris",
    },
    "berlin": {
        "code": "berlin",
        "name": "Berlin",
        "src": "images/berlin.html",
        "alt": "Map of Berlin",
    },
    "rome": {
        "code": "rome",
        "name": "Rome",
        "src": "images/rome.html",
        "alt": "Map of Rome",
    },
    "london": {
        "code": "london",
        "name": "London",
        "src": "images/london.html",
        "alt": "Map of London",
    },
}

# Definition of the supported trip durations.  These are presented to both
# creators (to restrict choices) and participants (to select their
# preference).
DEFAULT_DURATIONS = ["Day trip", "Weekend", "Full vacation"]

# Definition of the seasons along with corresponding images.  The
# date picker later uses the season names to enable/disable date ranges.
DEFAULT_SEASONS = [
    {"name": "Spring", "image": "images/spring.png"},
    {"name": "Summer", "image": "images/summer.png"},
    {"name": "Fall",   "image": "images/fall.png"},
    {"name": "Winter", "image": "images/winter.png"},
]


def load_trips() -> Dict[str, Any]:
    """Load all trips from the JSON file.  If the file does not exist
    an empty dictionary is returned.  The file stores a mapping from
    trip_id to the trip definition and any responses submitted so far.

    Returns
    -------
    Dict[str, Any]
        A dictionary keyed by trip_id containing trip definitions.
    """
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # If the file cannot be parsed we start fresh.  This situation
        # shouldn't normally occur but ensures the app continues running.
        return {}


def save_trips(trips: Dict[str, Any]) -> None:
    """Persist the trips dictionary back to disk.  The file is
    overwritten atomically to avoid corruption.

    Parameters
    ----------
    trips : Dict[str, Any]
        The dictionary of all trips to write to disk.
    """
    # Write to a temporary file first to avoid truncating the original if
    # something goes wrong while writing.
    tmp_path = DATA_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(trips, f, indent=2)
    os.replace(tmp_path, DATA_FILE)


@app.route("/")
def home():
    """Show the application home page.  This page lists any existing
    trips and offers a link to create a new one.  Listing existing trips
    makes it easy for a creator to revisit a trip or copy its share link.
    """
    trips = load_trips()
    # Convert to a list of (id, data) pairs for templating convenience
    trip_list = []
    for tid, tdata in trips.items():
        trip_list.append({
            "id": tid,
            "name": tdata.get("name") or f"Trip {tid[:6]}",
            "responses": len(tdata.get("responses", [])),
        })
    return render_template("home.html", trips=trip_list)


@app.route("/create", methods=["GET", "POST"])
def create_trip():
    """Handle creation of a new trip.  On GET the user is presented with
    a form to configure the trip.  On POST the submitted data is
    validated, persisted to the JSON file and the user is redirected to
    the planning page for the newly created trip.
    """
    if request.method == "POST":
        # Extract form fields
        trip_name = request.form.get("trip_name", "").strip()
        creator_names = request.form.get("names", "").strip()

        # Read custom destinations.  The user supplies one destination per
        # line in the form "Name,lat,lon".  We parse these lines and
        # generate map HTML files on the fly using folium.  Invalid
        # entries are ignored.
        destinations_input = request.form.get("destinations", "").strip()
        destination_lines = [ln for ln in destinations_input.splitlines() if ln.strip()]

        if not trip_name:
            flash("Please provide a title for your trip.", "error")
            return redirect(url_for("create_trip"))
        if not destination_lines:
            flash("Please enter at least one destination.", "error")
            return redirect(url_for("create_trip"))

        # Generate a unique identifier now so that maps can be stored
        # under a folder for this trip.  This avoids name collisions across
        # multiple trips.
        trip_id = uuid.uuid4().hex

        location_details: Dict[str, Dict[str, str]] = {}
        location_codes: List[str] = []
        # Ensure destination folder exists
        dest_folder = os.path.join(os.path.dirname(__file__), "static", "images", "custom", trip_id)
        os.makedirs(dest_folder, exist_ok=True)

        for line in destination_lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 3:
                continue
            name, lat_str, lon_str = parts
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                continue
            # Create a slug from the name for internal use
            base_slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
            slug = base_slug
            counter = 1
            # Ensure uniqueness of the slug within this trip
            while slug in location_details:
                slug = f"{base_slug}_{counter}"
                counter += 1
            # Build the map using folium
            m = folium.Map(location=[lat, lon], zoom_start=12)
            folium.Marker(location=[lat, lon], popup=name).add_to(m)
            filename = f"{slug}.html"
            filepath = os.path.join(dest_folder, filename)
            m.save(filepath)
            # Relative path for use with url_for('static', ...)
            relative_src = os.path.join("images", "custom", trip_id, filename)
            location_details[slug] = {
                "code": slug,
                "name": name,
                "src": relative_src,
                "alt": f"Map of {name}",
            }
            location_codes.append(slug)

        if not location_codes:
            flash("None of the destinations you provided could be parsed. Please use the format Name,Latitude,Longitude.", "error")
            return redirect(url_for("create_trip"))

        # Get selected durations/seasons as lists.  If nothing is selected
        # treat it as allowing all options.
        selected_durations: List[str] = request.form.getlist("durations")
        selected_seasons: List[str] = request.form.getlist("seasons")

        # Build the trip definition.  We include location_details so that
        # each trip carries its own destination metadata.  The old
        # locations list (codes) is retained for compatibility.
        trip_data = {
            "id": trip_id,
            "name": trip_name,
            "creator": creator_names,
            "locations": location_codes,
            "location_details": location_details,
            "durations": selected_durations if selected_durations else list(DEFAULT_DURATIONS),
            "seasons": selected_seasons if selected_seasons else [s["name"] for s in DEFAULT_SEASONS],
            "responses": [],
        }

        # Persist the trip
        trips = load_trips()
        trips[trip_id] = trip_data
        save_trips(trips)

        # Redirect to the newly created trip's planning page
        return redirect(url_for("plan_trip", trip_id=trip_id))

    # GET request: render the creation form
    # Preselect all options by default
    return render_template(
        "create_trip.html",
        durations=DEFAULT_DURATIONS,
        seasons=DEFAULT_SEASONS,
    )


@app.route("/trip/<trip_id>", methods=["GET", "POST"])
def plan_trip(trip_id: str):
    """Display the planning page for a given trip and handle submissions
    of participant preferences.  If the trip does not exist a 404
    response is returned.

    On POST the submitted preferences are appended to the trip's list
    of responses and persisted to disk.  After submission the user
    receives a thank you message but remains on the same page to
    encourage multiple submissions from different participants.
    """
    trips = load_trips()
    trip = trips.get(trip_id)
    if not trip:
        abort(404)

    # Convert stored codes into full objects for templating convenience
    # Build a list of allowed location objects.  If the trip was created
    # with custom destinations it will carry a location_details mapping.
    if "location_details" in trip:
        allowed_locations = list(trip["location_details"].values())
        location_details_map = trip["location_details"]
    else:
        # Fall back to predefined cities for older trips.  Construct a
        # location_details_map for convenience so templates can look up
        # names, etc.
        allowed_locations = [CITIES[code] for code in trip.get("locations", []) if code in CITIES]
        location_details_map = {code: CITIES[code] for code in trip.get("locations", []) if code in CITIES}

    allowed_durations = trip.get("durations", [])
    allowed_season_names = trip.get("seasons", [])
    allowed_seasons = [s for s in DEFAULT_SEASONS if s["name"] in allowed_season_names]

    # Determine allowed months based on allowed seasons.  Each season maps
    # to specific months in the year 2025.  We remove duplicates while
    # preserving order.
    season_to_months = {
        "Winter": ["December"],
        "Spring": ["March", "April", "May"],
        "Summer": ["June", "July", "August"],
        "Fall":   ["September", "October", "November"],
    }
    seen = set()
    allowed_months = []
    for s in allowed_season_names:
        for month in season_to_months.get(s, []):
            if month not in seen:
                allowed_months.append(month)
                seen.add(month)

    if request.method == "POST":
        # Read participant's selections
        selected_location = request.form.get("location")
        selected_duration = request.form.get("duration")
        selected_seasons = request.form.getlist("seasons")
        selected_dates_str = request.form.get("dates", "").strip()
        # Name is optional
        participant_name = request.form.get("participant_name", "").strip() or None

        # Validate required fields.  Location and duration are required
        # unless there is only one choice available in which case the
        # values are prefilled hidden inputs.
        errors: List[str] = []
        if len(allowed_locations) > 1 and not selected_location:
            errors.append("Missing selection: destination.")
        if len(allowed_durations) > 1 and not selected_duration:
            errors.append("Missing selection: duration.")
        # Dates are always required because they are used to find overlap
        # between participants.
        if not selected_dates_str:
            errors.append("Missing selection: at least one available date.")
        if errors:
            for e in errors:
                flash(e, "error")
            # redisplay the form with flashed errors
            return redirect(url_for("plan_trip", trip_id=trip_id))

        # Construct the response object.  If there are multiple seasons
        # allowed but none were selected we interpret that as the
        # participant being open to any allowed season.
        # Build list of selected date strings from the date picker.  When the
        # user selects multiple dates FlexiDatepicker returns a comma
        # separated list in the input value.  Split on comma and strip
        # whitespace.  If no dates were chosen the list is empty.
        selected_dates = [d.strip() for d in selected_dates_str.split(",") if d.strip()] if selected_dates_str else []

        response = {
            "name": participant_name,
            "location": selected_location if selected_location else allowed_locations[0]["code"],
            "duration": selected_duration if selected_duration else allowed_durations[0],
            # Seasons: if none selected treat as all allowed
            "seasons": selected_seasons if selected_seasons else allowed_season_names,
            "dates": selected_dates,
        }

        # Append to stored responses and persist
        trip.setdefault("responses", []).append(response)
        trips[trip_id] = trip
        save_trips(trips)

        flash("Your preferences have been recorded.  Thank you!", "success")
        # Stay on the same page to allow others to submit
        return redirect(url_for("plan_trip", trip_id=trip_id))

    # GET request: render the planning page
    # The full URL for sharing includes scheme/host/port and the trip path
    share_url = request.url

        # Aggregate responses to present simple statistics.  We count
        # how many times each option has been chosen so far.  Months
        # aggregation is also handled to surface the most popular months.
    response_summary = {
        "locations": {},
        "durations": {},
        "seasons": {},
        "months": {},
        "dates": {},
    }
    for resp in trip.get("responses", []):
        loc = resp.get("location")
        response_summary["locations"][loc] = response_summary["locations"].get(loc, 0) + 1
        dur = resp.get("duration")
        response_summary["durations"][dur] = response_summary["durations"].get(dur, 0) + 1
        for s in resp.get("seasons", []):
            response_summary["seasons"][s] = response_summary["seasons"].get(s, 0) + 1
        # Months may come from 'months' list or we derive from 'dates' list
        months = resp.get("months")
        if not months and resp.get("dates"):
            # derive month names from date strings YYYY-MM-DD
            derived_months: List[str] = []
            for d in resp.get("dates", []):
                try:
                    month_num = int(d.split("-")[1])
                    # map month number to name
                    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                    derived_months.append(month_names[month_num - 1])
                except Exception:
                    continue
            months = derived_months
        for m in months or []:
            response_summary["months"][m] = response_summary["months"].get(m, 0) + 1

        # Count each individual date chosen by participants
        for date_str in resp.get("dates", []):
            response_summary["dates"][date_str] = response_summary["dates"].get(date_str, 0) + 1

    # Sort each category by descending count for better presentation
    sorted_locations: List[Tuple[str, int]] = sorted(response_summary["locations"].items(), key=lambda x: x[1], reverse=True)
    sorted_durations: List[Tuple[str, int]] = sorted(response_summary["durations"].items(), key=lambda x: x[1], reverse=True)
    sorted_seasons: List[Tuple[str, int]] = sorted(response_summary["seasons"].items(), key=lambda x: x[1], reverse=True)
    sorted_months: List[Tuple[str, int]] = sorted(response_summary["months"].items(), key=lambda x: x[1], reverse=True)
    sorted_dates: List[Tuple[str, int]] = sorted(response_summary["dates"].items(), key=lambda x: x[1], reverse=True)
    # Only display top 5 dates to avoid overwhelming the UI
    sorted_dates_top = sorted_dates[:5]
    totals = {
        "locations": sum(response_summary["locations"].values()),
        "durations": sum(response_summary["durations"].values()),
        "seasons": sum(response_summary["seasons"].values()),
        "months": sum(response_summary["months"].values()),
        "dates": sum(response_summary["dates"].values()),
    }

    return render_template(
        "plan_trip.html",
        trip=trip,
        allowed_locations=allowed_locations,
        allowed_durations=allowed_durations,
        # Used to render the full duration list even when the trip only allows
        # a single duration (locked during trip creation).
        all_durations=list(DEFAULT_DURATIONS),
        allowed_seasons=allowed_seasons,
        allowed_months=allowed_months,
        share_url=share_url,
        sorted_locations=sorted_locations,
        sorted_durations=sorted_durations,
        sorted_seasons=sorted_seasons,
        sorted_months=sorted_months,
        sorted_dates=sorted_dates,
        sorted_dates_top=sorted_dates_top,
        totals=totals,
        location_details=location_details_map,
    )


if __name__ == "__main__":  # pragma: no cover
    # When run directly, launch the development server on port 5000.  In
    # production a WSGI server (e.g. gunicorn) should be used instead.
    app.run(host="0.0.0.0", port=5000, debug=True)
