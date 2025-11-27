from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
from web_telemetry_provider import WebTelemetryProvider

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)  # Enable CORS for all routes
telemetry_provider = WebTelemetryProvider()

@app.route('/api/years', methods=['GET'])
def get_years():
    years = telemetry_provider.get_years()
    return jsonify(years)

@app.route('/api/events/<int:year>', methods=['GET'])
def get_events(year):
    events = telemetry_provider.get_events_for_year(year)
    if events is not None:
        return jsonify(events)
    return jsonify({'error': 'Could not load events for the selected year'}), 404

@app.route('/api/race/<int:year>/<event_name>', methods=['GET'])
def get_race(year, event_name):
    from urllib.parse import unquote
    event_name = unquote(event_name)
    print(f"Getting race data for {year} '{event_name}'")
    race_data = telemetry_provider.get_race_data(year, event_name)
    if race_data is not None:
        return jsonify(race_data)
    return jsonify({'error': 'Could not load race data'}), 404

@app.route('/api/race/<int:year>/<event_name>/telemetry/<int:race_time>', methods=['GET'])
def get_telemetry(year, event_name, race_time):
    # URL decode the event name
    from urllib.parse import unquote
    event_name = unquote(event_name)
    print(f"Getting telemetry for {year} '{event_name}' at time {race_time}")
    telemetry_data = telemetry_provider.get_telemetry_data(year, event_name, race_time)
    if telemetry_data is not None:
        print(f"Returning {len(telemetry_data)} drivers")
        return jsonify(telemetry_data)
    print("No telemetry data found")
    return jsonify({'error': 'Could not load telemetry data'}), 404

@app.route('/')
def serve_main():
    return send_from_directory('.', 'f1_web_viewer.html')

@app.route('/f1_styles.css')
def serve_css():
    return send_from_directory('.', 'f1_styles.css', mimetype='text/css')

@app.route('/<path:path>')
def serve_static(path):
    print(f"Serving path: {path}")
    # Try to serve from static folder first
    if app.static_folder and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Try to serve from current directory
    elif os.path.exists(path):
        return send_from_directory('.', path)
    else:
        return send_from_directory('.', 'f1_web_viewer.html')

@app.route('/api/race/<int:year>/<event_name>/lap/<int:lap_number>', methods=['GET'])
def get_lap_start_time(year, event_name, lap_number):
    from urllib.parse import unquote
    event_name = unquote(event_name)
    lap_time_data = telemetry_provider.get_lap_start_time(year, event_name, lap_number)
    if lap_time_data:
        return jsonify(lap_time_data)
    return jsonify({'error': 'Could not load lap start time'}), 404

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
