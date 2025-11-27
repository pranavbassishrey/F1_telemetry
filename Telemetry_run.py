import arcade
import arcade.gui
from arcade.gui import widgets
import data_loader
import fastf1.plotting
import pandas as pd
import math

# Enable FastF1 plotting
fastf1.plotting.setup_mpl(misc_mpl_mods=False)


SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "F1 Telemetry Viewer"

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converts a hex color string to an RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

class Button(arcade.gui.UIFlatButton):
    """A simple button implementation."""
    def __init__(self, text, width, height, on_click=None):
        super().__init__(text=text, width=width, height=height)
        self._on_click = on_click

    def on_click(self, event: arcade.gui.UIOnClickEvent):
        if self._on_click:
            self._on_click(self)

class RaceView(arcade.View):
    def __init__(self, window: arcade.Window, year: int, event_name: str):
        super().__init__(window)
        self.year = year
        self.event_name = event_name
        self.session = None
        self.driver_telemetry = {}
        
        self.race_time = pd.Timedelta(seconds=0)
        self.total_race_time = pd.Timedelta(seconds=1)
        self.playback_speed = 1.0
        self.is_playing = False

        self.x_min, self.x_max, self.y_min, self.y_max = 0, 0, 0, 0
        self.scaled_left_boundary_points = []
        self.scaled_right_boundary_points = []
        
        # --- UI Elements ---
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        # Back button - top left
        back_button = Button("Back", 120, 40, self.on_back_click)
        back_anchor = arcade.gui.UIAnchorLayout()
        back_anchor.add(back_button, anchor_x="left", anchor_y="top", align_x=20, align_y=-20)
        
        # Playback controls - bottom center
        self.play_pause_button = Button("Play", 80, 40, self.on_play_pause_click)
        slow_down_button = Button("<<", 80, 40, self.on_slow_down_click)
        speed_up_button = Button(">>", 80, 40, self.on_speed_up_click)
        replay_button = Button("Replay", 80, 40, self.on_replay_click)
        
        # Create horizontal layout for playback controls
        controls_layout = arcade.gui.UIBoxLayout(vertical=False, space_between=10)
        controls_layout.add(slow_down_button)
        controls_layout.add(self.play_pause_button)
        controls_layout.add(replay_button)
        controls_layout.add(speed_up_button)
        
        controls_anchor = arcade.gui.UIAnchorLayout()
        controls_anchor.add(controls_layout, anchor_x="center", anchor_y="bottom", align_y=20)
        
        self.manager.add(back_anchor)
        self.manager.add(controls_anchor)


    def setup(self):
        self.session = data_loader.load_race_data(self.year, self.event_name)
        if self.session:
            self.session.load()
            all_telemetry = []
            # Process all drivers
            drivers_to_process = self.session.drivers
            for driver_number in drivers_to_process:
                try:
                    laps = self.session.laps.pick_driver(driver_number)
                    telemetry = laps.get_telemetry().add_distance()
                    if not telemetry.empty:
                        # Sample every 5th point for smooth animation while maintaining performance
                        sampled_telemetry = telemetry.iloc[::5].copy()
                        self.driver_telemetry[driver_number] = sampled_telemetry
                        all_telemetry.append(sampled_telemetry)
                except Exception:
                    pass

            if all_telemetry:
                full_telemetry_df = pd.concat(all_telemetry)
                self.x_min, self.x_max = full_telemetry_df['X'].min(), full_telemetry_df['X'].max()
                self.y_min, self.y_max = full_telemetry_df['Y'].min(), full_telemetry_df['Y'].max()
                self.total_race_time = full_telemetry_df['Time'].max()
                
                # Generate and scale track boundaries
                self._create_track_boundaries()
                self._scale_track_boundaries()

    def on_play_pause_click(self, button):
        self.is_playing = not self.is_playing
        self.play_pause_button.text = "Pause" if self.is_playing else "Play"
    
    def on_speed_up_click(self, button):
        self.playback_speed *= 1.5

    def on_slow_down_click(self, button):
        self.playback_speed = max(0.25, self.playback_speed / 1.5)

    def on_replay_click(self, button):
        self.race_time = pd.Timedelta(seconds=0)

    def on_back_click(self, button):
        self.manager.disable()
        self.window.show_view(MenuView(self.window))

    def on_update(self, delta_time: float):
        if self.session and self.is_playing:
            self.race_time += pd.Timedelta(seconds=delta_time * self.playback_speed)

    def on_draw(self):
        self.clear()
        if not self.session:
            arcade.draw_text("Loading...", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.WHITE, 30, anchor_x="center")
            return

        self.manager.draw()
            
        arcade.draw_text(f"Race: {self.year} {self.event_name}", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 30, arcade.color.WHITE, 20, anchor_x="center")
        arcade.draw_text(f"Time: {str(self.race_time).split('.')[0]}", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 60, arcade.color.WHITE, 20, anchor_x="center")
        arcade.draw_text(f"Speed: {self.playback_speed:.1f}x", SCREEN_WIDTH - 100, SCREEN_HEIGHT - 80, arcade.color.WHITE, 16)
        
        # Draw track boundaries
        self._draw_track_boundaries()
        
        for driver_number, telemetry in self.driver_telemetry.items():
            if 'Time' not in telemetry.columns: continue
            
            time_diff = (telemetry['Time'] - self.race_time).abs()
            closest_sample = telemetry.loc[time_diff.idxmin()]
            x, y = closest_sample['X'], closest_sample['Y']
            
            scale = min((SCREEN_WIDTH-200)/(self.x_max-self.x_min), (SCREEN_HEIGHT-200)/(self.y_max-self.y_min)) if self.x_max > self.x_min and self.y_max > self.y_min else 1
            offset_x = (SCREEN_WIDTH - (self.x_max - self.x_min) * scale) / 2
            offset_y = (SCREEN_HEIGHT - (self.y_max - self.y_min) * scale) / 2
            screen_x, screen_y = (x - self.x_min) * scale + offset_x, (y - self.y_min) * scale + offset_y

            driver = self.session.get_driver(driver_number)
            team_color_hex = fastf1.plotting.get_team_color(driver['TeamName'], session=self.session) or "#FFFFFF"
            arcade.draw_circle_filled(screen_x, screen_y, 7, hex_to_rgb(team_color_hex))
            arcade.draw_text(driver['Abbreviation'], screen_x + 10, screen_y, arcade.color.WHITE, 10)

        self._draw_positions()

    def _create_track_boundaries(self):
        """Create two boundary lines for the track."""
        try:
            # Get the fastest lap
            fastest_lap = self.session.laps.pick_fastest()
            if fastest_lap is not None:
                telemetry = fastest_lap.get_telemetry().add_distance()
                if not telemetry.empty:
                    self.track_left_boundary = []
                    self.track_right_boundary = []
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
                        left_point = (p1[0] + perp_dx * track_width, p1[1] + perp_dy * track_width)
                        right_point = (p1[0] - perp_dx * track_width, p1[1] - perp_dy * track_width)

                        self.track_left_boundary.append(left_point)
                        self.track_right_boundary.append(right_point)

        except Exception as e:
            print(f"Error creating track boundaries: {e}")
            self.track_left_boundary = []
            self.track_right_boundary = []

    def _scale_track_boundaries(self):
        """Scale the track boundaries to fit the screen."""
        if not self.track_left_boundary or not self.track_right_boundary:
            return
        
        if self.x_max > self.x_min and self.y_max > self.y_min:
            scale = min((SCREEN_WIDTH-200)/(self.x_max-self.x_min), (SCREEN_HEIGHT-200)/(self.y_max-self.y_min))
            offset_x = (SCREEN_WIDTH - (self.x_max - self.x_min) * scale) / 2
            offset_y = (SCREEN_HEIGHT - (self.y_max - self.y_min) * scale) / 2
        else:
            return
            
        self.scaled_left_boundary_points = [((x - self.x_min) * scale + offset_x, (y - self.y_min) * scale + offset_y) for x, y in self.track_left_boundary]
        self.scaled_right_boundary_points = [((x - self.x_min) * scale + offset_x, (y - self.y_min) * scale + offset_y) for x, y in self.track_right_boundary]

    def _draw_track_boundaries(self):
        """Draw the track boundaries."""
        if self.scaled_left_boundary_points and self.scaled_right_boundary_points:
            arcade.draw_line_strip(self.scaled_left_boundary_points, arcade.color.WHITE, 2)
            arcade.draw_line_strip(self.scaled_right_boundary_points, arcade.color.WHITE, 2)

    def _draw_positions(self):
        """Draw the driver positions on the right side of the screen."""
        # Create a list of drivers with their current distance
        driver_positions = []
        for driver_number, telemetry in self.driver_telemetry.items():
            if 'Time' not in telemetry.columns: continue
            
            time_diff = (telemetry['Time'] - self.race_time).abs()
            closest_sample = telemetry.loc[time_diff.idxmin()]
            distance = closest_sample['Distance']
            
            laps = self.session.laps.pick_driver(driver_number)
            current_laps = laps[laps['Time'] < self.race_time]
            if not current_laps.empty:
                lap_number = current_laps.iloc[-1]['LapNumber']
            else:
                lap_number = 1
            
            driver_positions.append({'driver_number': driver_number, 'distance': distance, 'lap_number': lap_number})

        # Sort drivers by distance
        driver_positions.sort(key=lambda x: x['distance'], reverse=True)

        # Draw background
        arcade.draw_lbwh_rectangle_filled(SCREEN_WIDTH - 200, 0, 200, SCREEN_HEIGHT, (0, 0, 0, 150))

        # Draw positions
        y_pos = SCREEN_HEIGHT - 30
        for i, pos_data in enumerate(driver_positions):
            driver = self.session.get_driver(pos_data['driver_number'])
            team_color_hex = fastf1.plotting.get_team_color(driver['TeamName'], session=self.session) or "#FFFFFF"
            
            arcade.draw_text(f"{i+1}", SCREEN_WIDTH - 180, y_pos, arcade.color.WHITE, 14)
            arcade.draw_lbwh_rectangle_filled(SCREEN_WIDTH - 160, y_pos + 7, 10, 10, hex_to_rgb(team_color_hex))
            arcade.draw_text(f"{driver['Abbreviation']} - Lap {int(pos_data['lap_number'])}", SCREEN_WIDTH - 140, y_pos, arcade.color.WHITE, 14)
            
            y_pos -= 30

    def on_mouse_press(self, x, y, button, modifiers):
        self.manager.on_mouse_press(x, y, button, modifiers)

    def on_mouse_press(self, x, y, button, modifiers):
        self.manager.on_mouse_press(x, y, button, modifiers)

class MenuView(arcade.View):
    def __init__(self, window: arcade.Window):
        super().__init__(window)
        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        
        self.selected_year = None
        self.event_buttons = []
        self.event_anchor = None
        
        # Create year buttons in vertical layout
        year_layout = arcade.gui.UIBoxLayout(vertical=True, space_between=10)
        for year in range(2025, 2020, -1):
            btn = Button(str(year), 120, 40, self.on_year_click)
            year_layout.add(btn)
            
        year_anchor = arcade.gui.UIAnchorLayout()
        year_anchor.add(year_layout, anchor_x="left", anchor_y="center", align_x=100)
        self.manager.add(year_anchor)

    def on_year_click(self, button):
        self.selected_year = int(button.text)
        
        # Remove existing event anchor
        if self.event_anchor:
            self.manager.remove(self.event_anchor)
        self.event_buttons.clear()

        schedule = data_loader.get_events_for_year(self.selected_year)
        if schedule is not None:
            races = schedule[schedule['EventFormat'] == 'conventional']['EventName'].tolist()
            num_races = len(races)
            if num_races == 0: return

            # Create event buttons in columns
            num_rows = 12  # Maximum rows per column
            col1_layout = arcade.gui.UIBoxLayout(vertical=True, space_between=5)
            col2_layout = arcade.gui.UIBoxLayout(vertical=True, space_between=5)
            
            for i, event_name in enumerate(races):
                btn = Button(event_name, 280, 35, self.on_event_click)
                self.event_buttons.append(btn)
                
                if i < num_rows:
                    col1_layout.add(btn)
                else:
                    col2_layout.add(btn)
            
            # Create horizontal layout for the two columns
            grid_layout = arcade.gui.UIBoxLayout(vertical=False, space_between=20)
            grid_layout.add(col1_layout)
            if len(races) > num_rows:
                grid_layout.add(col2_layout)
            
            self.event_anchor = arcade.gui.UIAnchorLayout()
            self.event_anchor.add(grid_layout, anchor_x="right", anchor_y="center", align_x=-50)
            self.manager.add(self.event_anchor)
    
    def on_event_click(self, button):
        self.manager.disable()
        race_view = RaceView(self.window, self.selected_year, button.text)
        race_view.setup()
        self.window.show_view(race_view)

    def on_draw(self):
        self.clear()
        self.manager.draw()
        arcade.draw_text("Select a Year", 100, SCREEN_HEIGHT - 50, arcade.color.WHITE, 20, anchor_x="center")
        if self.selected_year:
            arcade.draw_text(f"Select Race for {self.selected_year}", SCREEN_WIDTH - 200, SCREEN_HEIGHT - 50, arcade.color.WHITE, 20, anchor_x="center")
            
    def on_mouse_press(self, x, y, button, modifiers):
        self.manager.on_mouse_press(x, y, button, modifiers)

def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    menu_view = MenuView(window)
    window.show_view(menu_view)
    arcade.run()

if __name__ == "__main__":
    main()