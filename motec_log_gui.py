import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import sys
import subprocess
import threading
import requests
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

LAST_DIR_FILE = os.path.join(os.path.expanduser("~"), ".motec_log_gui_lastdir.json")
ICON_DL_PATH = os.path.join(os.path.dirname(__file__), "icons", "squirrel.png")
LOG_TYPES = ["MCAP", "CSV", "ACCESSPORT", "CAN"]

# Metadata fields: (label, variable name, default, type)
METADATA_FIELDS = [
    ("Driver", "driver", "", str),
    ("Vehicle ID", "vehicle_id", "", str),
    ("Vehicle Weight", "vehicle_weight", "", str),
    ("Vehicle Type", "vehicle_type", "", str),
    ("Vehicle Comment", "vehicle_comment", "", str),
    ("Venue Name", "venue_name", "", str),
    ("Event Name", "event_name", "", str),
    ("Event Session", "event_session", "", str),
    ("Long Comment", "long_comment", "", str),
    ("Short Comment", "short_comment", "", str),
]

def load_last_dir():
    logger.debug("Loading last directory from %s", LAST_DIR_FILE)
    if os.path.exists(LAST_DIR_FILE):
        try:
            with open(LAST_DIR_FILE, "r") as f:
                last_dir = json.load(f).get("last_dir", os.path.expanduser("~"))
                logger.info("Loaded last directory: %s", last_dir)
                return last_dir
        except Exception as e:
            logger.warning("Failed to load last directory: %s", e)
            return os.path.expanduser("~")
    logger.info("No last directory file found, using home directory")
    return os.path.expanduser("~")

def save_last_dir(path):
    d = os.path.dirname(path) if os.path.isfile(path) else path
    try:
        with open(LAST_DIR_FILE, "w") as f:
            json.dump({"last_dir": d}, f)
        logger.info("Saved last directory: %s", d)
    except Exception as e:
        logger.warning("Failed to save last directory: %s", e)

def get_default_output(log_path):
    if not log_path:
        logger.debug("No log path provided for default output")
        return ""
    candump_dir, candump_filename = os.path.split(log_path)
    candump_filename = os.path.splitext(candump_filename)[0]
    output_path = os.path.join(candump_dir, candump_filename + ".ld")
    logger.debug("Default output path computed: %s", output_path)
    return output_path

class MotecLogGUI(tk.Tk):
    def __init__(self):
        logger.info("Initializing MotecLogGUI")
        super().__init__()
        try:
            os.makedirs(os.path.dirname(ICON_DL_PATH), exist_ok=True)
            icon = tk.PhotoImage(file=ICON_DL_PATH)
            self.iconphoto(True, icon)
            logger.info("Loaded icon from %s", ICON_DL_PATH)
        except Exception as e:
            logger.warning("Error loading icon: %s", e)
            # Try to download the icon from github
            try:
                logger.info("Attempting to download icon from GitHub...")
                response = requests.get("https://raw.githubusercontent.com/mathbrook/MotecLogGenerator/refs/heads/master/icons/squirrel.png", timeout=3)
                if response.status_code == 200:
                    with open(ICON_DL_PATH, "wb") as f:
                        f.write(response.content)
                    icon = tk.PhotoImage(file=ICON_DL_PATH)
                    self.iconphoto(True, icon)
                    logger.info("Downloaded and loaded icon from GitHub")
                else:
                    logger.warning("Failed to download icon, status code: %s", response.status_code)
            except Exception as e:
                logger.error("Error downloading icon: %s, using default.", e)
        self.title("MoTeC Log Generator GUI")
        self.resizable(False, True)
        self.last_dir = load_last_dir()
        self.vars = {}
        for displayname, varname, default, typ in METADATA_FIELDS:
            self.vars[varname] = tk.StringVar(value=str(default) if default is not None else "")
        self.base_font = ("PMingLiU-ExtB", 14)
        self.entry_font = ("PMingLiU-ExtB", 14)
        self.button_font = ("PMingLiU-ExtB", 14, "bold")
        self.pad = 20
        self.create_widgets()
        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())
        self.geometry("")
        logger.info("GUI initialized")

    def create_widgets(self):
        logger.debug("Creating widgets")
        container = tk.Frame(self)
        container.pack(padx=self.pad, pady=self.pad, fill="both", expand=True)
        row = 0
        self.widget_refs = {}
        def add_label(text, width=None):
            logger.debug("Adding label: %s", text)
            if width is not None:
                return tk.Label(container, text=text, font=self.base_font, width=width)
            else:
                return tk.Label(container, text=text, font=self.base_font)
        def add_entry(var, width=50):
            logger.debug("Adding entry")
            return tk.Entry(container, textvariable=var, width=width, font=self.entry_font)
        def add_button(text, cmd):
            logger.debug("Adding button: %s", text)
            return tk.Button(container, text=text, command=cmd, font=self.button_font)
        def add_tooltip(widget, text):
            tooltip = None
            after_id = None
            def show_tooltip(event):
                nonlocal tooltip
                if tooltip is not None:
                    return
                tooltip = tk.Toplevel(self)
                tooltip.withdraw()
                tooltip.overrideredirect(True)
                label = tk.Label(tooltip, text=text, font=("PMingLiU-ExtB", 12), relief=tk.SOLID, borderwidth=1, padx=6, pady=2)
                label.pack()
                x = event.widget.winfo_rootx() + 20
                y = event.widget.winfo_rooty() + 30
                tooltip.geometry(f"+{x}+{y}")
                tooltip.deiconify()
            def schedule_tooltip(event):
                nonlocal after_id
                after_id = self.after(400, lambda e=event: show_tooltip(e))
            def hide_tooltip(event):
                nonlocal tooltip, after_id
                if after_id:
                    self.after_cancel(after_id)
                    after_id = None
                if tooltip:
                    tooltip.destroy()
                    tooltip = None
            widget.bind("<Enter>", schedule_tooltip)
            widget.bind("<Leave>", hide_tooltip)

        # Log Type label (short width)
        log_type_label = add_label("Log Type:", width=12)
        log_type_label.grid(row=row, column=0, sticky="e", pady=6, padx=6)
        self.vars["log_type"] = tk.StringVar(value=LOG_TYPES[0])
        log_type_menu = tk.OptionMenu(container, self.vars["log_type"], *LOG_TYPES, command=self.on_log_type_change)
        log_type_menu.config(font=self.base_font)
        log_type_menu['menu'].config(font=self.base_font)
        log_type_menu.grid(row=row, column=1, sticky="ew", pady=6, padx=6, columnspan=2)
        add_tooltip(log_type_menu, "Select the type of log file you want to convert.")
        row += 1

        add_label("Log File:").grid(row=row, column=0, sticky="e", pady=6, padx=6)
        self.vars["log"] = tk.StringVar()
        log_entry = add_entry(self.vars["log"])
        log_entry.grid(row=row, column=1, sticky="ew", pady=6, padx=6)
        log_browse_btn = add_button("Browse", self.browse_log)
        log_browse_btn.grid(row=row, column=2, pady=6, padx=6)
        add_tooltip(log_entry, "Path to the log file (.mcap, .log, .csv)")
        add_tooltip(log_browse_btn, "Browse for a log file.")
        row += 1

        add_label("DBC File (CAN only):").grid(row=row, column=0, sticky="e", pady=6, padx=6)
        self.vars["dbc"] = tk.StringVar()
        dbc_entry = add_entry(self.vars["dbc"])
        dbc_entry.grid(row=row, column=1, sticky="ew", pady=6, padx=6)
        dbc_browse_btn = add_button("Browse", self.browse_dbc)
        dbc_browse_btn.grid(row=row, column=2, pady=6, padx=6)
        add_tooltip(dbc_entry, "Path to the DBC file (required for CAN logs)")
        add_tooltip(dbc_browse_btn, "Browse for a DBC file.")
        self.widget_refs['dbc_entry'] = dbc_entry
        self.widget_refs['dbc_browse_btn'] = dbc_browse_btn
        # Set initial DBC entry state
        dbc_entry.config(state="normal")
        row += 1

        add_label("Output File:").grid(row=row, column=0, sticky="e", pady=6, padx=6)
        self.vars["output"] = tk.StringVar()
        output_entry = add_entry(self.vars["output"])
        output_entry.grid(row=row, column=1, sticky="ew", pady=6, padx=6)
        output_browse_btn = add_button("Browse", self.browse_output)
        output_browse_btn.grid(row=row, column=2, pady=6, padx=6)
        add_tooltip(output_entry, "Path for the output .ld file.")
        add_tooltip(output_browse_btn, "Browse for output file location.")
        row += 1

        add_label("Frequency (Hz):").grid(row=row, column=0, sticky="e", pady=6, padx=6)
        self.vars["frequency"] = tk.DoubleVar(value=20.0)
        freq_entry = tk.Entry(container, textvariable=self.vars["frequency"], width=10, font=self.entry_font)
        freq_entry.grid(row=row, column=1, sticky="ew", pady=6, padx=6, columnspan=2)
        add_tooltip(freq_entry, "Sample frequency for output log.")
        row += 1

        self.status = tk.Label(container, text="", font=("PMingLiU-ExtB", 12, "italic"))
        self.status.grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        row += 1

        button_frame = tk.Frame(container)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        self.convert_btn = tk.Button(button_frame, text="Convert", command=self.run_conversion, font=self.button_font)
        self.convert_btn.pack(side=tk.LEFT, padx=10)
        self.open_btn = tk.Button(button_frame, text="Open", command=self.open_output_folder, state=tk.DISABLED, font=self.button_font)
        self.open_btn.pack(side=tk.LEFT, padx=10)
        metadata_btn = tk.Button(button_frame, text="Metadata...", command=self.open_metadata_dialog, font=self.button_font)
        metadata_btn.pack(side=tk.LEFT, padx=10)
        add_tooltip(self.convert_btn, "Convert the log file to MoTeC format.")
        add_tooltip(self.open_btn, "Open the output folder.")
        add_tooltip(metadata_btn, "Edit metadata fields for the log file.")

        for i in range(3):
            container.grid_columnconfigure(i, weight=1)
        container.grid_rowconfigure(row+1, weight=1)
        self.on_log_type_change(LOG_TYPES[0])
        # After all widgets are created, set up trace for log path
        self.vars["log"].trace_add("write", self.on_log_path_change)
        self.update_convert_button_state()

    def on_log_type_change(self, value):
        logger.info("Log type changed to: %s", value)
        # Enable/disable DBC entry and browse button based on log type
        dbc_entry = self.widget_refs['dbc_entry']
        dbc_browse_btn = self.widget_refs['dbc_browse_btn']
        if value == "CAN":
            dbc_entry.config(state="normal")
            dbc_browse_btn.config(state="normal")
        else:
            dbc_entry.config(state="disabled")
            dbc_browse_btn.config(state="disabled")
        self.vars["dbc"].set("")

    def on_log_path_change(self, *args):
        logger.debug("Log path changed: %s", self.vars["log"].get())
        log_path = self.vars["log"].get()
        if log_path:
            self.vars["output"].set(get_default_output(log_path))
        self.update_convert_button_state()

    def update_convert_button_state(self):
        logger.debug("Updating convert button state")
        log_path = self.vars["log"].get()
        if hasattr(self, 'convert_btn'):
            if log_path:
                self.convert_btn.config(state=tk.NORMAL)
            else:
                self.convert_btn.config(state=tk.DISABLED)

    def browse_log(self):
        logger.info("Browsing for log file")
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
            logger.info("Selected log file: %s", path)
            self.vars["log"].set(path)
            self.last_dir = os.path.dirname(path)
            save_last_dir(self.last_dir)

    def browse_dbc(self):
        logger.info("Browsing for DBC file")
        path = filedialog.askopenfilename(initialdir=self.last_dir, title="Select DBC File", filetypes=[("DBC Files", "*.dbc"), ("All Files", "*.*")])
        if path:
            logger.info("Selected DBC file: %s", path)
            self.vars["dbc"].set(path)
            self.last_dir = os.path.dirname(path)
            save_last_dir(self.last_dir)

    def browse_output(self):
        logger.info("Browsing for output file")
        path = filedialog.asksaveasfilename(initialdir=self.last_dir, title="Select Output File", defaultextension=".ld", filetypes=[("MoTeC LD Files", "*.ld"), ("All Files", "*.*")])
        if path:
            logger.info("Selected output file: %s", path)
            self.vars["output"].set(path)
            self.last_dir = os.path.dirname(path)
            save_last_dir(self.last_dir)

    def open_output_folder(self):
        output_path = self.vars["output"].get()
        logger.info("Opening output folder for: %s", output_path)
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
        logger.info("Starting conversion thread")
        def do_conversion():
            logger.info("Running conversion subprocess")
            args = [sys.executable, os.path.join(os.path.dirname(__file__), "motec_log_generator.py")]
            args += [self.vars["log"].get(), self.vars["log_type"].get()]
            if self.vars["output"].get():
                args += ["--output", self.vars["output"].get()]
            args += ["--frequency", str(self.vars["frequency"].get())]
            if self.vars["log_type"].get() == "CAN":
                if not self.vars["dbc"].get():
                    logger.error("DBC file is required for CAN logs.")
                    self.after(0, lambda: messagebox.showerror("Error", "DBC file is required for CAN logs."))
                    self.after(0, lambda: self.unlock_buttons())
                    return
                args += ["--dbc", self.vars["dbc"].get()]
            try:
                for _, varname, _, typ in METADATA_FIELDS:
                    val = self.vars[varname].get()
                    if typ == int:
                        try:
                            val = int(val)
                        except Exception:
                            logger.warning("Could not convert %s to int, defaulting to 0", varname)
                            val = 0
                    if val != "" and val != 0:
                        newarg = [f"--{varname}", str(val)]
                        logger.debug("Adding metadata argument: %s", newarg)
                        args += newarg
            except Exception as e:
                logger.error("Error processing metadata: %s", e)
            logger.info("Subprocess args: %s", args)
            try:
                result = subprocess.run(args, capture_output=True, text=True)
                logger.info("Subprocess finished with return code %s", result.returncode)
                if result.stdout:
                    logger.info("Subprocess stdout: %s", result.stdout)
                if result.stderr:
                    logger.warning("Subprocess stderr: %s", result.stderr)
                if result.returncode == 0:
                    self.after(0, lambda: self.status.config(text="Done! Output: " + self.vars["output"].get(), fg="green"))
                    self.after(0, lambda: messagebox.showinfo("Success", "Conversion complete!\nOutput: " + self.vars["output"].get()))
                    self.after(0, lambda: self.open_btn.config(state=tk.NORMAL))
                else:
                    self.after(0, lambda: self.status.config(text="Error: " + result.stderr, fg="red"))
                    self.after(0, lambda: messagebox.showerror("Error", result.stderr))
            except Exception as e:
                logger.error("Exception running subprocess: %s", e)
                self.after(0, lambda: self.status.config(text="Error: " + str(e), fg="red"))
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.unlock_buttons())

        self.status.config(text="Running conversion...")
        self.update()
        self.lock_buttons()
        threading.Thread(target=do_conversion, daemon=True).start()
        logger.info("Conversion thread started")

    def lock_buttons(self):
        logger.debug("Locking buttons")
        self.convert_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.widget_refs['dbc_browse_btn'].config(state=tk.DISABLED)

    def unlock_buttons(self):
        logger.debug("Unlocking buttons")
        self.convert_btn.config(state=tk.NORMAL)
        if self.vars["log_type"].get() == "CAN":
            self.widget_refs['dbc_browse_btn'].config(state=tk.NORMAL)
        else:
            self.widget_refs['dbc_browse_btn'].config(state=tk.DISABLED)

    def open_metadata_dialog(self):
        logger.info("Opening metadata dialog")
        meta_win = tk.Toplevel(self)
        meta_win.title("Edit Metadata")
        meta_win.resizable(False, False)
        meta_win.transient(self)
        meta_win.grab_set()
        meta_win.focus_set()
        meta_frame = tk.Frame(meta_win)
        meta_frame.pack(padx=20, pady=20, fill="both", expand=True)
        row = 0
        entries = {}
        for label, varname, default, _ in METADATA_FIELDS:
            l = tk.Label(meta_frame, text=label+":", font=self.base_font)
            l.grid(row=row, column=0, sticky="e", pady=6, padx=6)
            if varname not in self.vars:
                self.vars[varname] = tk.StringVar(value=str(default))
            e = tk.Entry(meta_frame, textvariable=self.vars[varname], width=50, font=self.entry_font)
            e.grid(row=row, column=1, sticky="ew", pady=6, padx=6)
            entries[varname] = e
            row += 1
        def close_meta():
            meta_win.destroy()
        close_btn = tk.Button(meta_frame, text="Close", command=close_meta, font=self.button_font)
        close_btn.grid(row=row, column=0, columnspan=2, pady=10)

if __name__ == "__main__":
    logger.info("Starting mainloop")
    MotecLogGUI().mainloop()
