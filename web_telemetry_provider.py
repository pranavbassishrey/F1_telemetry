import fastf1
import pandas as pd
import math

class WebTelemetryProvider:
    def __init__(self):
        self.sessions = {}

    def get_years(self):
        return list(range(2025, 2020, -1))

    def get_events_for_year(self, year):
        try:
            schedule = fastf1.get_event_schedule(year)
            races = schedule[schedule['EventFormat'] == 'conventional']['EventName'].tolist()
            return races
        except Exception as e:
            print(f"Error getting event schedule for year {year}: {e}")
            return None

    def get_race_data(self, year, event_name):
        session_key = f"{year}_{event_name}"
        if session_key not in self.sessions:
            try:
                session = fastf1.get_session(year, event_name, 'R')
                session.load(telemetry=True)
                # Cache telemetry for all drivers
                driver_telemetry = {}
                for driver_number in session.drivers:
                    try:
                        laps = session.laps.pick_driver(driver_number)
                        telemetry = laps.get_telemetry().add_distance()
                        if not telemetry.empty:
                            # Sample every 5th point
                            driver_telemetry[driver_number] = telemetry.iloc[::5].copy()
                    except Exception:
                        pass
                session.driver_telemetry = driver_telemetry
                self.sessions[session_key] = session
            except Exception as e:
                print(f"Error loading race data for {year} {event_name}: {e}")
                return None

        try:
            session = self.sessions[session_key]
            fastest_lap = session.laps.pick_fastest()
            if fastest_lap is None:
                return None
            
            telemetry = fastest_lap.get_telemetry().add_distance()
            if telemetry.empty:
                return None

            x_min, x_max = float(telemetry['X'].min()), float(telemetry['X'].max())
            y_min, y_max = float(telemetry['Y'].min()), float(telemetry['Y'].max())

            # Create track boundaries from telemetry data
            track_left_boundary = []
            track_right_boundary = []
            track_width = 250  # Adjust this value to change the track width

            points = list(zip(telemetry['X'], telemetry['Y']))
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]

                # Calculate direction vector
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]

                # Normalize direction vector
                length = math.sqrt(dx**2 + dy**2)
                if length > 0:
                    dx /= length
                    dy /= length

                # Calculate perpendicular vector
                perp_dx = -dy
                perp_dy = dx

                # Calculate boundary points
                left_point = [p1[0] + perp_dx * track_width, p1[1] + perp_dy * track_width]
                right_point = [p1[0] - perp_dx * track_width, p1[1] - perp_dy * track_width]

                track_left_boundary.append(left_point)
                track_right_boundary.append(right_point)

            # Get total race time from the winner's result
            total_time = 0
            try:
                winner_time = session.results[session.results['Position'] == 1]['Time'].iloc[0]
                if pd.notna(winner_time):
                    total_time = winner_time.total_seconds()
            except (KeyError, IndexError):
                # Fallback if results are not available
                if not session.laps.empty and 'Time' in session.laps.columns:
                    last_time = session.laps['Time'].max()
                    if pd.notna(last_time):
                        total_time = last_time.total_seconds()

            return {
                'x_min': x_min,
                'x_max': x_max,
                'y_min': y_min,
                'y_max': y_max,
                'track_left_boundary': track_left_boundary,
                'track_right_boundary': track_right_boundary,
                'total_race_time': total_time
            }
        except Exception as e:
            print(f"Error processing race data for {year} {event_name}: {e}")
            return None

    def get_telemetry_data(self, year, event_name, race_time):
        session_key = f"{year}_{event_name}"
        
        # Ensure race data is loaded first
        if session_key not in self.sessions:
            print(f"Loading session for telemetry: {session_key}")
            race_data = self.get_race_data(year, event_name)
            if not race_data:
                return []

        try:
            session = self.sessions[session_key]
            race_time_td = pd.to_timedelta(race_time, unit='s')
            driver_positions = []
            
            for driver_number, telemetry in session.driver_telemetry.items():
                if 'Time' not in telemetry.columns or telemetry.empty:
                    continue

                time_diff = (telemetry['Time'] - race_time_td).abs()
                closest_sample = telemetry.loc[time_diff.idxmin()]
                
                laps = session.laps.pick_driver(driver_number)
                current_laps = laps[laps['Time'] < race_time_td]
                lap_number = current_laps.iloc[-1]['LapNumber'] if not current_laps.empty else 1

                driver = session.get_driver(driver_number)
                
                driver_positions.append({
                    'driver_number': driver_number,
                    'abbreviation': driver['Abbreviation'],
                    'x': float(closest_sample['X']),
                    'y': float(closest_sample['Y']),
                    'lap': int(lap_number),
                    'distance': float(closest_sample['Distance'])
                })

            # Sort by driver number to ensure consistent order
            driver_positions.sort(key=lambda d: d['driver_number'])
            return driver_positions
        except Exception as e:
            print(f"Error getting telemetry data: {e}")
            return []

    def get_lap_start_time(self, year, event_name, lap_number):
        session_key = f"{year}_{event_name}"
        if session_key not in self.sessions:
            return None

        try:
            session = self.sessions[session_key]
            
            if lap_number <= 1:
                return {'lap_start_time': 0.0}

            # Find the leader at the end of the previous lap
            prev_lap = lap_number - 1
            prev_lap_data = session.laps[session.laps['LapNumber'] == prev_lap]
            
            if prev_lap_data.empty:
                return None # Previous lap doesn't exist

            # The leader is the one who finished the previous lap first (lowest 'Time')
            leader_at_prev_lap = prev_lap_data.sort_values(by='Time').iloc[0]
            leader_driver_number = leader_at_prev_lap['DriverNumber']

            # Get the specific lap for the leader
            leader_lap = session.laps[
                (session.laps['DriverNumber'] == leader_driver_number) & 
                (session.laps['LapNumber'] == lap_number)
            ]

            if leader_lap.empty:
                return None # Leader has not started this lap yet

            # The 'Time' for a lap is its completion time. To get the start time,
            # we need the completion time of the previous lap.
            lap_start_time = leader_at_prev_lap['Time'].total_seconds()
            
            return {'lap_start_time': lap_start_time}

        except (KeyError, IndexError):
            return None # Lap or driver data does not exist
        except Exception as e:
            print(f"Error getting lap start time for {year} {event_name}, Lap {lap_number}: {e}")
            return None

if __name__ == '__main__':
    provider = WebTelemetryProvider()
    print("Testing WebTelemetryProvider...")
    print("Years:", provider.get_years())
    events = provider.get_events_for_year(2023)
    if events:
        print(f"Events for 2023: {events[:3]}...")  # Show first 3 events
    else:
        print("No events found for 2023")
