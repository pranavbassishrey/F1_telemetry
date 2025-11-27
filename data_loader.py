import fastf1
import pandas as pd
from typing import List, Optional

def get_events_for_year(year: int) -> Optional[pd.DataFrame]:
    """
    Gets the F1 schedule for a given year.

    Args:
        year: The year to get the schedule for.

    Returns:
        A pandas DataFrame containing the schedule, or None if an error occurs.
    """
    try:
        schedule = fastf1.get_event_schedule(year)
        return schedule
    except Exception as e:
        print(f"Error getting event schedule for year {year}: {e}")
        return None

def load_race_data(year: int, event_name: str):
    """
    Loads race data for a specific event.

    Args:
        year: The year of the event.
        event_name: The name of the event (e.g., 'Italian Grand Prix').

    Returns:
        A fastf1 Session object, or None if an error occurs.
    """
    try:
        session = fastf1.get_session(year, event_name, 'R')
        session.load()
        return session
    except Exception as e:
        print(f"Error loading race data for {year} {event_name}: {e}")
        return None

if __name__ == '__main__':
    # Example usage:
    YEAR = 2023
    
    # Get and print the schedule for the year
    event_schedule = get_events_for_year(YEAR)
    if event_schedule is not None:
        print(f"F1 Schedule for {YEAR}:")
        print(event_schedule[['EventName', 'EventDate', 'Location']])
        
        # Let's try to load data for a specific event
        event_name = "Italian Grand Prix"
        print(f"\nLoading race data for: {YEAR} {event_name}")
        race_session = load_race_data(YEAR, event_name)
        
        if race_session:
            print("Race data loaded successfully.")
            print(f"Session: {race_session.event['EventName']}")
            print(f"Track: {race_session.event['Location']}")
            
            # Example: Print the fastest lap of the race
            fastest_lap = race_session.laps.pick_fastest()
            print("\nFastest Lap:")
            print(fastest_lap[['Driver', 'LapTime']])
    else:
        print(f"Could not retrieve schedule for {YEAR}.")
