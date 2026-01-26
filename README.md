# Ausflug - Group Trip Planner

Ausflug is a modern, collaborative web application designed to help groups plan their perfect trip. It allows users to vote on destinations, durations, and dates, and then collaboratively build a detailed itinerary.

## Key Features

-   **Collaborative Voting**: Share a link with friends to vote on:
    -   **Destination**: Visualize options with embedded maps/views.
    -   **Duration**: Choose preferred trip length.
    -   **Dates**: Select available dates with season-aware coloring (Spring/Summer/Fall/Winter).
-   **Multi-day Planner**:
    -   Interactive map-based itinerary builder.
    -   Add stops (cities) and connection details (Travel Mode, Duration).
    -   Real-time route weather forecasts.
    -   Drag-and-drop reordering.
    -   Mobile-responsive list view.

## Tech Stack

-   **Backend**: Python (Flask)
-   **Database**: SQLite (SQLAlchemy)
-   **Frontend**: HTML, TailwindCSS (via CDN), Alpine.js/Vanilla JS
-   **Libraries**:
    -   `Flatpickr` (Date selection)
    -   `Leaflet.js` (Maps)
    -   `SortableJS` (Drag-and-drop)
    -   `Open-Meteo API` (Weather data)

## Setup & Run

1.  **Environment**: Ensure you have Python 3.8+ installed.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run Application**:
    ```bash
    python run.py
    ```
    or
    ```bash
    flask run
    ```
4.  **Access**: Open `http://localhost:5000` in your browser.

## Project Structure

-   `app/`: Core application logic.
    -   `routes.py`: Main voting/survey logic.
    -   `multiday_routes.py`: Planner and API endpoints.
    -   `models.py`: Database schema.
    -   `templates/`: HTML templates.
    -   `static/`: CSS, JS, and Images.
