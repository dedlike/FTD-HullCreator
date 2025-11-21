import tkinter as tk
from tkinter import messagebox
import json
import os
import glob
import numpy as np
import copy

# --- CONFIGURATION ---
DONOR_BLUEPRINT = "donor.blueprint"
OUTPUT_BLUEPRINT = "generated_hull.blueprint"
ITEMDUP_FOLDER = "ItemDup"
MATERIAL_FILTER = "Alloy" 

# --- ROTATION SETTINGS ---
ROT_BEAM      = 0 
ROT_LEFT_IN   = 19  
ROT_RIGHT_IN  = 17  
ROT_LEFT_OUT  = 18  
ROT_RIGHT_OUT = 16  
ROT_LEFT_STERN  = 19  
ROT_RIGHT_STERN = 17  

# --- VISUAL THEME ---
THEME_BG = "#C4F4FF"          
THEME_GRID_MINOR = "#BCE8F2"  
THEME_GRID_MAJOR = "#94C8D6"  
THEME_HULL_FILL = "#555555"   
THEME_HULL_OUTLINE = "#000000" 
THEME_CENTER_LINE = "#FFFFFF" 
THEME_PANEL_BG = "#D4D0C8"    
THEME_TEXT = "#000000"        

class HullDesigner:
    def __init__(self, root):
        self.root = root
        self.root.title("FTD Hull Designer (Final + Preset)")
        self.root.configure(bg=THEME_PANEL_BG)
        
        self.points = [(0, 0)] 
        
        # Defaults
        self.var_height = tk.IntVar(value=3)
        self.var_undercut = tk.IntVar(value=5)
        self.var_floor = tk.BooleanVar(value=True)
        
        # Logical Dimensions
        self.var_limit_width = tk.IntVar(value=40) 
        self.var_limit_length = tk.IntVar(value=100) 
        
        # View State
        self.grid_size = 10.0 
        self.offset_x = 0
        self.offset_y = 20
        self.phys_w = 800 
        self.phys_h = 600 
        
        self.setup_ui()
        
    def setup_ui(self):
        self.main_container = tk.Frame(self.root, bg=THEME_PANEL_BG)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.controls = tk.Frame(self.main_container, bg=THEME_PANEL_BG, padx=10, pady=10, relief=tk.RAISED, bd=2)
        self.controls.pack(side=tk.RIGHT, fill=tk.Y)
        
        lbl_opts = {"bg": THEME_PANEL_BG, "fg": THEME_TEXT, "font": ("MS Sans Serif", 10)}
        
        # --- EXPORT ---
        self.btn_export = tk.Button(self.controls, text="EXPORT", command=self.run_generator, 
                                    bg=THEME_PANEL_BG, relief=tk.RAISED, bd=3, font=("MS Sans Serif", 9, "bold"), pady=5)
        self.btn_export.pack(pady=10, fill=tk.X)
        
        # --- PRESET BUTTON (NEW) ---
        tk.Button(self.controls, text="Load Preset (100m)", command=self.load_preset, 
                  bg=THEME_PANEL_BG, relief=tk.RAISED, bd=2).pack(pady=5, fill=tk.X)
        
        # --- STATS ---
        grp_stats = tk.LabelFrame(self.controls, text="Ship Stats", bg=THEME_PANEL_BG, font=("MS Sans Serif", 9, "bold"))
        grp_stats.pack(fill=tk.X, pady=5, padx=5)
        
        self.lbl_stats_len = tk.Label(grp_stats, text="Length: 0m", width=15, anchor="w", **lbl_opts)
        self.lbl_stats_len.pack(anchor="w")
        self.lbl_stats_beam = tk.Label(grp_stats, text="Beam: 1m", width=15, anchor="w", **lbl_opts)
        self.lbl_stats_beam.pack(anchor="w")

        # --- DESIGN LIMITS ---
        grp_canvas = tk.LabelFrame(self.controls, text="Design Limits", bg=THEME_PANEL_BG, font=("MS Sans Serif", 9))
        grp_canvas.pack(fill=tk.X, pady=5, padx=5)
        
        tk.Label(grp_canvas, text="Length (m):", **lbl_opts).pack(anchor="w")
        s_l = tk.Spinbox(grp_canvas, from_=20, to=2000, textvariable=self.var_limit_length, width=10)
        s_l.pack(pady=2)
        s_l.bind("<Return>", lambda e: self.force_redraw())
        tk.Button(grp_canvas, text="Resize View", command=self.force_redraw, bg=THEME_PANEL_BG, relief=tk.RAISED, bd=2).pack(pady=5, fill=tk.X)

        # --- GENERATOR SETTINGS ---
        grp_dim = tk.LabelFrame(self.controls, text="Generator Settings", bg=THEME_PANEL_BG, font=("MS Sans Serif", 9))
        grp_dim.pack(fill=tk.X, pady=5, padx=5)
        
        tk.Label(grp_dim, text="Deck Height:", **lbl_opts).pack(anchor="w")
        tk.Spinbox(grp_dim, from_=1, to=50, textvariable=self.var_height, width=10).pack(pady=2)
        
        tk.Label(grp_dim, text="Undercut Layers:", **lbl_opts).pack(anchor="w")
        tk.Spinbox(grp_dim, from_=0, to=20, textvariable=self.var_undercut, width=10).pack(pady=2)
        
        tk.Checkbutton(grp_dim, text="Generate Floor", variable=self.var_floor, bg=THEME_PANEL_BG).pack(anchor="w", pady=5)

        self.lbl_info = tk.Label(self.controls, text="L-Click: Add Point\nR-Click: Undo\n\nDraw on either side\nof the center line.", 
                                 justify=tk.LEFT, bg=THEME_PANEL_BG, fg="#444")
        self.lbl_info.pack(pady=20)
        
        self.lbl_cursor = tk.Label(self.controls, text="Cursor: -", width=25, bg=THEME_PANEL_BG, font=("Courier New", 9))
        self.lbl_cursor.pack(side=tk.BOTTOM, pady=5)

        self.canvas_frame = tk.Frame(self.main_container, bg="black", bd=2, relief=tk.SUNKEN)
        self.canvas_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg=THEME_BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Button-1>", self.add_point)
        self.canvas.bind("<Button-3>", self.remove_point)
        self.canvas.bind("<Motion>", self.update_cursor)

    def load_preset(self):
        """Loads the predefined hull shape."""
        # Format: (Z_Length, X_Distance_From_Center)
        # Calculation: (Total_Beam - 1) / 2
        self.points = [
            (0, 0),   # Tip (1m Beam)
            (4, 2),   # User Point 1 (3m Beam -> 1 block from center)
            (14, 4),  # User Point 2 (7m Beam -> 3 blocks from center)
            (39, 6),  # User Point 3 (11m Beam -> 5 blocks from center)
            (69, 6),  # User Point 4 (11m Beam -> 5 blocks from center)
            (85, 5),  # User Point 5 (7m Beam -> 3 blocks from center)
            (100, 3)  # User Point 6 (5m Beam -> 2 blocks from center)
        ]
        
        # Update limits to match the preset
        self.var_limit_length.set(100)
        
        # Force update
        self.recalc_view()
        self.update_stats()

    def on_resize(self, event):
        self.phys_w = event.width
        self.phys_h = event.height
        self.recalc_view()

    def force_redraw(self):
        self.recalc_view()

    def recalc_view(self):
        try:
            log_len = int(self.var_limit_length.get())
        except ValueError:
            return

        if self.phys_w <= 1 or self.phys_h <= 1: return

        padding_px = 40
        available_h = self.phys_h - padding_px
        if available_h < 10: available_h = 10
        
        self.grid_size = available_h / log_len
        
        available_w = self.phys_w
        total_width_blocks = available_w / self.grid_size
        half_width = int(total_width_blocks / 2)
        self.var_limit_width.set(half_width)
        
        self.offset_x = 0
        self.offset_y = 20 
        
        self.draw_grid()
        self.redraw_shape()
        self.update_stats()

    def to_screen(self, gx, gz):
        log_w_half = int(self.var_limit_width.get())
        center_screen_x = self.offset_x + (log_w_half * self.grid_size)
        
        sx = center_screen_x + (gx * self.grid_size)
        sy = self.offset_y + (gz * self.grid_size)
        return sx, sy

    def to_grid(self, sx, sy):
        log_w_half = int(self.var_limit_width.get())
        center_screen_x = self.offset_x + (log_w_half * self.grid_size)
        
        dist_px = sx - center_screen_x
        gx = dist_px / self.grid_size
        gz = (sy - self.offset_y) / self.grid_size
        return gx, gz

    def draw_grid(self):
        self.canvas.delete("grid")
        
        log_w_half = int(self.var_limit_width.get())
        log_h = int(self.var_limit_length.get())
        center_x = self.offset_x + (log_w_half * self.grid_size)
        
        start_x = 0
        end_x = self.phys_w
        start_y = self.offset_y
        end_y = self.offset_y + (log_h * self.grid_size)
        
        for i in range(log_w_half * 2 + 1):
            # Right
            xr = center_x + (i * self.grid_size)
            if xr <= end_x:
                is_major = i % 10 == 0
                color = THEME_GRID_MAJOR if is_major else THEME_GRID_MINOR
                if is_major or self.grid_size > 3:
                    self.canvas.create_line(xr, start_y, xr, end_y, fill=color, tags="grid")
            # Left
            xl = center_x - (i * self.grid_size)
            if xl >= start_x:
                is_major = i % 10 == 0
                color = THEME_GRID_MAJOR if is_major else THEME_GRID_MINOR
                if is_major or self.grid_size > 3:
                    self.canvas.create_line(xl, start_y, xl, end_y, fill=color, tags="grid")

        for i in range(log_h + 1):
            y = start_y + (i * self.grid_size)
            is_major = i % 10 == 0
            color = THEME_GRID_MAJOR if is_major else THEME_GRID_MINOR
            if is_major or self.grid_size > 3:
                self.canvas.create_line(start_x, y, end_x, y, fill=color, tags="grid")
        
        self.canvas.create_line(center_x, start_y, center_x, end_y, fill=THEME_CENTER_LINE, width=2, dash=(6, 4), tags="grid")
        self.canvas.create_text(center_x, start_y - 10, text="BOW", fill="#444", font=("Arial", 10, "bold"), tags="grid")
        self.canvas.create_text(center_x, end_y + 10, text="STERN", fill="#444", font=("Arial", 10, "bold"), tags="grid")

    def update_cursor(self, event):
        gx, gz = self.to_grid(event.x, event.y)
        width_m = int(abs(gx)) * 2 + 1
        self.lbl_cursor.config(text=f"Width at Cursor: {width_m}m")

    def update_stats(self):
        if not self.points:
            l, b = 0, 0
        else:
            l = self.points[-1][0]
            max_x = 0
            for z, x in self.points:
                if x > max_x: max_x = x
            b = max_x * 2 + 1
        self.lbl_stats_len.config(text=f"Length: {l}m")
        self.lbl_stats_beam.config(text=f"Beam: {b}m")

    def add_point(self, event):
        raw_gx, raw_gz = self.to_grid(event.x, event.y)
        gx = int(round(abs(raw_gx)))
        gz = int(round(raw_gz))
        if gz < 0: gz = 0
        
        if not self.points or gz > self.points[-1][0]:
            self.points.append((gz, gx))
            self.redraw_shape()
            self.update_stats()

    def remove_point(self, event):
        if len(self.points) > 1:
            self.points.pop()
            self.redraw_shape()
            self.update_stats()

    def redraw_shape(self):
        self.canvas.delete("shape")
        self.canvas.delete("points")
        if not self.points: return
        
        poly_points = []
        for z, x in self.points:
            sx, sy = self.to_screen(x, z)
            poly_points.append((sx, sy))
        for z, x in reversed(self.points):
            sx, sy = self.to_screen(-x, z)
            poly_points.append((sx, sy))
            
        if len(poly_points) > 2:
            self.canvas.create_polygon(poly_points, fill=THEME_HULL_FILL, outline=THEME_HULL_OUTLINE, width=2, tags="shape")
            
        for z, x in self.points:
            rx, ry = self.to_screen(x, z)
            self.canvas.create_oval(rx-2, ry-2, rx+2, ry+2, fill="#BBB", outline="black", tags="points")
            lx, ly = self.to_screen(-x, z)
            self.canvas.create_oval(lx-2, ly-2, lx+2, ly+2, fill="#BBB", outline="black", tags="points")

    def run_generator(self):
        if len(self.points) < 2: return
        max_z = self.points[-1][0]
        z_coords = [p[0] for p in self.points]
        x_coords = [p[1] for p in self.points]
        full_z = np.arange(max_z + 1)
        full_x = np.interp(full_z, z_coords, x_coords)
        hull_profile = np.round(full_x).astype(int)
        
        height = int(self.var_height.get())
        undercut = int(self.var_undercut.get())
        do_floor = self.var_floor.get()
        center_offset = int(self.var_limit_width.get())
        
        generator = BlueprintGenerator(hull_profile, center_offset, height, undercut, do_floor)
        generator.generate()
        messagebox.showinfo("Success", f"Generated {OUTPUT_BLUEPRINT}")


class BlueprintGenerator:
    def __init__(self, profile, center_offset, height, undercut, do_floor):
        self.profile = profile
        self.center_offset = center_offset
        self.height = height
        self.undercut = undercut
        self.do_floor = do_floor
        self.placements = [] 
        
        self.beam_guids = {
            4: "f63c9b75-2473-424d-9a56-b25847324143",
            3: "44667921-6554-4589-b52c-c89794776685",
            2: "1643d621-6452-4d38-98cd-07130b232e65",
            1: "3cc75979-18ac-46c4-9a5b-25b327d99410",
        }
        self.slope_guids = {
            4: "33840566-0e0a-4d01-8333-f465d84a49c9",
            3: "0838778a-76d1-4289-8700-f5e6310f7b7a",
            2: "0158534b-8732-40ae-a085-e0d09cf3679f",
            1: "84951250-1854-4da5-9765-5c244a0c8980",
        }
        self.offset_guids = {} 
        self.load_assets()

    def load_assets(self):
        if not os.path.exists(ITEMDUP_FOLDER): return
        files = glob.glob(os.path.join(ITEMDUP_FOLDER, "*.itemdup")) + \
                glob.glob(os.path.join(ITEMDUP_FOLDER, "*.ITEMDUPLICATEANDMODIFY"))
        for f in files:
            try:
                with open(f, 'r') as jf: data = json.load(jf)
                name = data.get("InventoryNameOverride", "").lower()
                fname = os.path.basename(f).lower()
                if MATERIAL_FILTER.lower() not in name and MATERIAL_FILTER.lower() not in fname: continue
                
                guid = data["ComponentId"]["Guid"]
                sp, sn = data["SizeInfo"]["SizePos"], data["SizeInfo"]["SizeNeg"]
                
                length = 0
                if "4m" in name or "4m" in fname: length = 4
                elif "3m" in name or "3m" in fname: length = 3
                elif "2m" in name or "2m" in fname: length = 2
                elif "1m" in name or "1m" in fname: length = 1
                else:
                    length = max(sp["x"]+sn["x"]+1, sp["y"]+sn["y"]+1, sp["z"]+sn["z"]+1)

                if length == 0: continue

                if "offset" not in name and "offset" not in fname:
                    if "slope" in name or "slope" in fname:
                        self.slope_guids[length] = guid
                    else:
                        self.beam_guids[length] = guid
                else:
                    if length not in self.offset_guids:
                        self.offset_guids[length] = {"left": None, "right": None}
                    if "left" in name or "left" in fname:
                        self.offset_guids[length]["left"] = guid
                    elif "right" in name or "right" in fname:
                        self.offset_guids[length]["right"] = guid
            except: pass

    def generate(self):
        best_placements = []
        best_run_score = float('inf')
        print("Starting Solver...")
        
        for forced_1m_zone in range(0, 25):
            score, result = self.simulate_hull(forced_1m_zone)
            if result is not None:
                if score < best_run_score:
                    best_run_score = score
                    best_placements = result
        
        if best_placements:
            print(f"Optimal hull found. Score: {best_run_score}")
            self.placements = best_placements
        else:
            print("Fallback used.")
            _, self.placements = self.simulate_hull(1)
        
        self.fill_stern()
        self.stack_layers()
        self.generate_undercut()
        
        if self.do_floor:
            self.generate_floor()
        
        self.save_to_blueprint()

    def fill_stern(self):
        if not self.profile.any(): return
        stern_x_index = self.profile[-1]
        dist_from_center = stern_x_index # Updated math
        z_pos = 0
        start_x = -(dist_from_center - 1)
        end_x = (dist_from_center - 1)
        guid_1m = self.beam_guids.get(1)
        if not guid_1m: return
        if start_x <= end_x:
            for x in range(start_x, end_x + 1):
                beam_props = {"type": "beam", "len": 1, "offset": 0, "is_stern": False}
                entry = {'pos': (x, 10, z_pos), 'rot': ROT_BEAM, 'guid': guid_1m, 'props': beam_props}
                self.placements.append(entry)

    def stack_layers(self):
        if self.height <= 1: return
        base_layer = list(self.placements)
        self.placements = []
        for h in range(self.height):
            offset_y = h
            for p in base_layer:
                new_p = copy.deepcopy(p)
                x, y, z = new_p['pos']
                new_p['pos'] = (x, y - offset_y, z)
                self.placements.append(new_p)

    def generate_undercut(self):
        if self.undercut <= 0: return
        
        min_y = min(p['pos'][1] for p in self.placements)
        parent_layer = [p for p in self.placements if p['pos'][1] == min_y]
        
        max_z = max(p['pos'][2] for p in parent_layer) if parent_layer else 0
        ship_center_z = max_z / 2

        for u in range(1, self.undercut + 1):
            current_undercut_y = min_y - u
            new_layer = []
            occupied_coords = set() 
            placed_offsets = [] 
            
            for parent in parent_layer:
                props = parent['props']
                if props['type'] == 'beam': continue
                
                if props['type'] == 'slope':
                    length = props['len']
                    is_stern = props['is_stern']
                    rot = parent['rot']
                    
                    offset_guid = None
                    is_left_rot = rot in [ROT_LEFT_IN, ROT_LEFT_STERN, ROT_LEFT_OUT]
                    is_right_rot = rot in [ROT_RIGHT_IN, ROT_RIGHT_STERN, ROT_RIGHT_OUT]
                    
                    if is_stern:
                        if is_left_rot and length in self.offset_guids: offset_guid = self.offset_guids[length]["left"]
                        elif is_right_rot and length in self.offset_guids: offset_guid = self.offset_guids[length]["right"]
                    else:
                        if is_left_rot and length in self.offset_guids: offset_guid = self.offset_guids[length]["right"]
                        elif is_right_rot and length in self.offset_guids: offset_guid = self.offset_guids[length]["left"]
                    
                    if not offset_guid: continue 

                    z_shift = 1 if is_stern else -1
                    x, y, z = parent['pos']
                    new_pos = (x, current_undercut_y, z + z_shift)
                    
                    if is_stern:
                        for i in range(length): occupied_coords.add((new_pos[0], new_pos[2] - i))
                    else:
                        for i in range(length): occupied_coords.add((new_pos[0], new_pos[2] + i))
                    
                    new_entry = {
                        'pos': new_pos, 'rot': rot, 'guid': offset_guid, 'props': props 
                    }
                    new_layer.append(new_entry)
                    placed_offsets.append(new_entry)

            raw_beam_voxels = []
            for parent in parent_layer:
                if parent['props']['type'] == 'beam':
                    length = parent['props']['len']
                    px, py, pz = parent['pos']
                    
                    beam_z_shift = -1 if pz > ship_center_z else 1
                    shifted_pz = pz + beam_z_shift
                    
                    for z_offset in range(length):
                        voxel_z = shifted_pz + z_offset
                        voxel_x = px
                        if (voxel_x, voxel_z) not in occupied_coords:
                             raw_beam_voxels.append((voxel_x, voxel_z))
                             occupied_coords.add((voxel_x, voxel_z))

            for off in placed_offsets:
                x = off['pos'][0]
                z_anchor = off['pos'][2]
                length = off['props']['len']
                is_stern = off['props']['is_stern']
                
                if is_stern:
                    start_z = z_anchor + 1
                    direction = 1
                else:
                    start_z = z_anchor - 1
                    direction = -1
                
                current_z = start_z
                for _ in range(50): 
                    if (x, current_z) in occupied_coords: break 
                    has_neighbor = (x-1, current_z) in occupied_coords or (x+1, current_z) in occupied_coords
                    
                    raw_beam_voxels.append((x, current_z))
                    occupied_coords.add((x, current_z))
                    
                    if has_neighbor: break
                    current_z += direction

            optimized_beams = self.optimize_beams(raw_beam_voxels, current_undercut_y)
            new_layer.extend(optimized_beams)
            
            self.placements.extend(new_layer)
            parent_layer = new_layer

    def generate_floor(self):
        if not self.placements: return
        
        min_y = min(p['pos'][1] for p in self.placements)
        occupied = set()
        
        for p in self.placements:
            if p['pos'][1] == min_y:
                length = p['props']['len']
                px, py, pz = p['pos']
                is_stern = p['props'].get('is_stern', False)
                
                if is_stern:
                    for i in range(length): occupied.add((px, pz - i))
                else:
                    for i in range(length): occupied.add((px, pz + i))
        
        if not occupied: return
        
        min_z = min(z for x, z in occupied)
        max_z = max(z for x, z in occupied)
        
        raw_floor_voxels = []
        
        for z in range(min_z, max_z + 1):
            xs_at_z = [x for x, _z in occupied if _z == z]
            if not xs_at_z: continue
            
            min_x = min(xs_at_z)
            max_x = max(xs_at_z)
            
            for x in range(min_x + 1, max_x):
                if (x, z) not in occupied:
                    raw_floor_voxels.append((x, z))
                    occupied.add((x, z))
        
        floor_beams = self.optimize_beams(raw_floor_voxels, min_y)
        self.placements.extend(floor_beams)

    def optimize_beams(self, voxels, y_level):
        by_x = {}
        for x, z in voxels:
            if x not in by_x: by_x[x] = []
            by_x[x].append(z)
        
        optimized = []
        for x, z_list in by_x.items():
            z_list = sorted(list(set(z_list))) 
            if not z_list: continue
            
            runs = []
            if z_list:
                current_run = [z_list[0]]
                for i in range(1, len(z_list)):
                    if z_list[i] == z_list[i-1] + 1:
                        current_run.append(z_list[i])
                    else:
                        runs.append(current_run)
                        current_run = [z_list[i]]
                runs.append(current_run)
                
            for run in runs:
                start_z = run[0]
                total_len = len(run)
                current_fill_z = start_z
                
                while total_len > 0:
                    chosen = 1
                    for size in [4, 3, 2, 1]:
                        if size <= total_len and size in self.beam_guids:
                            chosen = size
                            break
                    
                    guid = self.beam_guids[chosen]
                    props = {"type": "beam", "len": chosen, "offset": 0, "is_stern": False}
                    
                    entry = {
                        'pos': (x, y_level, current_fill_z),
                        'rot': ROT_BEAM,
                        'guid': guid,
                        'props': props
                    }
                    optimized.append(entry)
                    current_fill_z += chosen
                    total_len -= chosen
        return optimized

    def simulate_hull(self, forced_1m_zone):
        temp_placements = []
        L = len(self.profile)
        current_z = 0
        current_min_len = 1 
        total_penalty = 0
        
        while current_z < L:
            x_current = self.profile[current_z]
            dist_current = x_current 
            
            best_choice = None
            min_step_cost = float('inf')
            
            all_lengths = sorted(list(set(list(self.slope_guids.keys()) + list(self.beam_guids.keys()))), reverse=True)
            limit_len = 99
            if current_z < forced_1m_zone: limit_len = 1
            
            candidates = []
            for l in all_lengths:
                if l > limit_len: continue
                if l in self.slope_guids:
                    candidates.append({"type": "slope", "len": l, "offset": -1, "is_stern": False, "guid": self.slope_guids[l]})
                    candidates.append({"type": "slope", "len": l, "offset": 1, "is_stern": True, "guid": self.slope_guids[l]})
                if l in self.beam_guids:
                    candidates.append({"type": "beam", "len": l, "offset": 0, "is_stern": False, "guid": self.beam_guids[l]})

            for cand in candidates:
                b_len = cand["len"]
                if current_z + b_len > L: continue
                
                target_x = self.profile[current_z + b_len - 1]
                if current_z + b_len < L: target_x = self.profile[current_z + b_len]
                else: target_x = self.profile[-1]

                dist_ideal = dist_current - cand["offset"] 
                error = abs(target_x - dist_ideal)
                
                if error > 1.0: continue 
                
                fit_penalty = error * 50 
                len_penalty = (current_min_len - b_len) * 10 if b_len < current_min_len else -(b_len * 2)
                efficiency_cost = 10 
                total_step_cost = len_penalty + efficiency_cost + fit_penalty
                
                valid_lookahead = True
                if b_len > 1:
                    lookahead_z = current_z + int(b_len * 1.5)
                    if lookahead_z < L:
                        future_x = self.profile[lookahead_z]
                        ratio = (lookahead_z - current_z) / b_len
                        dist_fut_ideal = dist_current - (cand["offset"] * ratio)
                        if abs(future_x - dist_fut_ideal) > 1.0: valid_lookahead = False
                if not valid_lookahead: continue

                if total_step_cost < min_step_cost:
                    min_step_cost = total_step_cost
                    best_choice = cand

            if not best_choice:
                total_penalty += 200
                current_min_len = 1
                if 1 in self.slope_guids:
                    fb_cands = [
                        {"type": "slope", "len": 1, "offset": -1, "is_stern": False, "guid": self.slope_guids[1]},
                        {"type": "slope", "len": 1, "offset": 1, "is_stern": True, "guid": self.slope_guids[1]},
                        {"type": "beam", "len": 1, "offset": 0, "is_stern": False, "guid": self.beam_guids.get(1)}
                    ]
                    best_err = float('inf')
                    for c in fb_cands:
                        if not c["guid"]: continue
                        if current_z + c["len"] > L: continue
                        tx = self.profile[current_z+1] if current_z+1 < L else self.profile[-1]
                        di = dist_current - c["offset"]
                        if abs(tx - di) < best_err: best_err = abs(tx - di); best_choice = c
                
                if not best_choice: current_z += 1; continue

            total_penalty += min_step_cost
            b_len = best_choice["len"]
            current_min_len = b_len
            
            z_shift = 1 if best_choice["is_stern"] else b_len
            placement_z = L - (current_z + z_shift)
            
            gx_left = -dist_current
            gx_right = dist_current
            rot_left = ROT_BEAM
            rot_right = ROT_BEAM
            
            if best_choice["type"] == "slope":
                if best_choice["is_stern"]:
                    rot_left = ROT_LEFT_STERN
                    rot_right = ROT_RIGHT_STERN
                else:
                    if best_choice["offset"] == -1: 
                        rot_left = ROT_LEFT_OUT; rot_right = ROT_RIGHT_OUT; gx_left -= 1; gx_right += 1
                    else:
                        rot_left = ROT_LEFT_IN; rot_right = ROT_RIGHT_IN

            entry_left = {'pos': (gx_left, 10, placement_z), 'rot': rot_left, 'guid': best_choice["guid"], 'props': best_choice}
            entry_right = {'pos': (gx_right, 10, placement_z), 'rot': rot_right, 'guid': best_choice["guid"], 'props': best_choice}
            
            temp_placements.append(entry_left)
            temp_placements.append(entry_right)
            
            current_z += b_len
            
        return total_penalty, temp_placements

    def save_to_blueprint(self):
        if not os.path.exists(DONOR_BLUEPRINT): 
            messagebox.showerror("Error", f"Missing {DONOR_BLUEPRINT}")
            return
        with open(DONOR_BLUEPRINT, "r") as f: bp = json.load(f)
        
        bp["Blueprint"]["SCs"] = []; bp["Blueprint"]["BP1"] = None; bp["Blueprint"]["BP2"] = None
        guid_map = {}; next_id = 1000
        bp["Blueprint"]["BLP"] = []; bp["Blueprint"]["BLR"] = []; bp["Blueprint"]["BlockIds"] = []; bp["Blueprint"]["BCI"] = []
        
        for p in self.placements:
            pos = p['pos']
            rot = p['rot']
            guid = p['guid']
            
            if guid not in guid_map: guid_map[guid] = next_id; next_id += 1
            bp["Blueprint"]["BLP"].append(f"{int(pos[0])},{int(pos[1])},{int(pos[2])}")
            bp["Blueprint"]["BLR"].append(int(rot))
            bp["Blueprint"]["BlockIds"].append(int(guid_map[guid]))
            bp["Blueprint"]["BCI"].append(0)

        if "ItemDictionary" not in bp: bp["ItemDictionary"] = {}
        for g, i in guid_map.items(): bp["ItemDictionary"][str(i)] = g
        
        count = len(self.placements)
        bp["Blueprint"]["BlockState"] = f"=0,{count}"
        bp["Blueprint"]["TotalBlockCount"] = count
        bp["Blueprint"]["AliveCount"] = count
        bp["SavedTotalBlockCount"] = count
        
        with open(OUTPUT_BLUEPRINT, "w") as f: json.dump(bp, f)

if __name__ == "__main__":
    root = tk.Tk()
    app = HullDesigner(root)
    root.mainloop()