import json
import uuid
from datetime import datetime
from .extensions import db

class Trip(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = db.Column(db.String(100), nullable=False)
    creator_name = db.Column(db.String(100))
    # Storing lists as JSON strings for simplicity in SQLite 
    # (In a larger postgres app we might use ARRAY or separate tables)
    _durations = db.Column("durations", db.Text, default="[]")
    _seasons = db.Column("seasons", db.Text, default="[]")
    _locations = db.Column("locations", db.Text, default="[]") # List of codes
    
    # Custom location details stored as JSON
    # Structure: {"slug": {"code": slug, "name": name, "src": path, "alt": alt}}
    _location_details = db.Column("location_details", db.Text, default="{}")
    
    responses = db.relationship('Response', backref='trip', lazy=True)

    @property
    def durations(self):
        return json.loads(self._durations)

    @durations.setter
    def durations(self, value):
        self._durations = json.dumps(value)

    @property
    def seasons(self):
        return json.loads(self._seasons)

    @seasons.setter
    def seasons(self, value):
        self._seasons = json.dumps(value)
        
    @property
    def locations(self):
        return json.loads(self._locations)
        
    @locations.setter
    def locations(self, value):
        self._locations = json.dumps(value)

    @property
    def location_details(self):
        return json.loads(self._location_details)

    @location_details.setter
    def location_details(self, value):
        self._location_details = json.dumps(value)

    # Multi-day trip data (Itinerary)
    _multiday_data = db.Column("multiday_data", db.Text, default="[]")

    @property
    def multiday_data(self):
        return json.loads(self._multiday_data)

    @multiday_data.setter
    def multiday_data(self, value):
        self._multiday_data = json.dumps(value)

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.String(36), db.ForeignKey('trip.id'), nullable=False)
    participant_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    duration = db.Column(db.String(50))
    
    _seasons = db.Column("seasons", db.Text, default="[]")
    _dates = db.Column("dates", db.Text, default="[]")
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def seasons(self):
        return json.loads(self._seasons)

    @seasons.setter
    def seasons(self, value):
        self._seasons = json.dumps(value)

    @property
    def dates(self):
        return json.loads(self._dates)

    @dates.setter
    def dates(self, value):
        self._dates = json.dumps(value)
