import os
import uuid
import folium
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, make_response
from .extensions import db
from .models import Trip, Response

main_bp = Blueprint('main', __name__)

DEFAULT_DURATIONS = ["Day trip", "Weekend", "Full vacation"]
DEFAULT_SEASONS = [
    {"name": "Spring", "image": "images/spring.png"},
    {"name": "Summer", "image": "images/summer.png"},
    {"name": "Fall",   "image": "images/fall.png"},
    {"name": "Winter", "image": "images/winter.png"},
]

# Legacy Cities constant for backward compatibility or defaults
CITIES = {
    "paris": {"code": "paris", "name": "Paris", "src": "images/paris.html", "alt": "Map of Paris"},
    "berlin": {"code": "berlin", "name": "Berlin", "src": "images/berlin.html", "alt": "Map of Berlin"},
    "rome": {"code": "rome", "name": "Rome", "src": "images/rome.html", "alt": "Map of Rome"},
    "london": {"code": "london", "name": "London", "src": "images/london.html", "alt": "Map of London"},
}

@main_bp.route("/")
def home():
    # Privacy: Only show trips the user has created or visited (stored in cookie)
    my_trips_cookie = request.cookies.get('my_trips')
    my_trip_ids = []
    if my_trips_cookie:
        try:
            my_trip_ids = json.loads(my_trips_cookie)
        except:
            my_trip_ids = []
    
    if my_trip_ids:
        trips = Trip.query.filter(Trip.id.in_(my_trip_ids)).all()
    else:
        trips = []

    trip_list = []
    for t in trips:
        trip_list.append({
            "id": t.id,
            "name": t.name or f"Trip {t.id[:6]}",
            "responses": len(t.responses),
        })
    return render_template("home.html", trips=trip_list)

@main_bp.route("/create", methods=["GET", "POST"])
def create_trip():
    if request.method == "POST":
        trip_name = request.form.get("trip_name", "").strip()
        creator_names = request.form.get("names", "").strip()
        destinations_input = request.form.get("destinations", "").strip()
        
        if not trip_name:
            flash("Please provide a title for your trip.", "error")
            return redirect(url_for("main.create_trip"))
        
        destination_lines = [ln for ln in destinations_input.splitlines() if ln.strip()]
        if not destination_lines:
             flash("Please enter at least one destination.", "error")
             return redirect(url_for("main.create_trip"))

        trip_id = uuid.uuid4().hex
        location_details = {}
        location_codes = []
        
        # Ensure destination folder exists (using current_app.root_path to locate static folder correctly)
        # We assume app/static structure
        static_folder = os.path.join(current_app.root_path, "static")
        dest_folder = os.path.join(static_folder, "images", "custom", trip_id)
        os.makedirs(dest_folder, exist_ok=True)

        for line in destination_lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 3: continue
            name, lat_str, lon_str = parts
            try:
                lat, lon = float(lat_str), float(lon_str)
            except ValueError: continue
                
            base_slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
            slug = base_slug
            counter = 1
            while slug in location_details:
                slug = f"{base_slug}_{counter}"
                counter += 1
            
            m = folium.Map(location=[lat, lon], zoom_start=12)
            folium.Marker(location=[lat, lon], popup=name).add_to(m)
            filename = f"{slug}.html"
            filepath = os.path.join(dest_folder, filename)
            m.save(filepath)
            
            relative_src = os.path.join("images", "custom", trip_id, filename)
            location_details[slug] = {
                "code": slug, "name": name, "src": relative_src, "alt": f"Map of {name}"
            }
            location_codes.append(slug)

        if not location_codes:
            flash("None of the destinations could be parsed.", "error")
            return redirect(url_for("main.create_trip"))

        selected_durations = request.form.getlist("durations")
        selected_seasons = request.form.getlist("seasons")

        new_trip = Trip(
            id=trip_id,
            name=trip_name,
            creator_name=creator_names,
            durations=selected_durations if selected_durations else list(DEFAULT_DURATIONS),
            seasons=selected_seasons if selected_seasons else [s["name"] for s in DEFAULT_SEASONS],
            locations=location_codes,
            location_details=location_details
        )
        db.session.add(new_trip)
        db.session.commit()
        
        # Cookie Logic: Add new trip to my_trips
        response = make_response(redirect(url_for("main.plan_trip", trip_id=trip_id)))
        my_trips_cookie = request.cookies.get('my_trips')
        try:
            my_ids = json.loads(my_trips_cookie) if my_trips_cookie else []
        except:
            my_ids = []
            
        if trip_id not in my_ids:
            my_ids.append(trip_id)
            
        response.set_cookie('my_trips', json.dumps(my_ids), max_age=60*60*24*365) # 1 year
        return response

    return render_template("create_trip.html", durations=DEFAULT_DURATIONS, seasons=DEFAULT_SEASONS)

@main_bp.route("/trip/<trip_id>", methods=["GET", "POST"])
def plan_trip(trip_id: str):
    trip = Trip.query.get_or_404(trip_id)
    
    # Logic to reconstruct allowed_locations
    if trip.location_details:
        allowed_locations = list(trip.location_details.values())
        location_details_map = trip.location_details
    else:
        # Fallback
        allowed_locations = [CITIES[code] for code in trip.locations if code in CITIES]
        location_details_map = {code: CITIES[code] for code in trip.locations if code in CITIES}

    allowed_durations = trip.durations
    allowed_season_names = trip.seasons
    allowed_seasons = [s for s in DEFAULT_SEASONS if s["name"] in allowed_season_names]
    
    # Months logic
    season_to_months = {
        "Winter": ["December"], "Spring": ["March", "April", "May"],
        "Summer": ["June", "July", "August"], "Fall": ["September", "October", "November"],
    }
    seen = set()
    allowed_months = []
    for s in allowed_season_names:
        for month in season_to_months.get(s, []):
            if month not in seen:
                allowed_months.append(month)
                seen.add(month)

    if request.method == "POST":
        selected_location = request.form.get("location")
        selected_duration = request.form.get("duration")
        selected_seasons = request.form.getlist("seasons")
        selected_dates_str = request.form.get("dates", "").strip()
        participant_name = request.form.get("participant_name", "").strip() or None

        errors = []
        if len(allowed_locations) > 1 and not selected_location: errors.append("Missing destination.")
        if len(allowed_durations) > 1 and not selected_duration: errors.append("Missing duration.")
        if not selected_dates_str: errors.append("Missing dates.")
        
        if errors:
            for e in errors: flash(e, "error")
            return redirect(url_for("main.plan_trip", trip_id=trip_id))

        selected_dates = [d.strip() for d in selected_dates_str.split(",") if d.strip()] if selected_dates_str else []

        new_resp = Response(
            trip_id=trip.id,
            participant_name=participant_name,
            location=selected_location if selected_location else allowed_locations[0]["code"],
            duration=selected_duration if selected_duration else allowed_durations[0],
            seasons=selected_seasons if selected_seasons else allowed_season_names,
            dates=selected_dates
        )
        db.session.add(new_resp)
        db.session.commit()
        flash("Preferences recorded!", "success")
        return redirect(url_for("main.plan_trip", trip_id=trip_id))

    # Aggregating stats for GET
    response_summary = {"locations": {}, "durations": {}, "seasons": {}, "months": {}, "dates": {}}
    for resp in trip.responses:
        loc = resp.location
        response_summary["locations"][loc] = response_summary["locations"].get(loc, 0) + 1
        dur = resp.duration
        response_summary["durations"][dur] = response_summary["durations"].get(dur, 0) + 1
        for s in resp.seasons:
             response_summary["seasons"][s] = response_summary["seasons"].get(s, 0) + 1
        
        # Derive months
        derived_months = []
        for d in resp.dates:
            try:
                month_num = int(d.split("-")[1])
                month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                m_name = month_names[month_num - 1]
                derived_months.append(m_name)
                response_summary["dates"][d] = response_summary["dates"].get(d, 0) + 1
            except: continue
        for m in derived_months:
             response_summary["months"][m] = response_summary["months"].get(m, 0) + 1

    sorted_locations = sorted(response_summary["locations"].items(), key=lambda x: x[1], reverse=True)
    sorted_durations = sorted(response_summary["durations"].items(), key=lambda x: x[1], reverse=True)
    sorted_seasons = sorted(response_summary["seasons"].items(), key=lambda x: x[1], reverse=True)
    sorted_months = sorted(response_summary["months"].items(), key=lambda x: x[1], reverse=True)
    sorted_dates = sorted(response_summary["dates"].items(), key=lambda x: x[1], reverse=True)
    
    totals = {k: sum(v.values()) for k, v in response_summary.items()}

    resp = make_response(render_template(
        "plan_trip.html", trip=trip, allowed_locations=allowed_locations,
        allowed_durations=allowed_durations, all_durations=DEFAULT_DURATIONS,
        allowed_seasons=allowed_seasons, allowed_months=allowed_months,
        share_url=request.url, sorted_locations=sorted_locations,
        sorted_durations=sorted_durations, sorted_seasons=sorted_seasons,
        sorted_months=sorted_months, sorted_dates=sorted_dates,
        sorted_dates_top=sorted_dates[:5], totals=totals,
        location_details=location_details_map
    ))
    
    # Cookie Logic: Add accessed trip to my_trips
    my_trips_cookie = request.cookies.get('my_trips')
    try:
        my_ids = json.loads(my_trips_cookie) if my_trips_cookie else []
    except:
        my_ids = []
        
    if trip_id not in my_ids:
        my_ids.append(trip_id)
        resp.set_cookie('my_trips', json.dumps(my_ids), max_age=60*60*24*365)

    return resp
