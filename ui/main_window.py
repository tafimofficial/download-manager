import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import time
from plyer import notification
import pystray
from PIL import Image, ImageDraw
from flask import Flask, request
from flask_cors import CORS
import logging

# Add parent directory to path to import core
if not getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.downloader import Downloader

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

api = Flask(__name__)
CORS(api)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- ULTRA PREMIUM GLASS DARK PALETTE ---
COLOR_BG_DARK = "#0A0A0B"        # Deep void
COLOR_BG_CARD = "#161618"        # Glass Card
COLOR_ACCENT = "#3498DB"         # Electric Blue
COLOR_ACCENT_HOVER = "#2980B9"
COLOR_TEXT_MAIN = "#F5F5F7"      # Off-white
COLOR_TEXT_MUTE = "#8E8E93"      # Silver Gray
COLOR_SUCCESS = "#2ECC71"
COLOR_DANGER = "#E74C3C"
COLOR_BORDER = "#2C2C2E"         # Subtle divider

class ModernPopup(ctk.CTkToplevel):
    def __init__(self, parent, title, message, url=None, type="capture", callback=None):
        super().__init__(parent)
        self.url = url
        self.title("")
        self.geometry("420x220")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.focus_force()
        self.callback = callback
        
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"420x220+{sw-440}+{sh-260}")
        
        self.configure(fg_color=COLOR_BG_DARK)
        
        # Glass Frame
        self.outer = ctk.CTkFrame(self, fg_color=COLOR_ACCENT, corner_radius=16)
        self.outer.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.inner = ctk.CTkFrame(self.outer, fg_color=COLOR_BG_DARK, corner_radius=15)
        self.inner.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.head_lbl = ctk.CTkLabel(self.inner, text=f"⚡ {title}", font=("Segoe UI", 20, "bold"), text_color=COLOR_ACCENT)
        self.head_lbl.pack(pady=(25, 10))
        
        self.msg_lbl = ctk.CTkLabel(self.inner, text=message, font=("Segoe UI", 12), text_color=COLOR_TEXT_MAIN, wraplength=350)
        self.msg_lbl.pack(pady=5, padx=30)
        
        self.btn_frame = ctk.CTkFrame(self.inner, fg_color="transparent")
        self.btn_frame.pack(side="bottom", pady=(0, 25))
        
        
        # Override close button
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        if type == "capture":
            self.main_btn = ctk.CTkButton(self.btn_frame, text="Catch Link", width=140, height=40, corner_radius=20, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, font=("Segoe UI", 13, "bold"), command=lambda: self.accept(url))
            self.main_btn.pack(side="left", padx=10)
            self.cancel_btn = ctk.CTkButton(self.btn_frame, text="Dismiss", width=100, height=40, corner_radius=20, fg_color=COLOR_BORDER, text_color=COLOR_TEXT_MAIN, hover_color="#3A3A3C", command=self.destroy)
            self.cancel_btn.pack(side="left", padx=10)
        else:
            self.main_btn = ctk.CTkButton(self.btn_frame, text="Open Folder", width=140, height=40, corner_radius=20, fg_color=COLOR_SUCCESS, hover_color="#27AE60", font=("Segoe UI", 13, "bold"), command=self.open_dir)
            self.main_btn.pack(side="left", padx=10)
            self.cancel_btn = ctk.CTkButton(self.btn_frame, text="Done", width=100, height=40, corner_radius=20, fg_color=COLOR_BORDER, text_color=COLOR_TEXT_MAIN, hover_color="#3A3A3C", command=self.destroy)
            self.cancel_btn.pack(side="left", padx=10)

    def accept(self, url):
        if self.callback: self.callback(url)
        self.destroy()
        

        
    def open_dir(self):
        if self.callback: self.callback()
        self.destroy()

    def destroy(self):
        if self.url and hasattr(self.master, 'active_popups'):
            if self.url in self.master.active_popups:
                self.master.active_popups.remove(self.url)
        super().destroy()

class DownloadRow(ctk.CTkFrame):
    def __init__(self, master, app, url, save_path, remove_callback, unit_var):
        super().__init__(master, fg_color=COLOR_BG_CARD, height=75, corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        self.app = app
        self.url = url
        self.save_path = save_path
        self.remove_callback = remove_callback
        self.unit_var = unit_var
        self.downloader = Downloader(url, save_path, threads=app.thread_count.get())
        self.monitoring = True

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.create_widgets()
        self.start()

    def create_widgets(self):
        self.icon_lbl = ctk.CTkLabel(self, text="💎", font=("Segoe UI", 24))
        self.icon_lbl.grid(row=0, column=0, padx=(20, 15), pady=18)

        name = self.downloader.filename
        if len(name) > 40: name = name[:37] + "..."
        self.name_lbl = ctk.CTkLabel(self, text=name, font=("Segoe UI", 14, "bold"), text_color=COLOR_TEXT_MAIN, anchor="w")
        self.name_lbl.grid(row=0, column=1, padx=5, sticky="ew")

        self.p_bar = ctk.CTkProgressBar(self, height=10, progress_color=COLOR_ACCENT, fg_color="#1C1C1E", corner_radius=5)
        self.p_bar.grid(row=0, column=2, padx=25, sticky="ew")
        self.p_bar.set(0)

        self.stats_lbl = ctk.CTkLabel(self, text="Initializing...", font=("Consolas", 11), text_color=COLOR_TEXT_MUTE, width=130, anchor="e")
        self.stats_lbl.grid(row=0, column=3, padx=5)

        self.speed_lbl = ctk.CTkLabel(self, text="--", font=("Consolas", 11, "bold"), text_color=COLOR_SUCCESS, width=95, anchor="e")
        self.speed_lbl.grid(row=0, column=4, padx=5)

        self.btn_f = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_f.grid(row=0, column=5, padx=(10, 20))

        self.p_btn = ctk.CTkButton(self.btn_f, text="⏸", width=34, height=34, corner_radius=10, fg_color="#2C2C2E", text_color=COLOR_TEXT_MAIN, hover_color="#3A3A3C", command=self.toggle)
        self.p_btn.pack(side="left", padx=5)

        self.c_btn = ctk.CTkButton(self.btn_f, text="✕", width=34, height=34, corner_radius=10, fg_color="#3D1212", text_color=COLOR_DANGER, hover_color="#5D1A1A", command=self.cancel)
        self.c_btn.pack(side="left", padx=5)

    def start(self):
        threading.Thread(target=self.downloader.start, daemon=True).start()
        self.update()

    def toggle(self):
        if self.downloader.status == "downloading":
            self.downloader.pause()
            self.p_btn.configure(text="▶", text_color=COLOR_SUCCESS)
        else:
            threading.Thread(target=self.downloader.start, daemon=True).start()
            self.p_btn.configure(text="⏸", text_color=COLOR_TEXT_MAIN)
        self.app.refresh_list()

    def set_completed_ui(self):
        # Change Pause to Open Folder
        self.p_btn.configure(text="📁", command=lambda: os.startfile(os.path.dirname(self.downloader.save_path)))
        # Change Cancel to Remove
        self.c_btn.configure(text="🗑", fg_color="#2C2C2E", text_color=COLOR_TEXT_MUTE, hover_color="#3A3A3C", command=self.remove_from_list)
        # Update speed to show file size
        self.speed_lbl.configure(text=self.app.fmt_size(self.downloader.file_size))
        
    def remove_from_list(self):
        self.monitoring = False
        self.remove_callback(self)
        self.app.refresh_list()

    def cancel(self):
        if self.downloader.status not in ["completed", "error"]:
            if not messagebox.askyesno("Tafim DL", f"Stop and DELETE {self.downloader.filename}?"): return
        
        self.downloader.cancel()
        
        # Hard delete the file if it exists
        if os.path.exists(self.save_path):
            try: os.remove(self.save_path)
            except: pass
            
        self.monitoring = False
        self.remove_callback(self)
        self.app.refresh_list()

    def update(self):
        if not self.monitoring: return
        status = self.downloader.status
        self.p_bar.set(self.downloader.get_progress())
        
        cur = self.app.fmt_size(self.downloader.downloaded_size)
        tot = self.app.fmt_size(self.downloader.file_size)
        self.stats_lbl.configure(text=f"{cur} / {tot}")
        
        speed = self.app.fmt_speed(self.downloader.speed)
        self.speed_lbl.configure(text=speed)

        if status == "completed":
            self.monitoring = False
            self.p_bar.configure(progress_color=COLOR_SUCCESS)
            self.set_completed_ui()
            self.app.on_download_complete(self.downloader.filename, self.downloader.save_path)
            self.app.refresh_list()
        elif status == "error":
            self.monitoring = False
            self.p_bar.configure(progress_color=COLOR_DANGER)
            self.app.refresh_list()
            
        if self.monitoring: self.after(100, self.update)

class TafimApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Tafim Downloader Pro+ (Premium Edition)")
        self.geometry("1100x750")
        self.configure(fg_color=COLOR_BG_DARK)
        
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.downloads = []
        self.active_popups = set()
        self.processed_urls = set()

        self.unit = ctk.StringVar(value="Auto")
        self.notify_on_complete = ctk.BooleanVar(value=True)
        self.current_filter = "All"
        self.nav_btns = {}
        try:
            self.last_clip = self.clipboard_get().strip()
        except:
            self.last_clip = ""
        self.thread_count = ctk.IntVar(value=32)

        self.create_sidebar()
        self.create_main()
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.setup_tray()
        
        @api.route('/add')
        def add():
            u = request.args.get('url')
            if u: 
                # Check duplication here too
                if u not in self.downloads and u not in self.active_popups:
                    self.after(100, lambda: self.prompt_capture(u))
                return "OK"
            return "ERR"
        threading.Thread(target=lambda: api.run(port=5555, debug=False, use_reloader=False), daemon=True).start()

    def create_sidebar(self):
        self.side = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#0D0D0E", border_width=1, border_color=COLOR_BORDER)
        self.side.grid(row=0, column=0, sticky="nsew")
        self.side.grid_propagate(False)

        ctk.CTkLabel(self.side, text="💎 TAFIM", font=("Segoe UI Black", 30), text_color=COLOR_ACCENT).pack(pady=(45, 5))
        ctk.CTkLabel(self.side, text="PRO EDITION V1", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_MUTE).pack(pady=(0, 45))

        self.nav_btns["All"] = self.create_nav("All Tasks", "All", True)
        self.nav_btns["InPr"] = self.create_nav("Downloading", "InPr", False)
        self.nav_btns["File"] = self.create_nav("Completed", "File", False)

        self.sets = ctk.CTkFrame(self.side, fg_color="transparent")
        self.sets.pack(side="bottom", fill="x", padx=25, pady=35)
        
        ctk.CTkSwitch(self.sets, text="Smart Completion Popup", variable=self.notify_on_complete, font=("Segoe UI", 12), progress_color=COLOR_ACCENT).pack(anchor="w", pady=8)
        ctk.CTkLabel(self.sets, text="Premium License Active", text_color=COLOR_SUCCESS, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=5)

    def create_nav(self, text, filter_id, active):
        btn = ctk.CTkButton(self.side, text=f"  {text}", height=50, corner_radius=12, anchor="w", 
                            fg_color=COLOR_ACCENT if active else "transparent", 
                            text_color="white" if active else COLOR_TEXT_MUTE, 
                            hover_color="#1C1C1E" if not active else COLOR_ACCENT_HOVER, 
                            font=("Segoe UI", 13, "bold"),
                            command=lambda: self.set_filter(filter_id))
        btn.pack(pady=5, padx=18, fill="x")
        return btn

    def set_filter(self, fid):
        self.current_filter = fid
        for k, b in self.nav_btns.items():
            act = (k == fid)
            b.configure(fg_color=COLOR_ACCENT if act else "transparent", text_color="white" if act else COLOR_TEXT_MUTE)
        self.refresh_list()

    def refresh_list(self):
        for r in self.downloads: r.pack_forget()
        for r in self.downloads:
            stat = r.downloader.status
            show = False
            if self.current_filter == "All": show = True
            elif self.current_filter == "InPr" and stat in ["downloading", "paused", "pending"]: show = True
            elif self.current_filter == "File" and stat == "completed": show = True
            
            if show: r.pack(fill="x", padx=15, pady=10)

    def create_main(self):
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_BG_DARK)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(2, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self.bar = ctk.CTkFrame(self.main, fg_color="transparent")
        self.bar.grid(row=0, column=0, sticky="ew", padx=45, pady=(45, 25))
        
        self.url_ent = ctk.CTkEntry(self.bar, placeholder_text="Secure URL Download...", height=55, font=("Segoe UI", 14), corner_radius=28, border_width=1, border_color=COLOR_BORDER, fg_color="#161618", text_color="white")
        self.url_ent.pack(side="left", fill="x", expand=True, padx=(0, 22))
        
        self.add_btn = ctk.CTkButton(self.bar, text="DOWNLOAD", width=140, height=55, corner_radius=28, font=("Segoe UI", 14, "bold"), fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, command=self.add_man)
        self.add_btn.pack(side="left")

        self.opt = ctk.CTkFrame(self.main, fg_color="transparent")
        self.opt.grid(row=1, column=0, sticky="ew", padx=55, pady=(0, 25))
        
        self.path_ent = ctk.CTkEntry(self.opt, width=320, height=34, border_width=0, fg_color="#1C1C1E", corner_radius=10, font=("Segoe UI", 11), text_color=COLOR_TEXT_MUTE)
        self.path_ent.pack(side="left")
        self.path_ent.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        ctk.CTkButton(self.opt, text="📁", width=40, height=34, corner_radius=10, fg_color="#1C1C1E", text_color=COLOR_TEXT_MAIN, hover_color="#2C2C2E", command=self.pick_dir).pack(side="left", padx=8)

        self.u_menu = ctk.CTkOptionMenu(self.opt, values=["Auto", "KB/s", "MB/s"], variable=self.unit, width=100, height=34, corner_radius=10, fg_color="#1C1C1E", button_color="#2C2C2E", text_color=COLOR_TEXT_MAIN)
        self.u_menu.pack(side="right")

        # Thread Slider
        self.thread_lbl = ctk.CTkLabel(self.opt, text="Threads: 32", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_MUTE, width=80)
        self.thread_lbl.pack(side="right", padx=(10, 5))
        
        self.thread_slider = ctk.CTkSlider(self.opt, from_=1, to=128, number_of_steps=127, variable=self.thread_count, width=120, progress_color=COLOR_ACCENT, button_color=COLOR_ACCENT, command=self.update_thread_lbl)
        self.thread_slider.pack(side="right", padx=5)

        self.list = ctk.CTkScrollableFrame(self.main, fg_color="transparent")
        self.list.grid(row=2, column=0, sticky="nsew", padx=35, pady=(0, 35))

    def pick_dir(self):
        d = filedialog.askdirectory()
        if d: self.path_ent.delete(0, "end"); self.path_ent.insert(0, d)

    def update_thread_lbl(self, val):
        self.thread_lbl.configure(text=f"Threads: {int(val)}")

    def add_man(self):
        u = self.url_ent.get().strip()
        if u: self.start_dl(u); self.url_ent.delete(0, "end")

    def start_dl(self, url):
        self.deiconify(); self.lift(); self.focus_force()
        row = DownloadRow(self.list, self, url, self.path_ent.get().strip(), self.remove_dl, self.unit)
        self.downloads.append(row)
        self.refresh_list()

    def remove_dl(self, row):
        row.pack_forget()
        if row in self.downloads: self.downloads.remove(row)
        row.destroy()

    def prompt_capture(self, url):
        # Deduplication
        if url in self.active_popups: return
        if any(d.url == url for d in self.downloads): return 
        
        self.active_popups.add(url)
        ModernPopup(self, "Tafim Catch", "A new file stream was detected. Download with Tafim Pro?", url, "capture", self.accept_capture)

    def accept_capture(self, url):
        if url in self.active_popups: self.active_popups.remove(url)
        self.start_dl(url)
        
    def on_download_complete(self, name, path):
        if self.notify_on_complete.get():
            ModernPopup(self, "Download Finished", f"Successfully saved:\n{name}", callback=lambda: os.startfile(os.path.dirname(path)), type="done")

    def check_clip(self):
        try:
            c = self.clipboard_get().strip()
            if c and c != self.last_clip and c.startswith("http"):
                self.last_clip = c
                
                # Check extension
                try:
                    from urllib.parse import urlparse
                    parsed_path = urlparse(c).path
                    base, ext_w_dot = os.path.splitext(parsed_path)
                    if ext_w_dot:
                        ext = ext_w_dot.lstrip('.').upper()
                        
                        allowed_exact = {
                            '3GP', '7Z', 'AAC', 'ACE', 'AIF', 'APK', 'ARJ', 'ASF', 'AVI', 'BIN', 'BZ2', 'EXE', 'GZ', 'GZIP', 'IMG', 'ISO', 'LZH', 
                            'M4A', 'M4V', 'MKV', 'MOV', 'MP3', 'MP4', 'MPA', 'MPE', 'MPEG', 'MPG', 'MSI', 'MSU', 'OGG', 'OGV', 'PDF', 'PLJ', 
                            'PPS', 'PPT', 'QT', 'RA', 'RAR', 'RM', 'RMVB', 'SEA', 'SIT', 'SITX', 'TAR', 'TIF', 'TIFF', 'WAV', 'WMA', 'WMV', 'Z', 'ZIP'
                        }
                        
                        is_match = ext in allowed_exact
                        
                        # Wildcards R0* and R1*
                        if not is_match:
                            import re
                            if re.match(r'^R0\d+$', ext) or re.match(r'^R1\d+$', ext):
                                is_match = True
                                
                        if is_match:
                            self.after(500, lambda: self.prompt_capture(c))
                except Exception as e:
                    print(f"Check clip error: {e}")
                    pass
        except: pass
        self.after(2000, self.check_clip)

    def hide(self): self.withdraw()
    
    def setup_tray(self):
        menu = pystray.Menu(pystray.MenuItem("Restore Tafim", self.deiconify), pystray.MenuItem("Exit Pro", self.full_quit))
        img = Image.new('RGB', (64, 64), (52, 152, 219))
        draw = ImageDraw.Draw(img)
        draw.polygon([(32,5), (45,30), (35,30), (45,60), (20,30), (30,30)], fill=(255, 255, 255))
        self.tray = pystray.Icon("TafimPro", img, "Tafim Downloader Pro", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def full_quit(self):
        self.tray.stop(); self.quit(); sys.exit(0)

    def fmt_size(self, s):
        if s < 1024: return f"{s} B"
        if s < 1024**2: return f"{s/1024:.1f} KB"
        return f"{s/1024**2:.1f} MB"

    def fmt_speed(self, s):
        u = self.unit.get()
        if u == "Auto": return self.fmt_size(s) + "/s"
        return f"{s/1024:.2f} KB/s" if u == "KB/s" else f"{s/1024**2:.2f} MB/s"

    def run(self):
        self.after(1000, self.check_clip)
        self.mainloop()

if __name__ == "__main__":
    app = TafimApp()
    app.run()
