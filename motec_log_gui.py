import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import sys
import subprocess

LAST_DIR_FILE = os.path.join(os.path.expanduser("~"), ".motec_log_gui_lastdir.json")
LOG_TYPES = ["CAN", "CSV", "ACCESSPORT", "MCAP"]

# Metadata fields: (label, variable name, default, type)
METADATA_FIELDS = [
    ("Driver", "driver", "", str),
    ("Vehicle ID", "vehicle_id", "", str),
    ("Vehicle Weight", "vehicle_weight", 0, int),
    ("Vehicle Type", "vehicle_type", "", str),
    ("Vehicle Comment", "vehicle_comment", "", str),
    ("Venue Name", "venue_name", "", str),
    ("Event Name", "event_name", "", str),
    ("Event Session", "event_session", "", str),
    ("Long Comment", "long_comment", "", str),
    ("Short Comment", "short_comment", "", str),
]

def load_last_dir():
    if os.path.exists(LAST_DIR_FILE):
        try:
            with open(LAST_DIR_FILE, "r") as f:
                return json.load(f).get("last_dir", os.path.expanduser("~"))
        except Exception:
            return os.path.expanduser("~")
    return os.path.expanduser("~")

def save_last_dir(path):
    d = os.path.dirname(path) if os.path.isfile(path) else path
    with open(LAST_DIR_FILE, "w") as f:
        json.dump({"last_dir": d}, f)

def get_default_output(log_path):
    if not log_path:
        return ""
    candump_dir, candump_filename = os.path.split(log_path)
    candump_filename = os.path.splitext(candump_filename)[0]
    return os.path.join(candump_dir, candump_filename + ".ld")

class MotecLogGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MoTeC Log Generator GUI")
        self.geometry("600x700")
        self.resizable(False, True)
        self.last_dir = load_last_dir()
        self.vars = {}
        self.create_widgets()

    def create_widgets(self):
        row = 0
        tk.Label(self, text="Log Type:").grid(row=row, column=0, sticky="e")
        self.vars["log_type"] = tk.StringVar(value=LOG_TYPES[0])
        log_type_menu = tk.OptionMenu(self, self.vars["log_type"], *LOG_TYPES, command=self.on_log_type_change)
        log_type_menu.grid(row=row, column=1, sticky="w")
        row += 1

        tk.Label(self, text="Log File:").grid(row=row, column=0, sticky="e")
        self.vars["log"] = tk.StringVar()
        log_entry = tk.Entry(self, textvariable=self.vars["log"], width=50)
        log_entry.grid(row=row, column=1, sticky="w")
        tk.Button(self, text="Browse", command=self.browse_log).grid(row=row, column=2)
        row += 1

        tk.Label(self, text="DBC File (CAN only):").grid(row=row, column=0, sticky="e")
        self.vars["dbc"] = tk.StringVar()
        dbc_entry = tk.Entry(self, textvariable=self.vars["dbc"], width=50)
        dbc_entry.grid(row=row, column=1, sticky="w")
        tk.Button(self, text="Browse", command=self.browse_dbc).grid(row=row, column=2)
        row += 1

        tk.Label(self, text="Output File:").grid(row=row, column=0, sticky="e")
        self.vars["output"] = tk.StringVar()
        output_entry = tk.Entry(self, textvariable=self.vars["output"], width=50)
        output_entry.grid(row=row, column=1, sticky="w")
        tk.Button(self, text="Browse", command=self.browse_output).grid(row=row, column=2)
        row += 1

        tk.Label(self, text="Frequency (Hz):").grid(row=row, column=0, sticky="e")
        self.vars["frequency"] = tk.DoubleVar(value=20.0)
        tk.Entry(self, textvariable=self.vars["frequency"], width=10).grid(row=row, column=1, sticky="w")
        row += 1

        # Metadata fields
        for label, varname, default, _ in METADATA_FIELDS:
            tk.Label(self, text=label+":").grid(row=row, column=0, sticky="e")
            self.vars[varname] = tk.StringVar(value=str(default))
            tk.Entry(self, textvariable=self.vars[varname], width=50).grid(row=row, column=1, sticky="w", columnspan=2)
            row += 1

        self.status = tk.Label(self, text="", fg="blue")
        self.status.grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        # Convert and Open buttons
        button_frame = tk.Frame(self)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        self.convert_btn = tk.Button(button_frame, text="Convert", command=self.run_conversion, bg="#4CAF50", fg="white")
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        self.open_btn = tk.Button(button_frame, text="Open", command=self.open_output_folder, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=5)

        self.on_log_type_change(LOG_TYPES[0])
        self.vars["log"].trace_add("write", self.on_log_path_change)

    def on_log_type_change(self, value):
        if value == "CAN":
            self.vars["dbc"].set("")
            for child in self.grid_slaves():
                if hasattr(child, "grid_info") and child.grid_info().get("row") == 2:
                    child.configure(state="normal")
        else:
            self.vars["dbc"].set("")
            for child in self.grid_slaves():
                if hasattr(child, "grid_info") and child.grid_info().get("row") == 2:
                    child.configure(state="disabled")

    def on_log_path_change(self, *args):
        log_path = self.vars["log"].get()
        if log_path:
            self.vars["output"].set(get_default_output(log_path))

    def browse_log(self):
        path = filedialog.askopenfilename(
            initialdir=self.last_dir,
            title="Select Log File",
            filetypes=[
                ("Supported Logs", "*.mcap *.log *.csv"),
                ("MCAP Files", "*.mcap"),
                ("Log Files", "*.log"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ]
        )
        if path:
            self.vars["log"].set(path)
            self.last_dir = os.path.dirname(path)
            save_last_dir(self.last_dir)

    def browse_dbc(self):
        path = filedialog.askopenfilename(initialdir=self.last_dir, title="Select DBC File", filetypes=[("DBC Files", "*.dbc"), ("All Files", "*.*")])
        if path:
            self.vars["dbc"].set(path)
            self.last_dir = os.path.dirname(path)
            save_last_dir(self.last_dir)

    def browse_output(self):
        path = filedialog.asksaveasfilename(initialdir=self.last_dir, title="Select Output File", defaultextension=".ld", filetypes=[("MoTeC LD Files", "*.ld"), ("All Files", "*.*")])
        if path:
            self.vars["output"].set(path)
            self.last_dir = os.path.dirname(path)
            save_last_dir(self.last_dir)

    def open_output_folder(self):
        output_path = self.vars["output"].get()
        if output_path:
            folder = os.path.dirname(output_path)
            if not folder:
                folder = os.getcwd()
            if sys.platform.startswith('win'):
                os.startfile(folder)
            elif sys.platform.startswith('darwin'):
                subprocess.Popen(['open', folder])
            else:
                subprocess.Popen(['xdg-open', folder])

    def run_conversion(self):
        args = [sys.executable, os.path.join(os.path.dirname(__file__), "motec_log_generator.py")]
        args += [self.vars["log"].get(), self.vars["log_type"].get()]
        if self.vars["output"].get():
            args += ["--output", self.vars["output"].get()]
        args += ["--frequency", str(self.vars["frequency"].get())]
        if self.vars["log_type"].get() == "CAN":
            if not self.vars["dbc"].get():
                messagebox.showerror("Error", "DBC file is required for CAN logs.")
                return
            args += ["--dbc", self.vars["dbc"].get()]
        for _, varname, _, typ in METADATA_FIELDS:
            val = self.vars[varname].get()
            if typ == int:
                try:
                    val = int(val)
                except Exception:
                    val = 0
            if val != "" and val != 0:
                args += [f"--{varname}", str(val)]
        self.status.config(text="Running conversion...")
        self.update()
        self.open_btn.config(state=tk.DISABLED)
        try:
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode == 0:
                self.status.config(text="Done! Output: " + self.vars["output"].get(), fg="green")
                messagebox.showinfo("Success", "Conversion complete!\nOutput: " + self.vars["output"].get())
                self.open_btn.config(state=tk.NORMAL)
            else:
                self.status.config(text="Error: " + result.stderr, fg="red")
                messagebox.showerror("Error", result.stderr)
        except Exception as e:
            self.status.config(text="Error: " + str(e), fg="red")
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    MotecLogGUI().mainloop()
