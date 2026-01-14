import math
import keyboard
import openvr
import time
import numpy as np
import os
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import pyautogui
import json

# --- DEFAULTS ---
DEFAULT_GAME_PATH = 'E:/SteamLibrary/steamapps/common/Fallout New Vegas'
DEFAULT_PIP_POS = [-0.18, 0.17, -0.2]
DEFAULT_PIP_ROT = [200.51, -50.9, -60.27]
DEFAULT_MENU_POS = [-0.10, 0.40, 0.10]
DEFAULT_MENU_ROT = [0.0, 0.0, 0.0]

# Default "Safe" positions
DEFAULT_HK_POS = [0.0, -1.0, 0.0]
DEFAULT_HK_ROT = [0.0, 0.0, 0.0]

DEFAULT_HOLSTER_CUTOFF = -0.55

CONFIG_FILE = 'fnvr_config.txt'

# Global Offsets
PitchOffset = 0.0
RollOffset = 0.0
YawOffset = 0.0
XOffset = 0.0
YOffset = 0.0
ZOffset = 0.0
ADJUST_SPEED = 0.5

# Disable PyAutoGUI fail-safe
pyautogui.FAILSAFE = False


def get_pose_matrix(pose):
    """ Convert OpenVR Pose to a 4x4 Numpy Matrix. """
    m = pose.mDeviceToAbsoluteTracking
    return np.array([
        [m[0][0], m[0][1], m[0][2], m[0][3]],
        [m[1][0], m[1][1], m[1][2], m[1][3]],
        [m[2][0], m[2][1], m[2][2], m[2][3]],
        [0, 0, 0, 1]
    ])


def rotation_matrix_to_euler_angles(R):
    """ Returns angles in Degrees: [Pitch (X), Yaw (Y), Roll (Z)] """
    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
    singular = sy < 1e-6

    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0

    return np.array([math.degrees(x), math.degrees(y), math.degrees(z)])


class SimpleTrackingApp:
    def __init__(self, gui_callback=None):
        self.vr_system = None
        self.controllers = []
        self.active_controller_idx = 0
        self.secondary_controller_idx = -1
        self.current_vals = {}
        # Used for manual offset anchoring
        self.anchor_vals = None

        self.fpXr_current = 0.0
        self.fpZr_current = 0.0
        self.lerp_speed = 8.0
        self.last_time = time.time()
        self.running = False
        self.gui_callback = gui_callback

        self.hmd_pos = [0.0, 0.0, 0.0]
        self.hmd_rot = [0.0, 0.0, 0.0]
        self.controller_pos = [0.0, 0.0, 0.0]
        self.controller_rot = [0.0, 0.0, 0.0]
        self.secondary_controller_pos = [0.0, 0.0, 0.0]
        self.secondary_controller_rot = [0.0, 0.0, 0.0]

        self.last_x_press_time = 0
        self.x_was_pressed = False

        # Defaults
        self.game_dir = DEFAULT_GAME_PATH
        self.test_dir = ""
        self.holster_cutoff = DEFAULT_HOLSTER_CUTOFF

        # Target Data Storage
        self.targets = {
            "pipboy": {"pos": list(DEFAULT_PIP_POS), "rot": list(DEFAULT_PIP_ROT)},
            "menu": {"pos": list(DEFAULT_MENU_POS), "rot": list(DEFAULT_MENU_ROT)},
        }
        # Initialize Hotkeys 1-8
        for k in range(1, 9):
            self.targets[str(k)] = {"pos": list(DEFAULT_HK_POS), "rot": list(DEFAULT_HK_ROT)}

        self.pos_sensitivity = 0.15
        self.rot_sensitivity = 40.0

        # Gesture States
        self.gesture_active_type = "NONE"

        # Pipboy Sequence Vars
        self.gesture_sequence_active = False
        self.last_activation_time = 0
        self.fpXr_override = 0.0
        self.tab_pressed = False
        self.cooldown_period = 2.0
        self.activation_duration = 2.2

        # Menu Sequence Vars
        self.menu_sequence_active = False
        self.last_menu_activation_time = 0
        self.menu_esc_pressed = False
        self.menu_cooldown = 2.0

        # Hotkey Hold State Tracking
        self.hotkey_states = {}
        for k in range(1, 9):
            self.hotkey_states[str(k)] = {'is_held': False}

        # Load Configuration
        self.load_config()
        self.update_test_dir_path()

        try:
            self.vr_system = openvr.init(openvr.VRApplication_Background)
            print("VR System Initialized")
            self.find_controllers()
        except openvr.OpenVRError as e:
            print(f"Error: {e}")

    def load_config(self):
        default_config = {
            "game_directory": DEFAULT_GAME_PATH,
            "holster_cutoff": DEFAULT_HOLSTER_CUTOFF,
            "pipboy_pos": DEFAULT_PIP_POS, "pipboy_rot": DEFAULT_PIP_ROT,
            "menu_pos": DEFAULT_MENU_POS, "menu_rot": DEFAULT_MENU_ROT,
        }
        # Add defaults for keys 1-8
        for k in range(1, 9):
            default_config[f"{k}_pos"] = DEFAULT_HK_POS
            default_config[f"{k}_rot"] = DEFAULT_HK_ROT

        if not os.path.exists(CONFIG_FILE):
            print("Config file not found. Creating default.")
            self.save_config(default_config)
            data = default_config
        else:
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print("Config file corrupted. Using defaults.")
                data = default_config

        self.game_dir = data.get("game_directory", DEFAULT_GAME_PATH)
        self.holster_cutoff = data.get("holster_cutoff", DEFAULT_HOLSTER_CUTOFF)

        for key in self.targets.keys():
            self.targets[key]["pos"] = data.get(f"{key}_pos", DEFAULT_PIP_POS if key == "pipboy" else DEFAULT_HK_POS)
            self.targets[key]["rot"] = data.get(f"{key}_rot", DEFAULT_PIP_ROT if key == "pipboy" else DEFAULT_HK_ROT)

    def save_config(self, data_override=None):
        if data_override:
            data = data_override
        else:
            data = {
                "game_directory": self.game_dir,
                "holster_cutoff": self.holster_cutoff
            }
            for key, val in self.targets.items():
                data[f"{key}_pos"] = val["pos"]
                data[f"{key}_rot"] = val["rot"]

        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print("Configuration saved.")

    def set_game_directory(self, path):
        if path:
            self.game_dir = path
            self.update_test_dir_path()
            self.save_config()

    def update_test_dir_path(self):
        self.test_dir = os.path.join(self.game_dir, "Data", "NVSE", "Test")
        if not os.path.exists(self.test_dir):
            try:
                os.makedirs(self.test_dir, exist_ok=True)
            except Exception as e:
                print(f"Directory Creation Error: {e}")

    def set_target_from_secondary(self, target_key):
        if self.secondary_controller_idx != -1:
            self.targets[target_key]["pos"] = list(self.secondary_controller_pos)
            self.targets[target_key]["rot"] = list(self.secondary_controller_rot)
            print(f"Set {target_key} Target: {self.targets[target_key]['pos']}")
            self.save_config()

    def reset_target(self, target_key):
        if target_key == "pipboy":
            self.targets[target_key]["pos"] = list(DEFAULT_PIP_POS)
            self.targets[target_key]["rot"] = list(DEFAULT_PIP_ROT)
        elif target_key == "menu":
            self.targets[target_key]["pos"] = list(DEFAULT_MENU_POS)
            self.targets[target_key]["rot"] = list(DEFAULT_MENU_ROT)
        else:
            self.targets[target_key]["pos"] = list(DEFAULT_HK_POS)
            self.targets[target_key]["rot"] = list(DEFAULT_HK_ROT)
        self.save_config()

    def find_controllers(self):
        self.controllers = []
        for i in range(openvr.k_unMaxTrackedDeviceCount):
            if self.vr_system.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_Controller:
                role = self.vr_system.getControllerRoleForTrackedDeviceIndex(i)
                role_name = "Left" if role == openvr.TrackedControllerRole_LeftHand else "Right"
                self.controllers.append({'index': i, 'role': role_name})

    def cycle_controller(self):
        if self.controllers:
            self.active_controller_idx = (self.active_controller_idx + 1) % len(self.controllers)
            return self.controllers[self.active_controller_idx]['role']
        return "None"

    def cycle_secondary_controller(self):
        if len(self.controllers) >= 2:
            self.secondary_controller_idx += 1
            if self.secondary_controller_idx >= len(self.controllers):
                self.secondary_controller_idx = -1
            return "None" if self.secondary_controller_idx == -1 else self.controllers[self.secondary_controller_idx][
                'role']
        return "None"

    def is_match(self, target_pos, target_rot):
        pos_dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(self.secondary_controller_pos, target_pos)))
        rot_diffs = [abs(a - b) for a, b in zip(self.secondary_controller_rot, target_rot)]
        rot_diffs = [min(d, 360 - d) for d in rot_diffs]
        return (pos_dist <= self.pos_sensitivity) and all(d <= self.rot_sensitivity for d in rot_diffs)

    def check_gestures(self):
        """Main loop to check all gesture types."""
        if self.secondary_controller_idx == -1:
            self.gesture_active_type = "NONE"
            return

        # 1. Pipboy
        pip_match = self.is_match(self.targets["pipboy"]["pos"], self.targets["pipboy"]["rot"])

        if pip_match:
            self.gesture_active_type = "PIPBOY"
            now = time.time()
            if not self.gesture_sequence_active and not self.menu_sequence_active:
                if (now - self.last_activation_time > (self.activation_duration + self.cooldown_period)):
                    self.start_pipboy_sequence()
        elif self.is_match(self.targets["menu"]["pos"], self.targets["menu"]["rot"]):
            self.gesture_active_type = "MENU"
            now = time.time()
            if not self.menu_sequence_active and not self.gesture_sequence_active:
                if (now - self.last_menu_activation_time > self.menu_cooldown):
                    self.start_menu_sequence()
        else:
            self.gesture_active_type = "NONE"

        # 3. Check Hotkeys 1-8
        self.update_hotkeys()

    def update_hotkeys(self):
        """Updates instantaneous hotkey presses based on gesture presence."""
        for k in range(1, 9):
            key = str(k)
            matched = self.is_match(self.targets[key]["pos"], self.targets[key]["rot"])
            state = self.hotkey_states[key]

            if matched:
                if not state['is_held']:
                    keyboard.press(key)
                    state['is_held'] = True
                    print(f"Hotkey {key} DOWN")

                # Update status for UI
                if self.gesture_active_type == "NONE":
                    self.gesture_active_type = f"HOLDING {key}"
            else:
                if state['is_held']:
                    keyboard.release(key)
                    state['is_held'] = False
                    print(f"Hotkey {key} UP")

    def start_pipboy_sequence(self):
        self.gesture_sequence_active = True
        self.last_activation_time = time.time()
        self.fpXr_override = 1.0
        self.tab_pressed = False

    def update_pipboy_logic(self):
        if not self.gesture_sequence_active:
            self.fpXr_override = 0.0
            return

        elapsed = time.time() - self.last_activation_time
        if elapsed >= 1.0 and not self.tab_pressed:
            keyboard.press('Tab')
            time.sleep(0.05)
            keyboard.release('Tab')
            self.tab_pressed = True

        if elapsed >= self.activation_duration:
            self.gesture_sequence_active = False
            self.fpXr_override = 0.0

    def start_menu_sequence(self):
        self.menu_sequence_active = True
        self.last_menu_activation_time = time.time()
        self.menu_esc_pressed = False
        print("Menu Sequence Started")

    def update_menu_logic(self):
        if not self.menu_sequence_active:
            return

        elapsed = time.time() - self.last_menu_activation_time
        if not self.menu_esc_pressed:
            keyboard.press('esc')
            self.menu_esc_pressed = True

        if elapsed >= 0.1:
            keyboard.release('esc')
            self.menu_sequence_active = False
            print("Menu Sequence Ended")

    def reset_offsets(self):
        global PitchOffset, RollOffset, YawOffset, XOffset, YOffset, ZOffset
        PitchOffset = RollOffset = YawOffset = XOffset = YOffset = ZOffset = 0.0

    def handle_manual_offsets(self):
        global PitchOffset, RollOffset, YawOffset, XOffset, YOffset, ZOffset
        is_x_down = keyboard.is_pressed('x')
        if is_x_down and not self.x_was_pressed:
            current_time = time.time()
            if current_time - self.last_x_press_time < 1.0:
                self.reset_offsets()
                self.last_x_press_time = 0
            else:
                self.last_x_press_time = current_time
        self.x_was_pressed = is_x_down

    def update_encoded_filename(self, dt):
        """
        Calculates values for both controllers and writes to the filename.
        Format: iX_iY_iZ_iXr_iYr_iZr_pXr_iX2_iY2_iZ2_iXr2_iYr2_iZr2
        """
        try:
            # --- 1. Primary Controller Calculation ---
            # NOTE: self.controller_pos/rot were already updated in run_loop before this call

            # Holster Cutoff Check (Done before transform, specific to Primary)
            iX_raw, iY_raw, iZ_raw = self.controller_pos
            iXr_raw, iYr_raw, iZr_raw = self.controller_rot

            if iZ_raw < self.holster_cutoff:
                # Apply holster static values
                iX_raw, iY_raw, iZ_raw = -0.4, 0.1, -0.17
                iXr_raw, iYr_raw, iZr_raw = 5.0, 40.0, 0.0

            # Primary Transformations
            adj_X = (iX_raw * 85) + XOffset - 2
            adj_Y = (iY_raw * 45) + YOffset - 0
            adj_Z = (iZ_raw * 70) + ZOffset - 5.42
            adj_Pitch = iYr_raw + PitchOffset - 4
            adj_Yaw = iXr_raw + YawOffset + 4
            adj_Roll = iZr_raw + RollOffset

            # Swizzle for game engine
            p_iX = adj_Y
            p_iY = (adj_X * -1) - 10
            p_iZ = adj_Z
            p_iXr = adj_Pitch - 60
            p_iYr = adj_Roll
            p_iZr = adj_Yaw - 10

            # Pipboy Override (pXr)
            target_fpXr = self.fpXr_override
            lerp_step = min(1.0, self.lerp_speed * dt)
            self.fpXr_current += (target_fpXr - self.fpXr_current) * lerp_step

            # Update internal tracking for calculated secondary vals (used just for reference)
            target_fpZr = (adj_Pitch * 1.25) + 2
            self.fpZr_current += (target_fpZr - self.fpZr_current) * lerp_step

            # --- 2. Secondary Controller Calculation ---
            sX_raw, sY_raw, sZ_raw = self.secondary_controller_pos
            sXr_raw, sYr_raw, sZr_raw = self.secondary_controller_rot

            # Secondary Transformations
            # Apply same constant world offsets and scaling, but ignore dynamic manual offsets (XOffset etc)
            s_adj_X = (sX_raw * 85) - 2
            s_adj_Y = (sY_raw * 45) - 0
            s_adj_Z = (sZ_raw * 70) - 5.42
            s_adj_Pitch = sYr_raw - 4
            s_adj_Yaw = sXr_raw + 4
            s_adj_Roll = sZr_raw

            # Swizzle for game engine
            s_iX = s_adj_Y
            s_iY = (s_adj_X * -1) - 10
            s_iZ = s_adj_Z
            s_iXr = s_adj_Pitch - 60
            s_iYr = s_adj_Roll
            s_iZr = s_adj_Yaw - 10

            # --- 3. Construct Output List ---
            output_values = [
                p_iX, p_iY, p_iZ, p_iXr, p_iYr, p_iZr,  # Primary
                self.fpXr_current,  # Pipboy Trigger
                s_iX, s_iY, s_iZ, s_iXr, s_iYr, s_iZr  # Secondary
            ]

            encoded_name = "_".join([f"{v:.2f}" for v in output_values])

            if not os.path.exists(self.test_dir):
                return

            files = os.listdir(self.test_dir)
            if not files:
                with open(os.path.join(self.test_dir, encoded_name), 'w') as f:
                    f.write("VR")
            else:
                old_path = os.path.join(self.test_dir, files[0])
                new_path = os.path.join(self.test_dir, encoded_name)
                if old_path != new_path: os.rename(old_path, new_path)
        except Exception as e:
            # Fail silently to avoid crashing thread on file IO race conditions
            pass

    def get_relative_transform(self, hmd_matrix_inv, device_pose):
        dev_m = get_pose_matrix(device_pose)
        rel_m = hmd_matrix_inv @ dev_m
        rel_pos = rel_m[:3, 3]
        euler_angles = rotation_matrix_to_euler_angles(rel_m[:3, :3])
        rel_rot = [euler_angles[1], euler_angles[0], euler_angles[2]]
        return rel_pos, rel_rot

    def apply_roll_correction(self, yaw, pitch, roll):
        p_adj = pitch - 45.0
        y_adj = yaw
        rad_roll = math.radians(roll)
        cos_r = math.cos(rad_roll)
        sin_r = math.sin(rad_roll)
        p_new = (p_adj * cos_r) - (y_adj * sin_r)
        y_new = (p_adj * sin_r) + (y_adj * cos_r)
        return y_new, p_new, roll

    def run_loop(self):
        while self.running:
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time

            self.handle_manual_offsets()
            self.update_pipboy_logic()
            self.update_menu_logic()

            poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
            self.vr_system.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0.0, poses)
            h_pose = poses[openvr.k_unTrackedDeviceIndex_Hmd]

            if h_pose and h_pose.bPoseIsValid:
                h_m = get_pose_matrix(h_pose)
                self.hmd_pos = list(h_m[:3, 3])
                h_euler = rotation_matrix_to_euler_angles(h_m[:3, :3])
                self.hmd_rot = [h_euler[0], h_euler[1], h_euler[2]]

                h_m_inv = np.linalg.inv(h_m)

                # --- Primary Controller ---
                c_idx = self.controllers[self.active_controller_idx]['index'] if self.controllers else None
                c_pose = poses[c_idx] if c_idx is not None else None

                if c_pose and c_pose.bPoseIsValid:
                    rel_pos_vec, rel_rot_vec = self.get_relative_transform(h_m_inv, c_pose)
                    self.controller_pos = [rel_pos_vec[2], rel_pos_vec[0], rel_pos_vec[1]]

                    raw_y, raw_p, raw_r = rel_rot_vec
                    adj_y, adj_p, adj_r = self.apply_roll_correction(raw_y, raw_p, raw_r)
                    adj_p += 45.0
                    self.controller_rot = [adj_y, adj_p, adj_r]

                    # Offset Logic
                    if keyboard.is_pressed('x'):
                        if self.anchor_vals is None:
                            self.anchor_vals = {
                                "iX": self.controller_pos[0], "iY": self.controller_pos[1],
                                "iZ": self.controller_pos[2],
                                "iXr": self.controller_rot[0], "iYr": self.controller_rot[1],
                                "iZr": self.controller_rot[2]
                            }
                        else:
                            global XOffset, YOffset, ZOffset, YawOffset, PitchOffset, RollOffset
                            XOffset += (self.controller_pos[0] - self.anchor_vals["iX"]) * 100
                            YOffset += (self.controller_pos[1] - self.anchor_vals["iY"]) * 100
                            ZOffset += (self.controller_pos[2] - self.anchor_vals["iZ"]) * 100
                            YawOffset += (self.controller_rot[0] - self.anchor_vals["iXr"])
                            PitchOffset += (self.controller_rot[1] - self.anchor_vals["iYr"])
                            RollOffset += (self.controller_rot[2] - self.anchor_vals["iZr"])
                            self.anchor_vals = {
                                "iX": self.controller_pos[0], "iY": self.controller_pos[1],
                                "iZ": self.controller_pos[2],
                                "iXr": self.controller_rot[0], "iYr": self.controller_rot[1],
                                "iZr": self.controller_rot[2]
                            }
                    else:
                        self.anchor_vals = None

                # --- Secondary Controller ---
                s_idx = self.controllers[self.secondary_controller_idx][
                    'index'] if 0 <= self.secondary_controller_idx < len(self.controllers) else None
                s_pose = poses[s_idx] if s_idx is not None else None

                if s_pose and s_pose.bPoseIsValid:
                    rel_pos_vec_s, rel_rot_vec_s = self.get_relative_transform(h_m_inv, s_pose)
                    self.secondary_controller_pos = [rel_pos_vec_s[2], rel_pos_vec_s[0], rel_pos_vec_s[1]]

                    s_raw_y, s_raw_p, s_raw_r = rel_rot_vec_s
                    s_adj_y, s_adj_p, s_adj_r = self.apply_roll_correction(s_raw_y, s_raw_p, s_raw_r)
                    self.secondary_controller_rot = [s_adj_y, s_adj_p, s_adj_r]

                    self.check_gestures()
                else:
                    self.secondary_controller_pos, self.secondary_controller_rot = [0, 0, 0], [0, 0, 0]
                    self.gesture_active_type = "NONE"

                # Update File with both controllers data
                if c_pose and c_pose.bPoseIsValid:
                    self.update_encoded_filename(dt)

                if self.gui_callback: self.gui_callback()
            time.sleep(0.01)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False


class TrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FNV VR Tracker Configurator")
        self.root.geometry("1040x800")

        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=1)

        canvas = tk.Canvas(main_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self.scroll_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.app = SimpleTrackingApp(gui_callback=self.update_display)

        # --- LAYOUT COLUMNS ---
        self.left_column = ttk.Frame(self.scroll_frame)
        self.left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5, anchor="n")

        self.right_column = ttk.Frame(self.scroll_frame)
        self.right_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5, anchor="n")

        # --- LEFT COLUMN WIDGETS ---

        # Directory Configuration
        config_frame = ttk.LabelFrame(self.left_column, text="Directory Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        self.dir_label = ttk.Label(config_frame, text=f"Game Folder: {self.app.game_dir}", wraplength=480)
        self.dir_label.pack(anchor=tk.W, pady=2)
        ttk.Button(config_frame, text="Set Game Directory", command=self.choose_directory).pack(anchor=tk.W, pady=5)

        # Status & Hardware Info
        status_frame = ttk.LabelFrame(self.left_column, text="Status & Hardware Info", padding="10")
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        btn_frame = ttk.Frame(status_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        self.start_btn = ttk.Button(btn_frame, text="Start Tracking", command=self.start_tracking)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Stop Tracking", command=self.stop_tracking, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(status_frame, text="Status: Stopped", font=("Arial", 10, "bold"))
        self.status_label.pack(anchor=tk.W)
        self.controller_label = ttk.Label(status_frame, text="Primary (Data): None")
        self.controller_label.pack(anchor=tk.W)
        self.sec_controller_label = ttk.Label(status_frame, text="Secondary (Trigger): None")
        self.sec_controller_label.pack(anchor=tk.W)

        # HMD Section
        hmd_frame = ttk.LabelFrame(self.left_column, text="HMD Info (World Space)", padding="10")
        hmd_frame.pack(fill=tk.X, padx=10, pady=2)
        self.hmd_pos_label = ttk.Label(hmd_frame, text="Pos: X: 0.00 Y: 0.00 Z: 0.00")
        self.hmd_pos_label.pack(anchor=tk.W)
        self.hmd_rot_label = ttk.Label(hmd_frame, text="Rot: P: 0.00 Y: 0.00 R: 0.00")
        self.hmd_rot_label.pack(anchor=tk.W)

        # Primary Controller Section
        primary_frame = ttk.LabelFrame(self.left_column, text="Primary Controller (Relative to HMD - ADJ)",
                                       padding="10")
        primary_frame.pack(fill=tk.X, padx=10, pady=5)
        self.ctrl_pos_label = ttk.Label(primary_frame, text="Pos: X: 0.00 Y: 0.00 Z: 0.00")
        self.ctrl_pos_label.pack(anchor=tk.W)
        self.ctrl_rot_label = ttk.Label(primary_frame, text="Rot: Y: 0.00 P: 0.00 R: 0.00")
        self.ctrl_rot_label.pack(anchor=tk.W)

        # Primary Button Row
        p_btn_row = ttk.Frame(primary_frame)
        p_btn_row.pack(anchor=tk.W, pady=5)
        ttk.Button(p_btn_row, text="Cycle Primary", command=self.cycle_controller).pack(side=tk.LEFT)
        self.primary_btn_label = ttk.Label(p_btn_row, text="None")
        self.primary_btn_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(primary_frame,
                  text="Do the numbers change when the correct controller is being moved? If not, cycle which controller is chosen!",
                  font=("Arial", 8, "italic"), foreground="gray", wraplength=450).pack(anchor=tk.W)

        # Secondary Controller Section
        secondary_frame = ttk.LabelFrame(self.left_column, text="Secondary Controller (Relative to HMD - ADJ)",
                                         padding="10")
        secondary_frame.pack(fill=tk.X, padx=10, pady=5)
        self.sec_ctrl_pos_label = ttk.Label(secondary_frame, text="Pos: X: 0.00 Y: 0.00 Z: 0.00")
        self.sec_ctrl_pos_label.pack(anchor=tk.W)
        self.sec_ctrl_rot_label = ttk.Label(secondary_frame, text="Rot: Y: 0.00 P: 0.00 R: 0.00")
        self.sec_ctrl_rot_label.pack(anchor=tk.W)

        # Secondary Button Row
        s_btn_row = ttk.Frame(secondary_frame)
        s_btn_row.pack(anchor=tk.W, pady=5)
        ttk.Button(s_btn_row, text="Cycle Secondary", command=self.cycle_secondary_controller).pack(side=tk.LEFT)
        self.secondary_btn_label = ttk.Label(s_btn_row, text="None")
        self.secondary_btn_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(secondary_frame,
                  text="Do the numbers change when the correct controller is being moved? If not, cycle which controller is chosen!",
                  font=("Arial", 8, "italic"), foreground="gray", wraplength=450).pack(anchor=tk.W)

        # Offsets Section
        offset_frame = ttk.LabelFrame(self.left_column, text="Offsets", padding="10")
        offset_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(offset_frame, text="Hold X to drag Offsets around. Double tap X to reset Offsets.",
                  font=("Arial", 8, "italic"), foreground="gray", wraplength=450).pack(anchor=tk.W, pady=(0, 5))

        self.offset_pos_label = ttk.Label(offset_frame, text="X: 0.00 Y: 0.00 Z: 0.00")
        self.offset_pos_label.pack(anchor=tk.W)
        self.offset_rot_label = ttk.Label(offset_frame, text="P: 0.00 R: 0.00 Y: 0.00")
        self.offset_rot_label.pack(anchor=tk.W)
        ttk.Button(offset_frame, text="Reset Offsets", command=self.reset_offsets).pack(anchor=tk.W, pady=5)

        # --- RIGHT COLUMN WIDGETS ---

        # Gesture Section
        gesture_frame = ttk.LabelFrame(self.right_column, text="Gesture Configuration", padding="10")
        gesture_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(gesture_frame,
                  text="Hold your Secondary Controller in a desired position and orientation while selecting Set Current for your desired hotkey. When you bring your Secondary Controller to this position again, the hotkey will trigger.",
                  font=("Arial", 8, "italic"), foreground="gray", wraplength=450).pack(fill=tk.X, pady=(0, 10))

        def create_config_row(parent, label_text, target_key):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label_text, width=15, font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            ttk.Button(row, text="Set Current", command=lambda: self.app.set_target_from_secondary(target_key)).pack(
                side=tk.LEFT, padx=2)
            ttk.Button(row, text="Reset", command=lambda: self.app.reset_target(target_key)).pack(side=tk.LEFT, padx=2)

        create_config_row(gesture_frame, "Pipboy:", "pipboy")
        create_config_row(gesture_frame, "Menu (Esc):", "menu")
        create_config_row(gesture_frame, "Hotkey 1:", "1")
        create_config_row(gesture_frame, "Hotkey 2:", "2")
        create_config_row(gesture_frame, "Hotkey 3:", "3")
        create_config_row(gesture_frame, "Hotkey 4:", "4")
        create_config_row(gesture_frame, "Hotkey 5:", "5")
        create_config_row(gesture_frame, "Hotkey 6:", "6")
        create_config_row(gesture_frame, "Hotkey 7:", "7")
        create_config_row(gesture_frame, "Hotkey 8:", "8")

        self.gesture_status_indicator = tk.Label(gesture_frame, text="GESTURE INACTIVE", bg="red", fg="white",
                                                 font=("Arial", 12, "bold"))
        self.gesture_status_indicator.pack(fill=tk.X, pady=10)

        # Sensitivity Inputs
        input_container = ttk.Frame(gesture_frame)
        input_container.pack(fill=tk.X, pady=5)

        ttk.Label(input_container,
                  text="Adjust how far off your controller can be from your set Gesture before triggering.",
                  font=("Arial", 8, "italic"), foreground="gray", wraplength=450).grid(row=0, column=0, columnspan=3,
                                                                                       sticky=tk.W, pady=(0, 5))

        ttk.Label(input_container, text="Position Gesture Sensitivity (m):").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.pos_entry = ttk.Entry(input_container, width=8)
        self.pos_entry.insert(0, "0.15")
        self.pos_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.pos_entry.bind("<FocusOut>", self.update_sensitivity)

        ttk.Label(input_container, text="Rotation Gesture Sensitivity (deg):").grid(row=2, column=0, sticky=tk.W,
                                                                                    padx=5)
        self.rot_entry = ttk.Entry(input_container, width=8)
        self.rot_entry.insert(0, "40.0")
        self.rot_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.rot_entry.bind("<FocusOut>", self.update_sensitivity)

        ttk.Button(input_container, text="Reset", command=self.reset_sensitivity).grid(row=1, column=2, rowspan=2,
                                                                                       padx=5)

        ttk.Label(input_container,
                  text="Distance down in meters you can lower your Primary Controller before sending a resting state to the game.",
                  font=("Arial", 8, "italic"), foreground="gray", wraplength=450).grid(row=3, column=0, columnspan=3,
                                                                                       sticky=tk.W, pady=(10, 5))

        ttk.Label(input_container, text="Holster Z Cutoff:").grid(row=4, column=0, sticky=tk.W, padx=5)
        self.cutoff_entry = ttk.Entry(input_container, width=8)
        self.cutoff_entry.insert(0, str(DEFAULT_HOLSTER_CUTOFF))
        self.cutoff_entry.grid(row=4, column=1, sticky=tk.W, pady=2)
        self.cutoff_entry.bind("<FocusOut>", self.update_sensitivity)

        ttk.Button(input_container, text="Reset", command=self.reset_holster).grid(row=4, column=2, padx=5)

    def choose_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.app.set_game_directory(directory)
            self.dir_label.config(text=f"Game Folder: {self.app.game_dir}")

    def update_sensitivity(self, _=None):
        try:
            self.app.pos_sensitivity = float(self.pos_entry.get())
            self.app.rot_sensitivity = float(self.rot_entry.get())

            cutoff_val = float(self.cutoff_entry.get())
            if self.app.holster_cutoff != cutoff_val:
                self.app.holster_cutoff = cutoff_val
                self.app.save_config()
        except ValueError:
            pass

    def reset_sensitivity(self):
        self.pos_entry.delete(0, tk.END)
        self.pos_entry.insert(0, "0.15")
        self.rot_entry.delete(0, tk.END)
        self.rot_entry.insert(0, "40.0")
        self.update_sensitivity()

    def reset_holster(self):
        self.cutoff_entry.delete(0, tk.END)
        self.cutoff_entry.insert(0, str(DEFAULT_HOLSTER_CUTOFF))
        self.update_sensitivity()

    def start_tracking(self):
        self.app.start()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Running")
        self.update_controller_labels()

    def stop_tracking(self):
        self.app.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Stopped")

    def cycle_controller(self):
        self.app.cycle_controller()
        self.update_controller_labels()

    def cycle_secondary_controller(self):
        self.app.cycle_secondary_controller()
        self.update_controller_labels()

    def reset_offsets(self):
        self.app.reset_offsets()

    def update_controller_labels(self):
        # Update Primary Info
        if self.app.controllers:
            act_data = self.app.controllers[self.app.active_controller_idx]
            info_text = f"Index: {act_data['index']}"
            self.controller_label.config(text=f"Primary (Data): {info_text}")
            self.primary_btn_label.config(text=info_text)

        # Update Secondary Info
        if 0 <= self.app.secondary_controller_idx < len(self.app.controllers):
            sec_data = self.app.controllers[self.app.secondary_controller_idx]
            info_text = f"Index: {sec_data['index']}"
            self.sec_controller_label.config(text=f"Secondary (Trigger): {info_text}")
            self.secondary_btn_label.config(text=info_text)
        else:
            self.secondary_btn_label.config(text="None")

    def update_display(self):
        self.hmd_pos_label.config(
            text=f"Pos: X: {self.app.hmd_pos[0]:.2f} Y: {self.app.hmd_pos[1]:.2f} Z: {self.app.hmd_pos[2]:.2f}")
        self.hmd_rot_label.config(
            text=f"Rot: P: {self.app.hmd_rot[0]:.2f} Y: {self.app.hmd_rot[1]:.2f} R: {self.app.hmd_rot[2]:.2f}")
        self.ctrl_pos_label.config(
            text=f"Pos: X: {self.app.controller_pos[0]:.2f} Y: {self.app.controller_pos[1]:.2f} Z: {self.app.controller_pos[2]:.2f}")
        self.ctrl_rot_label.config(
            text=f"Rot: Y: {self.app.controller_rot[0]:.2f} P: {self.app.controller_rot[1]:.2f} R: {self.app.controller_rot[2]:.2f}")
        self.sec_ctrl_pos_label.config(
            text=f"Pos: X: {self.app.secondary_controller_pos[0]:.2f} Y: {self.app.secondary_controller_pos[1]:.2f} Z: {self.app.secondary_controller_pos[2]:.2f}")
        self.sec_ctrl_rot_label.config(
            text=f"Rot: Y: {self.app.secondary_controller_rot[0]:.2f} P: {self.app.secondary_controller_rot[1]:.2f} R: {self.app.secondary_controller_rot[2]:.2f}")
        self.offset_pos_label.config(text=f"X: {XOffset:.2f} Y: {YOffset:.2f} Z: {ZOffset:.2f}")
        self.offset_rot_label.config(text=f"P: {PitchOffset:.2f} R: {RollOffset:.2f} Y: {YawOffset:.2f}")

        if self.app.gesture_sequence_active:
            self.gesture_status_indicator.config(text="PIPBOY SEQ RUNNING", bg="blue", fg="white")
        elif "HOLDING" in self.app.gesture_active_type:
            self.gesture_status_indicator.config(text=self.app.gesture_active_type, bg="orange", fg="black")
        elif "MATCHED" in self.app.gesture_active_type or "MENU" in self.app.gesture_active_type or "PIPBOY" in self.app.gesture_active_type:
            self.gesture_status_indicator.config(text=f"{self.app.gesture_active_type} MATCHED", bg="green", fg="white")
        else:
            now = time.time()
            pip_rem = (self.app.activation_duration + self.app.cooldown_period) - (now - self.app.last_activation_time)

            if pip_rem > 0:
                self.gesture_status_indicator.config(text=f"PIP COOLDOWN ({pip_rem:.1f}s)", bg="gray", fg="white")
            else:
                self.gesture_status_indicator.config(text="READY / INACTIVE", bg="red", fg="white")


if __name__ == "__main__":
    root = tk.Tk()
    gui = TrackerGUI(root)
    root.mainloop()
    openvr.shutdown()
