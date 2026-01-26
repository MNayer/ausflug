from flask import Blueprint, render_template, request, jsonify, url_for
from .models import Trip
from .extensions import db
import time

multiday_bp = Blueprint('multiday', __name__)

@multiday_bp.route("/trip/<trip_id>/multiday")
def planner(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    return render_template("multiday.html", trip=trip)

@multiday_bp.route("/trip/<trip_id>/multiday/api/save", methods=["POST"])
def save_itinerary(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    data = request.json
    trip.multiday_data = data
    db.session.commit()
    return jsonify({"status": "success"})

@multiday_bp.route("/trip/<trip_id>/multiday/api/load", methods=["GET"])
def load_itinerary(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    return jsonify(trip.multiday_data)
