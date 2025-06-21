import tkinter as tk
from tkinter import Canvas, messagebox, Frame, Label, Button, OptionMenu, Entry
import threading
import time
import random
import math
import sqlite3
import pygame

# Database Functions
def get_db_connection():
    conn = sqlite3.connect('nasa_explorer.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            user_id INTEGER,
            explore_progress INTEGER DEFAULT 0,
            solar_progress INTEGER DEFAULT 0,
            quiz_progress INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# Login Window Class
class LoginWindow:
    def __init__(self, login_root, main_root):
        self.login_root = login_root
        self.main_root = main_root
        self.login_root.title("Login to NASA Spaceship Explorer")
        self.login_root.geometry("300x200")
        self.login_root.config(bg="#000033")
        
        Label(self.login_root, text="Username", font=("Arial", 12), fg="white", bg="#000033").pack(pady=10)
        self.username_entry = Entry(self.login_root, font=("Arial", 12))
        self.username_entry.pack()
        
        Label(self.login_root, text="Password", font=("Arial", 12), fg="white", bg="#000033").pack(pady=10)
        self.password_entry = Entry(self.login_root, show="*", font=("Arial", 12))
        self.password_entry.pack()
        
        Button(self.login_root, text="Login", font=("Arial", 12), bg="#FF6600", fg="white", command=self.login).pack(pady=10)
        Button(self.login_root, text="Create Account", font=("Arial", 12), bg="#3399FF", fg="white", command=self.create_account).pack()
        
        self.login_root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            self.login_root.destroy()
            self.main_root.deiconify()
            app = NASASpaceshipExplorer(self.main_root, user['id'])
        else:
            messagebox.showerror("Error", "Invalid credentials")
    
    def create_account(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            user_id = cursor.lastrowid
            cursor.execute("INSERT INTO progress (user_id) VALUES (?)", (user_id,))
            conn.commit()
            messagebox.showinfo("Success", "Account created. Please login.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists")
        finally:
            conn.close()
    
    def on_close(self):
        self.main_root.destroy()

# Main Application Class
class NASASpaceshipExplorer:
    def __init__(self, root, user_id):
        self.root = root
        self.user_id = user_id
        self.root.title("🚀 NASA Spaceship Explorer for Kids")
        self.root.geometry("1000x700")
        self.root.config(bg="#000033")
        self.fullscreen = False
        self.responsive = True
        pygame.mixer.init()
        self.load_sounds()
        self.count_thread = None
        
        self.spacecraft = [
            {"name": "Space Shuttle", "id": "shuttle", "era": "1981-2011", 
             "fact": "Reusable spacecraft that carried astronauts to space 135 times"},
            {"name": "Artemis SLS", "id": "artemis", "era": "2022-Present", 
             "fact": "NASA's new rocket for returning astronauts to the Moon"},
            {"name": "Saturn V", "id": "saturn", "era": "1967-1973", 
             "fact": "Tallest rocket ever flown (363 ft), took astronauts to the Moon"},
            {"name": "Falcon Heavy", "id": "falcon", "era": "2018-Present", 
             "fact": "World's most powerful operational rocket with reusable boosters"},
            {"name": "Voyager Probe", "id": "voyager", "era": "1977-Present", 
             "fact": "Farthest human-made object from Earth, now in interstellar space"}
        ]
        self.current_ship = 0
        self.mode = "explore"
        self.quiz_score = 0
        self.quiz_question = 0
        self.mission = "Earth Orbit"
        self.missions = ["Earth Orbit", "Moon Mission", "Mars Expedition", "Jupiter Flyby", "Deep Space"]
        self.progress = {"explore": 0, "solar": 0, "quiz": 0}
        self.load_progress()
        
        self.planets = [
            {"name": "Mercury", "color": "gray", "size": 15, "distance": 50},
            {"name": "Venus", "color": "orange", "size": 20, "distance": 80},
            {"name": "Earth", "color": "blue", "size": 22, "distance": 120},
            {"name": "Mars", "color": "red", "size": 19, "distance": 170},
            {"name": "Jupiter", "color": "sandybrown", "size": 35, "distance": 240},
            {"name": "Saturn", "color": "gold", "size": 30, "distance": 300},
            {"name": "Uranus", "color": "lightblue", "size": 25, "distance": 350},
            {"name": "Neptune", "color": "royalblue", "size": 24, "distance": 400}
        ]
        
        self.setup_ui()
        self.draw_spaceship()
        self.root.bind("<Configure>", self.on_window_resize)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_sounds(self):
        self.beep_sound = None
        self.launch_sound = None
        self.space_sound = None
        self.planet_sound = None
        self.quiz_sound = None

    def load_progress(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM progress WHERE user_id = ?", (self.user_id,))
        progress = cursor.fetchone()
        conn.close()
        if progress:
            self.progress["explore"] = progress["explore_progress"]
            self.progress["solar"] = progress["solar_progress"]
            self.progress["quiz"] = progress["quiz_progress"]

    def save_progress(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE progress SET explore_progress = ?, solar_progress = ?, quiz_progress = ?
            WHERE user_id = ?
        """, (self.progress["explore"], self.progress["solar"], self.progress["quiz"], self.user_id))
        conn.commit()
        conn.close()

    def on_close(self):
        self.save_progress()
        self.root.destroy()

    def setup_ui(self):
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_rowconfigure(3, weight=0)
        self.root.grid_columnconfigure(0, weight=1)
        
        header = Frame(self.root, bg="#000033")
        header.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)
        
        self.title = Label(header, text="NASA Spaceship Explorer", 
                         font=("Arial", 28, "bold"), fg="#FF9900", bg="#000033")
        self.title.grid(row=0, column=0, sticky="w")
        
        self.ship_name = Label(header, text=self.spacecraft[self.current_ship]["name"], 
                              font=("Arial", 18), fg="white", bg="#000033")
        self.ship_name.grid(row=0, column=1, padx=20)
        
        mission_frame = Frame(header, bg="#000033")
        mission_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")
        
        tk.Label(mission_frame, text="Select Mission:", 
                font=("Arial", 12), fg="white", bg="#000033").pack(side=tk.LEFT, padx=5)
        
        self.mission_var = tk.StringVar(value=self.mission)
        mission_menu = tk.OptionMenu(mission_frame, self.mission_var, *self.missions)
        mission_menu.config(font=("Arial", 12), bg="#9933FF", fg="white")
        mission_menu.pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = tk.Canvas(mission_frame, width=200, height=15, bg="#000033", highlightthickness=0)
        self.progress_bar.pack(side=tk.RIGHT, padx=10)
        self.update_progress_bar()
        
        self.canvas = Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.create_stars()
        
        status_frame = Frame(self.root, bg="#000033")
        status_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_columnconfigure(1, weight=0)
        
        self.status_label = Label(status_frame, text="Status: Ready for launch", 
                                font=("Consolas", 14), fg="#00FFFF", bg="#000033", anchor="w")
        self.status_label.grid(row=0, column=0, sticky="w")
        
        self.science_label = Label(status_frame, text="Thrust: 0% | Gravity: 9.8 m/s²", 
                                 font=("Consolas", 12), fg="#FFCC00", bg="#000033")
        self.science_label.grid(row=0, column=1, sticky="e")
        
        btn_frame = Frame(self.root, bg="#000033")
        btn_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        
        for i in range(8):
            btn_frame.grid_columnconfigure(i, weight=1)
        
        Button(btn_frame, text="Start Countdown", font=("Arial", 12), bg="#FF6600", fg="white",
              command=self.start_countdown).grid(row=0, column=0, padx=5, sticky="ew")
        Button(btn_frame, text="Spacecraft Info", font=("Arial", 12), bg="#3399FF", fg="white",
              command=self.show_facts).grid(row=0, column=1, padx=5, sticky="ew")
        Button(btn_frame, text="Next Spacecraft", font=("Arial", 12), bg="#66CC66", fg="white",
              command=self.next_ship).grid(row=0, column=2, padx=5, sticky="ew")
        Button(btn_frame, text="Solar System", font=("Arial", 12), bg="#9933FF", fg="white",
              command=self.show_solar_system).grid(row=0, column=3, padx=5, sticky="ew")
        Button(btn_frame, text="Rocket Quiz", font=("Arial", 12), bg="#FF33CC", fg="white",
              command=self.start_quiz).grid(row=0, column=4, padx=5, sticky="ew")
        Button(btn_frame, text="Astronaut Training", font=("Arial", 12), bg="#FF9900", fg="white",
               command=self.show_training).grid(row=0, column=5, padx=5, sticky="ew")
        Button(btn_frame, text="Mission Timeline", font=("Arial", 12), bg="#3399FF", fg="white",
               command=self.show_timeline).grid(row=0, column=6, padx=5, sticky="ew")
        Button(btn_frame, text="Fun Facts", font=("Arial", 12), bg="#66CC66", fg="white",
               command=self.show_fun_fact).grid(row=0, column=7, padx=5, sticky="ew")
        
        self.create_educational_panels()

    def update_progress_bar(self):
        self.progress_bar.delete("progress")
        total = len(self.spacecraft) + len(self.planets) + 5
        completed = self.progress["explore"] + self.progress["solar"] + self.progress["quiz"]
        width = 200 * completed / total
        
        self.progress_bar.create_rectangle(0, 0, width, 15, fill="#00CC00", tags="progress")
        self.progress_bar.create_text(100, 8, text=f"{completed}/{total}", 
                                    fill="white", font=("Arial", 10))

    def on_window_resize(self, event):
        if not self.responsive:
            return
        if self.mode == "explore":
            self.draw_spaceship()
        elif self.mode == "solar":
            self.show_solar_system()
        elif self.mode == "timeline":
            self.show_timeline()

    def create_stars(self):
        self.canvas.delete("stars")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        for _ in range(200):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.uniform(0.1, 1.5)
            color = random.choice(["white", "#FFFFCC", "#CCFFFF"])
            self.canvas.create_oval(x, y, x+size, y+size, fill=color, outline="", tags="stars")

    def create_educational_panels(self):
        self.science_frame = Frame(self.root, bg="#001133", bd=2, relief=tk.RIDGE)
        self.science_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=5)
        
        concepts = [
            ("Thrust", "Force that propels the rocket upward", "Newton's 3rd Law"),
            ("Gravity", "Force pulling rocket toward Earth", "9.8 m/s² acceleration"),
            ("Orbit", "Balancing speed and gravity", "~28,000 km/h for Earth orbit"),
            ("Stages", "Discarding empty fuel tanks", "Reduces weight for efficiency")
        ]
        
        for i, (title, desc, detail) in enumerate(concepts):
            self.science_frame.grid_columnconfigure(i, weight=1)
            frame = Frame(self.science_frame, bg="#001133")
            frame.grid(row=0, column=i, padx=10, pady=5, sticky="nsew")
            
            Label(frame, text=title, font=("Arial", 12, "bold"), 
                 fg="#FF9900", bg="#001133").pack()
            Label(frame, text=desc, font=("Arial", 9), 
                 fg="white", bg="#001133").pack()
            Label(frame, text=detail, font=("Arial", 9, "italic"), 
                 fg="#66CCFF", bg="#001133").pack()

    def next_ship(self):
        self.current_ship = (self.current_ship + 1) % len(self.spacecraft)
        self.ship_name.config(text=self.spacecraft[self.current_ship]["name"])
        self.draw_spaceship()
        self.status_label.config(text=f"Loaded {self.spacecraft[self.current_ship]['name']}")
        self.progress["explore"] = min(len(self.spacecraft), self.progress["explore"] + 1)
        self.update_progress_bar()
        self.save_progress()

    def draw_spaceship(self):
        self.canvas.delete("spaceship")
        ship_id = self.spacecraft[self.current_ship]["id"]
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        center_x = width // 2
        base_y = height - 50
        
        if ship_id == "shuttle":
            self.draw_shuttle(center_x, base_y)
        elif ship_id == "artemis":
            self.draw_artemis(center_x, base_y)
        elif ship_id == "saturn":
            self.draw_saturn_v(center_x, base_y)
        elif ship_id == "falcon":
            self.draw_falcon_heavy(center_x, base_y)
        elif ship_id == "voyager":
            self.draw_voyager(center_x, base_y)

    def draw_shuttle(self, center_x, base_y):
        body = self.canvas.create_polygon(
            center_x-50, base_y, center_x+50, base_y, center_x+70, base_y-170, center_x-70, base_y-170, 
            fill="#D0D0D0", outline="white", width=2, tags="spaceship"
        )
        nose = self.canvas.create_polygon(
            center_x-70, base_y-170, center_x+70, base_y-170, center_x, base_y-220, 
            fill="white", outline="gray", width=2, tags="spaceship"
        )
        wing1 = self.canvas.create_polygon(
            center_x-70, base_y, center_x-110, base_y+40, center_x-70, base_y+40, 
            fill="#A0A0A0", outline="white", width=1, tags="spaceship"
        )
        wing2 = self.canvas.create_polygon(
            center_x+50, base_y, center_x+90, base_y+40, center_x+50, base_y+40, 
            fill="#A0A0A0", outline="white", width=1, tags="spaceship"
        )
        tail = self.canvas.create_polygon(
            center_x-30, base_y-220, center_x+30, base_y-220, center_x+40, base_y-250, center_x-40, base_y-250, 
            fill="gray", outline="white", width=1, tags="spaceship"
        )
        engine1 = self.canvas.create_oval(center_x-30, base_y, center_x-10, base_y+20, fill="#FF8800", outline="red", tags="spaceship")
        engine2 = self.canvas.create_oval(center_x+10, base_y, center_x+30, base_y+20, fill="#FF8800", outline="red", tags="spaceship")
        
        self.canvas.tag_bind(body, "<Enter>", lambda e: self.show_tooltip("Orbiter", "Carries crew and cargo"))
        self.canvas.tag_bind(nose, "<Enter>", lambda e: self.show_tooltip("Cockpit", "Where astronauts control the shuttle"))
        self.canvas.tag_bind(wing1, "<Enter>", lambda e: self.show_tooltip("Wing", "Provides lift during landing"))
        self.canvas.tag_bind(tail, "<Enter>", lambda e: self.show_tooltip("Vertical Stabilizer", "Keeps shuttle stable during flight"))
        self.canvas.tag_bind(engine1, "<Enter>", lambda e: self.show_tooltip("Main Engine", "Burns liquid hydrogen and oxygen"))
        self.canvas.tag_bind(engine2, "<Enter>", lambda e: self.show_tooltip("Main Engine", "Each produces 400,000 lbs of thrust"))

    def draw_artemis(self, center_x, base_y):
        core = self.canvas.create_rectangle(center_x-10, base_y-200, center_x+10, base_y, fill="white", outline="orange", width=3, tags="spaceship")
        booster1 = self.canvas.create_rectangle(center_x-40, base_y-190, center_x-20, base_y-10, fill="silver", outline="gray", width=2, tags="spaceship")
        booster2 = self.canvas.create_rectangle(center_x+20, base_y-190, center_x+40, base_y-10, fill="silver", outline="gray", width=2, tags="spaceship")
        capsule = self.canvas.create_polygon(
            center_x-40, base_y-200, center_x+40, base_y-200, center_x, base_y-240, 
            fill="#99CCFF", outline="gray", width=2, tags="spaceship"
        )
        engine = self.canvas.create_oval(center_x-10, base_y, center_x+10, base_y+20, fill="#FF5500", tags="spaceship")
        
        self.canvas.tag_bind(core, "<Enter>", lambda e: self.show_tooltip("Core Stage", "Holds liquid hydrogen and oxygen fuel"))
        self.canvas.tag_bind(booster1, "<Enter>", lambda e: self.show_tooltip("Solid Rocket Booster", "Provides extra thrust at liftoff"))
        self.canvas.tag_bind(capsule, "<Enter>", lambda e: self.show_tooltip("Orion Capsule", "Carries astronauts to the Moon"))
        self.canvas.tag_bind(engine, "<Enter>", lambda e: self.show_tooltip("RS-25 Engine", "Reused from Space Shuttle program"))

    def draw_saturn_v(self, center_x, base_y):
        stage1 = self.canvas.create_rectangle(center_x-20, base_y, center_x+20, base_y-100, fill="white", outline="black", width=2, tags="spaceship")
        stage2 = self.canvas.create_rectangle(center_x-15, base_y-100, center_x+15, base_y-160, fill="white", outline="black", width=2, tags="spaceship")
        stage3 = self.canvas.create_rectangle(center_x-10, base_y-160, center_x+10, base_y-200, fill="white", outline="black", width=2, tags="spaceship")
        module = self.canvas.create_polygon(
            center_x-10, base_y-200, center_x+10, base_y-200, center_x, base_y-230, 
            fill="silver", outline="gray", width=1, tags="spaceship"
        )
        engine1 = self.canvas.create_oval(center_x-15, base_y, center_x-5, base_y+10, fill="orange", tags="spaceship")
        engine2 = self.canvas.create_oval(center_x+5, base_y, center_x+15, base_y+10, fill="orange", tags="spaceship")
        
        self.canvas.tag_bind(stage1, "<Enter>", lambda e: self.show_tooltip("First Stage", "5 F-1 engines burning kerosene"))
        self.canvas.tag_bind(stage2, "<Enter>", lambda e: self.show_tooltip("Second Stage", "5 J-2 engines burning liquid hydrogen"))
        self.canvas.tag_bind(stage3, "<Enter>", lambda e: self.show_tooltip("Third Stage", "Single J-2 engine for trans-lunar injection"))
        self.canvas.tag_bind(module, "<Enter>", lambda e: self.show_tooltip("Command Module", "Housed astronauts during lunar missions"))

    def draw_falcon_heavy(self, center_x, base_y):
        core = self.canvas.create_rectangle(center_x-10, base_y, center_x+10, base_y-170, fill="white", outline="black", width=2, tags="spaceship")
        booster1 = self.canvas.create_rectangle(center_x-50, base_y, center_x-30, base_y-140, fill="white", outline="black", width=2, tags="spaceship")
        booster2 = self.canvas.create_rectangle(center_x+30, base_y, center_x+50, base_y-140, fill="white", outline="black", width=2, tags="spaceship")
        fairing = self.canvas.create_polygon(
            center_x-10, base_y-170, center_x+10, base_y-170, center_x, base_y-220, 
            fill="lightgray", outline="black", width=1, tags="spaceship"
        )
        fin1 = self.canvas.create_polygon(center_x-50, base_y-140, center_x-60, base_y-130, center_x-50, base_y-130, fill="gray", tags="spaceship")
        fin2 = self.canvas.create_polygon(center_x+50, base_y-140, center_x+60, base_y-130, center_x+50, base_y-130, fill="gray", tags="spaceship")
        
        self.canvas.tag_bind(core, "<Enter>", lambda e: self.show_tooltip("Core Stage", "Powered by Merlin engines, lands vertically"))
        self.canvas.tag_bind(booster1, "<Enter>", lambda e: self.show_tooltip("Booster", "Reusable side booster, returns to launch site"))
        self.canvas.tag_bind(fairing, "<Enter>", lambda e: self.show_tooltip("Payload Fairing", "Protects satellites during launch"))
        self.canvas.tag_bind(fin1, "<Enter>", lambda e: self.show_tooltip("Grid Fin", "Steers booster during descent"))

    def draw_voyager(self, center_x, base_y):
        bus = self.canvas.create_rectangle(center_x-10, base_y-50, center_x+10, base_y-20, fill="gold", outline="gray", tags="spaceship")
        dish = self.canvas.create_oval(center_x-15, base_y-70, center_x+15, base_y-40, fill="silver", outline="gray", tags="spaceship")
        boom = self.canvas.create_rectangle(center_x-1, base_y-20, center_x+1, base_y+20, fill="gray", tags="spaceship")
        inst1 = self.canvas.create_rectangle(center_x-20, base_y-30, center_x-10, base_y-25, fill="darkgray", tags="spaceship")
        inst2 = self.canvas.create_rectangle(center_x+10, base_y-30, center_x+20, base_y-25, fill="darkgray", tags="spaceship")
        
        self.canvas.tag_bind(bus, "<Enter>", lambda e: self.show_tooltip("Spacecraft Bus", "Holds scientific instruments and computers"))
        self.canvas.tag_bind(dish, "<Enter>", lambda e: self.show_tooltip("High-Gain Antenna", "Communicates with Earth across billions of miles"))
        self.canvas.tag_bind(boom, "<Enter>", lambda e: self.show_tooltip("Magnetometer Boom", "Measures magnetic fields in space"))
        self.canvas.tag_bind(inst1, "<Enter>", lambda e: self.show_tooltip("Cosmic Ray Detector", "Studies high-energy particles from space"))

    def show_tooltip(self, title, description):
        self.status_label.config(text=f"{title}: {description}")

    def show_facts(self):
        ship = self.spacecraft[self.current_ship]
        facts = {
            "shuttle": (
                "Space Shuttle Facts:\n"
                "- First launched: April 12, 1981\n"
                "- Length: 184 feet (56 m)\n"
                "- Wingspan: 78 feet (24 m)\n"
                "- Maximum payload: 65,000 lbs (29,500 kg)\n"
                "- Unique as the first reusable spacecraft\n"
                "- Flew 135 missions over 30 years"
            ),
            "artemis": (
                "Artemis SLS Facts:\n"
                "- First launched: November 16, 2022\n"
                "- Height: 322 feet (98 m)\n"
                "- Thrust: 8.8 million pounds\n"
                "- Payload to Moon: 59,000 lbs (27,000 kg)\n"
                "- Carries the Orion crew capsule\n"
                "- Part of NASA's return to the Moon"
            ),
            "saturn": (
                "Saturn V Facts:\n"
                "- Height: 363 feet (111 m)\n"
                "- Weight: 6.5 million pounds\n"
                "- Thrust: 7.6 million pounds\n"
                "- Launched all Apollo Moon missions\n"
                "- Remains the tallest, heaviest rocket ever flown\n"
                "- Never lost a payload in 13 launches"
            ),
            "falcon": (
                "Falcon Heavy Facts:\n"
                "- First launched: February 6, 2018\n"
                "- Height: 230 feet (70 m)\n"
                "- Thrust: 5.1 million pounds\n"
                "- Payload to LEO: 141,000 lbs (64,000 kg)\n"
                "- Features reusable boosters\n"
                "- Side boosters return to landing sites"
            ),
            "voyager": (
                "Voyager Facts:\n"
                "- Launched: September 5, 1977\n"
                "- Speed: 38,000 mph (61,000 km/h)\n"
                "- Distance from Earth: 14+ billion miles\n"
                "- Powered by radioisotope thermoelectric generators\n"
                "- Carries Golden Record with sounds of Earth\n"
                "- Entered interstellar space in 2012"
            )
        }
        messagebox.showinfo(f"🚀 {ship['name']} Information", facts[ship["id"]])

    def start_countdown(self):
        if hasattr(self, 'count_thread') and self.count_thread and self.count_thread.is_alive():
            return
        self.count_thread = threading.Thread(target=self.countdown_sequence)
        self.count_thread.daemon = True
        self.count_thread.start()

    def countdown_sequence(self):
        self.status_label.config(text="Status: Starting countdown sequence")
        time.sleep(1)
        
        for check in ["Engine check", "Fuel tanks pressurized", "Guidance systems online", "Weather clear"]:
            self.status_label.config(text=f"Status: {check}...")
            time.sleep(0.7)
        
        for i in range(10, 0, -1):
            self.status_label.config(text=f"Status: T-{i} seconds to launch")
            self.update_thrust_display(i)
            self.flicker_flame()
            time.sleep(1)
        
        self.status_label.config(text="Status: LIFT-OFF! 🚀")
        self.launch_animation()

    def update_thrust_display(self, countdown):
        thrust = 100 - (countdown * 10)
        gravity = 9.8 - (countdown * 0.1)
        self.science_label.config(text=f"Thrust: {thrust}% | Gravity: {gravity:.1f} m/s²")

    def flicker_flame(self):
        colors = ["#FF0000", "#FF5500", "#FFFF00"]
        for _ in range(5):
            color = random.choice(colors)
            self.canvas.itemconfig("spaceship", fill=color)
            self.canvas.update()
            time.sleep(0.1)
        self.canvas.itemconfig("spaceship", fill="")

    def launch_animation(self):
        self.status_label.config(text="Status: Ascending through atmosphere")
        
        mission = self.mission_var.get()
        if mission == "Earth Orbit":
            target_altitude = 400
            orbit_radius = 150
        elif mission == "Moon Mission":
            target_altitude = 380000
            orbit_radius = 500
        elif mission == "Mars Expedition":
            target_altitude = 78000000
            orbit_radius = 800
        elif mission == "Jupiter Flyby":
            target_altitude = 628000000
            orbit_radius = 1200
        else:
            target_altitude = 1000000000
            orbit_radius = 1500
        
        for step in range(80):
            self.canvas.move("spaceship", 0, -5)
            altitude = step * target_altitude // 80
            gravity = max(1.0, 9.8 - (step * 0.12))
            thrust = 100 if step < 60 else 70
            self.science_label.config(text=f"Mission: {mission} | Altitude: {altitude} km | Thrust: {thrust}% | Gravity: {gravity:.1f} m/s²")
            
            if step > 20:
                for _ in range(3):
                    width = self.canvas.winfo_width()
                    height = self.canvas.winfo_height()
                    x = random.randint(width//2-50, width//2+50)
                    y = random.randint(height-100, height-50)
                    size = random.randint(2, 8)
                    self.canvas.create_oval(x, y, x+size, y+size, fill="#FF5500", tags="effect")
            
            self.canvas.update()
            time.sleep(0.05)
        
        self.canvas.delete("effect")
        self.status_label.config(text=f"Status: Achieving orbit for {mission}")
        self.simulate_orbit(orbit_radius)

    def simulate_orbit(self, orbit_radius):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        body_size = orbit_radius // 3
        
        if self.mission_var.get() == "Earth Orbit":
            color = "#2277CC"
        elif self.mission_var.get() == "Moon Mission":
            color = "#AAAAAA"
        elif self.mission_var.get() == "Mars Expedition":
            color = "#FF5500"
        elif self.mission_var.get() == "Jupiter Flyby":
            color = "#D8CA9D"
        else:
            color = "#666699"
        
        celestial_body = self.canvas.create_oval(
            width-body_size, height//2-body_size, width+body_size, height//2+body_size, 
            fill=color, outline="", tags="celestial"
        )
        
        orbit = self.canvas.create_oval(
            width//2-orbit_radius, height//2-orbit_radius,
            width//2+orbit_radius, height//2+orbit_radius,
            outline="#444444", dash=(4, 4), width=1, tags="orbit"
        )
        
        craft = self.canvas.create_oval(
            width//2+orbit_radius-5, height//2-5, 
            width//2+orbit_radius+5, height//2+5, 
            fill="white", tags="craft"
        )
        
        for angle in range(0, 360, 3):
            rad = math.radians(angle)
            x = width//2 + orbit_radius * math.cos(rad)
            y = height//2 + orbit_radius * math.sin(rad)
            self.canvas.coords(craft, x-5, y-5, x+5, y+5)
            speed = 28000 - (200 * math.sin(rad*2))
            self.science_label.config(text=f"Orbit: {int(speed)} km/h | Altitude: {orbit_radius*10} km")
            self.canvas.update()
            time.sleep(0.03)
        
        self.status_label.config(text="Status: Mission accomplished! Ready for next mission")
        self.science_label.config(text="Thrust: 0% | Gravity: 9.8 m/s²")
        self.canvas.delete("celestial")
        self.canvas.delete("orbit")
        self.canvas.delete("craft")

    def show_solar_system(self):
        self.mode = "solar"
        self.canvas.delete("all")
        self.create_stars()
        self.title.config(text="Solar System Explorer")
        self.ship_name.config(text="Our Solar System")
        self.status_label.config(text="Status: Exploring our cosmic neighborhood")
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        sun_size = 30
        self.canvas.create_oval(
            width//8-sun_size, height//2-sun_size,
            width//8+sun_size, height//2+sun_size,
            fill="#FFCC00", outline="#FF9900", width=2
        )
        
        planet_objects = []
        for i, planet in enumerate(self.planets):
            x = width//8 + planet["distance"]
            y = height//2
            size = planet["size"]
            planet_obj = self.canvas.create_oval(x-size, y-size, x+size, y+size, 
                                               fill=planet["color"], tags=planet["name"])
            self.canvas.tag_bind(planet_obj, "<Button-1>", 
                                lambda e, p=planet: self.show_planet_info(p))
            planet_objects.append(planet_obj)
            self.canvas.create_oval(
                width//8-planet["distance"], height//2-planet["distance"],
                width//8+planet["distance"], height//2+planet["distance"],
                outline="#333366", dash=(2, 2)
            )
        
        self.canvas.create_text(width//8, height//2-sun_size-10, text="Sun", fill="white", font=("Arial", 10))
        for i, planet in enumerate(self.planets):
            x = width//8 + planet["distance"]
            y = height//2 - planet["size"] - 10
            self.canvas.create_text(x, y, text=planet["name"], fill="white", font=("Arial", 9))

    def show_planet_info(self, planet):
        facts = {
            "Mercury": "Closest planet to the Sun\nSurface temperature: 430°C (day) to -180°C (night)\nNo moons",
            "Venus": "Hottest planet (475°C)\nThick toxic atmosphere\nRotates backwards",
            "Earth": "Only known planet with life\n71% covered in water\n1 Moon",
            "Mars": "The Red Planet\nLargest volcano in solar system (Olympus Mons)\n2 moons: Phobos and Deimos",
            "Jupiter": "Largest planet\nGreat Red Spot is a giant storm\n79 known moons",
            "Saturn": "Famous for its rings\nLess dense than water\n62 moons",
            "Uranus": "Rotates on its side\nBlue-green from methane gas\n27 moons",
            "Neptune": "Windiest planet (2,100 km/h winds)\nDiscovered through math\n14 moons"
        }
        messagebox.showinfo(f"Planet {planet['name']}", facts[planet["name"]])
        self.progress["solar"] = min(len(self.planets), self.progress["solar"] + 1)
        self.update_progress_bar()
        self.save_progress()

    def start_quiz(self):
        self.quiz_score = 0
        self.quiz_question = 0
        self.ask_question()

    def ask_question(self):
        questions = [
            {
                "question": "What force propels a rocket upward?",
                "options": ["Gravity", "Thrust", "Magnetism", "Friction"],
                "answer": 1
            },
            {
                "question": "Which planet is known as the Red Planet?",
                "options": ["Venus", "Jupiter", "Mars", "Saturn"],
                "answer": 2
            },
            {
                "question": "What was the first animal in space?",
                "options": ["Dog (Laika)", "Chimpanzee", "Monkey", "Cat"],
                "answer": 0
            },
            {
                "question": "How fast must a rocket go to escape Earth's gravity?",
                "options": ["1,000 km/h", "10,000 km/h", "28,000 km/h", "40,000 km/h"],
                "answer": 3
            },
            {
                "question": "Which of these is NOT a real NASA spacecraft?",
                "options": ["Voyager", "Cassini", "Enterprise", "Galileo"],
                "answer": 2
            },
            {
                "question": "What is the largest planet in our solar system?",
                "options": ["Earth", "Jupiter", "Saturn", "Neptune"],
                "answer": 1
            },
            {
                "question": "Who was the first human to walk on the Moon?",
                "options": ["Yuri Gagarin", "Buzz Aldrin", "Neil Armstrong", "John Glenn"],
                "answer": 2
            }
        ]
        
        if self.quiz_question < len(questions):
            q = questions[self.quiz_question]
            self.quiz_window = tk.Toplevel(self.root)
            self.quiz_window.title(f"Space Quiz - Question {self.quiz_question+1}")
            self.quiz_window.geometry("500x300")
            self.quiz_window.config(bg="#000033")
            self.quiz_window.attributes('-topmost', True)
            
            Label(self.quiz_window, text=q["question"], font=("Arial", 14, "bold"), 
                 fg="white", bg="#000033", wraplength=450).pack(pady=20)
            
            for i, option in enumerate(q["options"]):
                Button(self.quiz_window, text=option, font=("Arial", 12), 
                      width=30, bg="#444466", fg="white", 
                      command=lambda idx=i: self.check_answer(idx, q["answer"])).pack(pady=5)
        else:
            self.progress["quiz"] = 5
            self.update_progress_bar()
            self.save_progress()
            messagebox.showinfo("Quiz Complete", 
                               f"Your score: {self.quiz_score}/{len(questions)}\n"
                               f"Great job, space explorer!")

    def check_answer(self, selected, correct):
        if selected == correct:
            self.quiz_score += 1
            self.status_label.config(text="Status: Correct answer!")
        else:
            self.status_label.config(text="Status: Try the next one!")
        
        self.quiz_question += 1
        self.quiz_window.destroy()
        self.ask_question()

    def show_training(self):
        self.mode = "training"
        self.canvas.delete("all")
        self.create_stars()
        self.title.config(text="Astronaut Training Center")
        self.ship_name.config(text="Prepare for Space!")
        self.status_label.config(text="Status: Learning to be an astronaut")
        
        training_frame = Frame(self.canvas, bg="#000033")
        training_frame.pack(pady=20)
        
        modules = ["Physical Training", "Simulations", "Space Living"]
        for module in modules:
            Button(training_frame, text=module, font=("Arial", 12), bg="#444466", fg="white",
                   command=lambda m=module: self.show_module(m)).pack(pady=10)

    def show_module(self, module):
        info = {
            "Physical Training": "Astronauts must be in top physical shape. They exercise daily in space to combat muscle and bone loss.",
            "Simulations": "Astronauts train in simulators that mimic spacecraft and space station environments.",
            "Space Living": "In space, astronauts eat specially prepared food, sleep in sleeping bags, and use special toilets."
        }
        messagebox.showinfo(module, info[module])

    def show_timeline(self):
        self.mode = "timeline"
        self.canvas.delete("all")
        self.create_stars()
        self.title.config(text="NASA Mission Timeline")
        self.ship_name.config(text="Key Space Missions")
        self.status_label.config(text="Status: Exploring space history")
        
        timeline_canvas = Canvas(self.canvas, bg="black", highlightthickness=0)
        timeline_canvas.pack(fill=tk.BOTH, expand=True)
        
        missions = [
            {"name": "Apollo 11", "date": "1969", "desc": "First Moon landing"},
            {"name": "Voyager 1", "date": "1977", "desc": "First probe to interstellar space"},
            {"name": "Space Shuttle", "date": "1981", "desc": "First reusable spacecraft"},
            {"name": "Hubble Telescope", "date": "1990", "desc": "Revolutionized astronomy"},
            {"name": "ISS", "date": "1998", "desc": "International Space Station"},
            {"name": "Mars Rover", "date": "2004", "desc": "Exploration of Mars"},
            {"name": "Artemis", "date": "2022", "desc": "Return to the Moon"}
        ]
        
        for i, mission in enumerate(missions):
            x = 100 + i * 150
            y = 100
            rect = timeline_canvas.create_rectangle(x-50, y-30, x+50, y+30, fill="#444466", tags=mission["name"])
            timeline_canvas.create_text(x, y, text=mission["name"], fill="white", font=("Arial", 10))
            timeline_canvas.create_text(x, y+20, text=mission["date"], fill="gray", font=("Arial", 8))
            timeline_canvas.tag_bind(rect, "<Button-1>", lambda e, m=mission: self.show_mission_info(m))
        
        timeline_canvas.create_line(50, 100, 100 + len(missions)*150, 100, fill="white", width=2)

    def show_mission_info(self, mission):
        messagebox.showinfo(mission["name"], f"{mission['date']}: {mission['desc']}")

    def show_fun_fact(self):
        facts = [
            "The Sun is so big that about 1.3 million Earths could fit inside it.",
            "Venus spins in the opposite direction to most other planets.",
            "A day on Venus is longer than a year on Venus.",
            "Mars has the largest volcano in the solar system, Olympus Mons.",
            "Jupiter's Great Red Spot is a storm that has been raging for over 300 years.",
            "Saturn's rings are made mostly of ice particles.",
            "Uranus rotates on its side, making its seasons very extreme.",
            "Neptune was discovered using mathematics before it was seen with a telescope.",
            "The International Space Station orbits Earth every 90 minutes.",
            "The first living creatures in space were fruit flies in 1947."
        ]
        fact = random.choice(facts)
        messagebox.showinfo("Fun Space Fact", fact)

if __name__ == "__main__":
    create_tables()
    root = tk.Tk()
    root.withdraw()
    login_window = tk.Toplevel(root)
    login_app = LoginWindow(login_window, root)
    root.mainloop()