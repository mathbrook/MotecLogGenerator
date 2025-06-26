import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import sys
import subprocess
import threading
import requests

LAST_DIR_FILE = os.path.join(os.path.expanduser("~"), ".motec_log_gui_lastdir.json")
ICON_DL_PATH = os.path.join(os.path.dirname(__file__), "icons", "squirrel.png")
LOG_TYPES = ["MCAP", "CSV", "ACCESSPORT", "CAN"]

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
        try:
            os.makedirs(os.path.dirname(ICON_DL_PATH), exist_ok=True)
            icon = tk.PhotoImage(file=ICON_DL_PATH)
            self.iconphoto(True, icon)
        except Exception as e:
            print(f"Error loading icon: {e}")
            # Try to download the icon from github lmao
            try:
                response = requests.get("https://raw.githubusercontent.com/mathbrook/MotecLogGenerator/refs/heads/master/icons/squirrel.png", timeout=3)
                if response.status_code == 200:
                    with open(ICON_DL_PATH, "wb") as f:
                        f.write(response.content)
                    icon = tk.PhotoImage(file=ICON_DL_PATH)
                    self.iconphoto(True, icon)
                else:
                    print("Failed to download icon, using default.")
            except Exception as e:
                print(f"Error downloading icon: {e}, using default.")
        self.title("MoTeC Log Generator GUI")
        self.configure(bg="#23272e")  # dark background
        self.resizable(False, True)
        self.last_dir = load_last_dir()
        self.vars = {}
        self.base_font = ("PMingLiU-ExtB", 14)
        self.entry_font = ("PMingLiU-ExtB", 14)
        self.button_font = ("PMingLiU-ExtB", 14, "bold")
        self.fg_color = "#f5f6fa"
        self.accent_color = "#23408e"  # dark blue
        self.pad = 20
        self.create_widgets()
        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())
        self.geometry("")

    def create_widgets(self):
        container = tk.Frame(self, bg="#23272e")
        container.pack(padx=self.pad, pady=self.pad, fill="both", expand=True)
        row = 0
        self.widget_refs = {}
        def add_label(text, width=None):
            return tk.Label(container, text=text, font=self.base_font, fg=self.fg_color, bg="#23272e", width=width)
        def add_entry(var, width=50):
            entry = tk.Entry(container, textvariable=var, width=width, font=self.entry_font, bg="#353a45", fg=self.fg_color, insertbackground=self.fg_color, relief=tk.FLAT, highlightthickness=1, highlightbackground="#444")
            return entry
        def add_button(text, cmd):
            return tk.Button(container, text=text, command=cmd, font=self.button_font, bg=self.accent_color, fg="white", activebackground="#16244a", activeforeground="white", relief=tk.FLAT, bd=0, padx=10, pady=4)
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
                label = tk.Label(tooltip, text=text, bg="#444", fg="#fff", font=("PMingLiU-ExtB", 12), relief=tk.SOLID, borderwidth=1, padx=6, pady=2)
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
        log_type_menu.config(font=self.base_font, bg="#2c313a", fg=self.fg_color, activebackground="#353a45", activeforeground=self.fg_color, highlightthickness=0, relief=tk.FLAT)
        log_type_menu['menu'].config(font=self.base_font, bg="#2c313a", fg=self.fg_color, activebackground="#353a45", activeforeground=self.fg_color)
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
        # Set initial DBC entry color
        dbc_entry.config(bg="#23272e", disabledbackground="#23272e", disabledforeground="#888")
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
        freq_entry = tk.Entry(container, textvariable=self.vars["frequency"], width=10, font=self.entry_font, bg="#2c313a", fg=self.fg_color, insertbackground=self.fg_color, relief=tk.FLAT, highlightthickness=1, highlightbackground="#444")
        freq_entry.grid(row=row, column=1, sticky="ew", pady=6, padx=6, columnspan=2)
        add_tooltip(freq_entry, "Sample frequency for output log.")
        row += 1

        self.status = tk.Label(container, text="", fg="#7ecfff", bg="#23272e", font=("PMingLiU-ExtB", 12, "italic"))
        self.status.grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        row += 1

        button_frame = tk.Frame(container, bg="#23272e")
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        self.convert_btn = tk.Button(button_frame, text="Convert", command=self.run_conversion, font=self.button_font, bg=self.accent_color, fg="white", activebackground="#16244a", activeforeground="white", relief=tk.FLAT, bd=0, padx=16, pady=8)
        self.convert_btn.pack(side=tk.LEFT, padx=10)
        self.open_btn = tk.Button(button_frame, text="Open", command=self.open_output_folder, state=tk.DISABLED, font=self.button_font, bg="#23408e", fg="#fff", activebackground="#16244a", activeforeground="#fff", relief=tk.FLAT, bd=0, padx=16, pady=8)
        self.open_btn.pack(side=tk.LEFT, padx=10)
        metadata_btn = tk.Button(button_frame, text="Metadata...", command=self.open_metadata_dialog, font=self.button_font, bg=self.accent_color, fg="white", activebackground="#16244a", activeforeground="white", relief=tk.FLAT, bd=0, padx=16, pady=8)
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
        # Enable/disable DBC entry and browse button based on log type
        dbc_entry = self.widget_refs['dbc_entry']
        dbc_browse_btn = self.widget_refs['dbc_browse_btn']
        if value == "CAN":
            dbc_entry.config(state="normal", bg="#353a45", disabledbackground="#23272e", disabledforeground="#888")
            dbc_browse_btn.config(state="normal")
        else:
            dbc_entry.config(state="disabled", bg="#23272e", disabledbackground="#23272e", disabledforeground="#888")
            dbc_browse_btn.config(state="disabled")
        self.vars["dbc"].set("")

    def on_log_path_change(self, *args):
        log_path = self.vars["log"].get()
        if log_path:
            self.vars["output"].set(get_default_output(log_path))
        self.update_convert_button_state()

    def update_convert_button_state(self):
        log_path = self.vars["log"].get()
        if hasattr(self, 'convert_btn'):
            if log_path:
                self.convert_btn.config(state=tk.NORMAL)
            else:
                self.convert_btn.config(state=tk.DISABLED)

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
        def do_conversion():
            args = [sys.executable, os.path.join(os.path.dirname(__file__), "motec_log_generator.py")]
            args += [self.vars["log"].get(), self.vars["log_type"].get()]
            if self.vars["output"].get():
                args += ["--output", self.vars["output"].get()]
            args += ["--frequency", str(self.vars["frequency"].get())]
            if self.vars["log_type"].get() == "CAN":
                if not self.vars["dbc"].get():
                    self.after(0, lambda: messagebox.showerror("Error", "DBC file is required for CAN logs."))
                    self.after(0, lambda: self.unlock_buttons())
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
            try:
                result = subprocess.run(args, capture_output=True, text=True)
                if result.returncode == 0:
                    self.after(0, lambda: self.status.config(text="Done! Output: " + self.vars["output"].get(), fg="green"))
                    self.after(0, lambda: messagebox.showinfo("Success", "Conversion complete!\nOutput: " + self.vars["output"].get()))
                    self.after(0, lambda: self.open_btn.config(state=tk.NORMAL))
                else:
                    self.after(0, lambda: self.status.config(text="Error: " + result.stderr, fg="red"))
                    self.after(0, lambda: messagebox.showerror("Error", result.stderr))
            except Exception as e:
                self.after(0, lambda: self.status.config(text="Error: " + str(e), fg="red"))
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.unlock_buttons())

        self.status.config(text="Running conversion...")
        self.update()
        self.lock_buttons()
        threading.Thread(target=do_conversion, daemon=True).start()

    def lock_buttons(self):
        self.convert_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.widget_refs['dbc_browse_btn'].config(state=tk.DISABLED)

    def unlock_buttons(self):
        self.convert_btn.config(state=tk.NORMAL)
        if self.vars["log_type"].get() == "CAN":
            self.widget_refs['dbc_browse_btn'].config(state=tk.NORMAL)
        else:
            self.widget_refs['dbc_browse_btn'].config(state=tk.DISABLED)

    def open_metadata_dialog(self):
        meta_win = tk.Toplevel(self)
        meta_win.title("Edit Metadata")
        meta_win.configure(bg="#23272e")
        meta_win.resizable(False, False)
        meta_win.transient(self)
        meta_win.grab_set()
        meta_win.focus_set()
        meta_frame = tk.Frame(meta_win, bg="#23272e")
        meta_frame.pack(padx=20, pady=20, fill="both", expand=True)
        row = 0
        entries = {}
        for label, varname, default, _ in METADATA_FIELDS:
            l = tk.Label(meta_frame, text=label+":", font=self.base_font, fg=self.fg_color, bg="#23272e")
            l.grid(row=row, column=0, sticky="e", pady=6, padx=6)
            if varname not in self.vars:
                self.vars[varname] = tk.StringVar(value=str(default))
            e = tk.Entry(meta_frame, textvariable=self.vars[varname], width=50, font=self.entry_font, bg="#353a45", fg=self.fg_color, insertbackground=self.fg_color, relief=tk.FLAT, highlightthickness=1, highlightbackground="#444")
            e.grid(row=row, column=1, sticky="ew", pady=6, padx=6)
            entries[varname] = e
            row += 1
        def close_meta():
            meta_win.destroy()
        close_btn = tk.Button(meta_frame, text="Close", command=close_meta, font=self.button_font, bg=self.accent_color, fg="white", activebackground="#16244a", activeforeground="white", relief=tk.FLAT, bd=0, padx=16, pady=8)
        close_btn.grid(row=row, column=0, columnspan=2, pady=10)

if __name__ == "__main__":
    MotecLogGUI().mainloop()
