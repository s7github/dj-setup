import json
import os
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


REPO_ROOT = Path(__file__).resolve().parents[1]
SPOTIFY_ROOT = REPO_ROOT / "providers" / "spotify"
LINKS_FILE = SPOTIFY_ROOT / "download-links.txt"
SETTINGS_DIR_NAME = "DJ Setup"
ACCENT = "#43d17a"
BACKGROUND = "#101820"
SIDEBAR = "#0b1219"
CARD = "#192630"
CARD_HOVER = "#22333f"
FOREGROUND = "#edf4f7"
MUTED = "#9aabb6"
SPOTIFY_DOWNLOADER_URL = "https://github.com/WilliamSchack/Spotify-Downloader"


def default_settings() -> dict[str, str]:
    return {
        "download_root": str(Path.home() / "Music" / "DJ Incoming" / "Spotify"),
        "links_file": str(LINKS_FILE),
        "spotify_downloader_exe": "",
    }


def settings_path() -> Path:
    app_data = os.environ.get("APPDATA")
    if not app_data:
        raise RuntimeError("APPDATA is not set; DJ Setup requires a Windows user profile.")
    return Path(app_data) / SETTINGS_DIR_NAME / "settings.json"


def load_settings() -> dict[str, str]:
    path = settings_path()
    settings = default_settings()
    try:
        saved_settings = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return settings
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read DJ Setup settings at {path}: {error}") from error
    if not isinstance(saved_settings, dict):
        raise RuntimeError(f"DJ Setup settings must contain a JSON object: {path}")
    for key in settings:
        value = saved_settings.get(key, settings[key])
        if not isinstance(value, str):
            raise RuntimeError(f"DJ Setup setting {key!r} must be text: {path}")
        settings[key] = value
    return settings


def save_settings(settings: dict[str, str]) -> Path:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as error:
        raise RuntimeError(f"Could not save DJ Setup settings at {path}: {error}") from error
    return path


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


class DJSetupApp:
    def __init__(self, root: tk.Tk, settings: dict[str, str]) -> None:
        self.root = root
        self.settings = settings
        self.events: queue.Queue[tuple] = queue.Queue()
        self.busy = False
        self.root.title("DJ Setup")
        self.root.geometry("1180x820")
        self.root.minsize(980, 680)
        self.root.configure(bg=BACKGROUND)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_workspace()
        self.show_page("Home")
        self.root.after(100, self._poll_events)

    def _build_sidebar(self) -> None:
        sidebar = tk.Frame(self.root, bg=SIDEBAR, width=205, padx=18, pady=25)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        tk.Label(
            sidebar, text="DJ SETUP", bg=SIDEBAR, fg=ACCENT,
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            sidebar, text="Music workflow hub", bg=SIDEBAR, fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 32))
        for page in ("Home", "Downloads", "Library", "Tools", "Settings"):
            tk.Button(
                sidebar,
                text=page,
                command=lambda selected=page: self.show_page(selected),
                anchor="w",
                relief="flat",
                bd=0,
                padx=13,
                pady=11,
                bg=SIDEBAR,
                fg=FOREGROUND,
                activebackground=CARD_HOVER,
                activeforeground=ACCENT,
                font=("Segoe UI", 11),
                cursor="hand2",
            ).pack(fill="x", pady=2)
        tk.Label(
            sidebar, text="WINDOWS  |  LOCAL SETTINGS", bg=SIDEBAR, fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(side="bottom", anchor="w")

    def _build_workspace(self) -> None:
        workspace = tk.Frame(self.root, bg=BACKGROUND, padx=28, pady=22)
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(1, weight=1)

        header = tk.Frame(workspace, bg=BACKGROUND)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header.grid_columnconfigure(0, weight=1)
        self.title_label = tk.Label(
            header, text="", bg=BACKGROUND, fg=FOREGROUND,
            font=("Segoe UI", 22, "bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = tk.Label(
            header, text="", bg=BACKGROUND, fg=MUTED,
            font=("Segoe UI", 10),
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.canvas = tk.Canvas(
            workspace, bg=BACKGROUND, bd=0, highlightthickness=0,
        )
        scrollbar = tk.Scrollbar(workspace, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.page_frame = tk.Frame(self.canvas, bg=BACKGROUND)
        self.page_window = self.canvas.create_window(
            (0, 0), window=self.page_frame, anchor="nw",
        )
        self.page_frame.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_page)
        self.canvas.bind("<Enter>", lambda _event: self.canvas.bind_all(
            "<MouseWheel>", self._scroll_page,
        ))
        self.canvas.bind("<Leave>", lambda _event: self.canvas.unbind_all("<MouseWheel>"))

        footer = tk.Frame(workspace, bg=BACKGROUND)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.status_label = tk.Label(
            footer, text="Ready", bg=BACKGROUND, fg=ACCENT,
            font=("Segoe UI", 9),
        )
        self.status_label.pack(anchor="w")
        self.log_text = tk.Text(
            footer, height=4, bg="#0b1219", fg=MUTED, relief="flat",
            font=("Consolas", 9), state="disabled", wrap="word",
        )
        self.log_text.pack(fill="x", pady=(7, 0))

    def _update_scroll_region(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_page(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.page_window, width=event.width)

    def _scroll_page(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def show_page(self, page: str) -> None:
        self.title_label.configure(text=page)
        subtitles = {
            "Home": "Your music tools and DJ workflows, together in one place.",
            "Downloads": "Choose a source, downloader, and destination.",
            "Library": "Organize and maintain your local music collection.",
            "Tools": "Playlist, tag, and library utilities.",
            "Settings": "Change folders and connect the tools you use.",
        }
        self.subtitle_label.configure(text=subtitles[page])
        for child in self.page_frame.winfo_children():
            child.destroy()
        if page == "Settings":
            self._render_settings()
        elif page == "Library":
            self._render_placeholders(
                "Library management",
                ("Move downloads into your library", "Reorder tracks", "Fix MP3 tags"),
            )
        elif page == "Tools":
            self._render_placeholders(
                "DJ tools",
                ("DJ playlists", "Library analytics", "YouTube downloads"),
            )
        else:
            self._render_downloads(home=page == "Home")
        self.canvas.yview_moveto(0)

    def _section(self, parent: tk.Widget, title: str, description: str = "") -> tk.Frame:
        section = tk.Frame(parent, bg=BACKGROUND)
        section.pack(fill="x", pady=(4, 14))
        tk.Label(
            section, text=title.upper(), bg=BACKGROUND, fg=ACCENT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        if description:
            tk.Label(
                section, text=description, bg=BACKGROUND, fg=MUTED,
                font=("Segoe UI", 9), wraplength=820, justify="left",
            ).pack(anchor="w", pady=(3, 8))
        return section

    def _tile(
        self,
        parent: tk.Widget,
        title: str,
        description: str,
        action_text: str,
        action,
        *,
        enabled: bool = True,
    ) -> tk.Frame:
        tile = tk.Frame(parent, bg=CARD, padx=15, pady=13)
        tk.Label(
            tile, text=title, bg=CARD, fg=FOREGROUND,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        tk.Label(
            tile, text=description, bg=CARD, fg=MUTED,
            font=("Segoe UI", 9), justify="left", wraplength=300,
            height=2, anchor="nw",
        ).pack(fill="x", pady=(5, 9))
        button = tk.Button(
            tile,
            text=action_text,
            command=action,
            state="normal" if enabled else "disabled",
            relief="flat",
            bd=0,
            padx=11,
            pady=6,
            bg=ACCENT if enabled else CARD_HOVER,
            fg="#08120c" if enabled else MUTED,
            activebackground="#68e590",
            activeforeground="#08120c",
            disabledforeground=MUTED,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2" if enabled else "arrow",
        )
        button.pack(anchor="w")
        return tile

    def _tile_grid(self, section: tk.Frame, entries: list[tuple]) -> None:
        grid = tk.Frame(section, bg=BACKGROUND)
        grid.pack(fill="x")
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1, uniform="tiles")
        for index, entry in enumerate(entries):
            tile_arguments = entry[:4]
            enabled = entry[4] if len(entry) > 4 else True
            tile = self._tile(grid, *tile_arguments, enabled=enabled)
            tile.grid(
                row=index // 2, column=index % 2, sticky="nsew",
                padx=(0, 8) if index % 2 == 0 else (8, 0),
                pady=5,
            )

    def _render_downloads(self, *, home: bool) -> None:
        if home:
            root = tk.Frame(self.page_frame, bg=CARD, padx=16, pady=12)
            root.pack(fill="x", pady=(0, 14))
            tk.Label(
                root, text="DOWNLOAD DESTINATION", bg=CARD, fg=MUTED,
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w")
            destination = tk.Frame(root, bg=CARD)
            destination.pack(fill="x", pady=(5, 0))
            self.destination_label = tk.Label(
                destination, text=self.settings["download_root"], bg=CARD,
                fg=FOREGROUND, font=("Segoe UI", 10), anchor="w",
            )
            self.destination_label.pack(side="left", fill="x", expand=True)
            tk.Button(
                destination, text="Change", command=lambda: self.show_page("Settings"),
                relief="flat", bg=CARD_HOVER, fg=FOREGROUND, padx=10, pady=5,
                cursor="hand2",
            ).pack(side="right")

        sources = self._section(self.page_frame, "Music sources")
        self._tile_grid(sources, [
            ("Spotify", "Open Spotify in your default browser.", "Open Spotify", self.open_spotify),
            ("Spotify Web Player", "Browse your Spotify library and playlists.", "Open web player", lambda: self.open_url("https://open.spotify.com/")),
            ("YouTube", "Open YouTube. A download provider can be added later.", "Open YouTube", lambda: self.open_url("https://www.youtube.com/")),
        ])

        downloads = self._section(
            self.page_frame, "Spotify downloaders",
            "Compare available tools. The selected download folder is managed in Settings.",
        )
        self._tile_grid(downloads, [
            ("Zotify", "Command-line downloader with a guided setup and resumable URL list.", "Set up / repair", self.start_zotify_setup),
            ("Download links", "Edit the local list of Spotify tracks, albums, or playlists.", "Open song list", self.open_links_file),
            ("Download with Zotify", "Process pending URLs and keep successful progress marked.", "Start download", self.start_zotify_download),
            ("Spotify Downloader", "Optional separate Windows GUI app; select its executable in Settings.", "Open app / releases", self.open_external_downloader),
            ("More about the project", "Review the upstream project, its release notes, and current status.", "Visit project", lambda: self.open_url(SPOTIFY_DOWNLOADER_URL)),
        ])

        if home:
            future = self._section(
                self.page_frame, "Library & DJ workflows",
                "These sections are planned for future releases; they are not active features yet.",
            )
            self._tile_grid(future, [
                ("Move to library", "Plan and organize incoming tracks.", "Coming soon", None, False),
                ("DJ playlists", "Manage playlist files for your DJ software.", "Coming soon", None, False),
                ("MP3 tag fixing", "Review and correct track metadata.", "Coming soon", None, False),
                ("Library analytics", "Explore your music collection.", "Coming soon", None, False),
            ])

    def _render_placeholders(self, title: str, items: tuple[str, ...]) -> None:
        section = self._section(
            self.page_frame, title,
            "This area is part of the DJ Setup roadmap. These actions are not implemented yet.",
        )
        self._tile_grid(section, [
            (item, "Planned workflow; no files will be changed.", "Coming soon", None, False)
            for item in items
        ])

    def _render_settings(self) -> None:
        panel = tk.Frame(self.page_frame, bg=CARD, padx=18, pady=16)
        panel.pack(fill="x", pady=(4, 14))
        tk.Label(
            panel, text="Folders and applications", bg=CARD, fg=FOREGROUND,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", pady=(0, 14))

        self.root_var = tk.StringVar(value=self.settings["download_root"])
        self.links_var = tk.StringVar(value=self.settings["links_file"])
        self.downloader_var = tk.StringVar(value=self.settings["spotify_downloader_exe"])
        self._path_row(panel, "Downloaded music folder", self.root_var, self.choose_download_folder)
        self._path_row(panel, "Spotify URL list", self.links_var, self.choose_links_file)
        self._path_row(
            panel, "Spotify Downloader app (optional)",
            self.downloader_var, self.choose_spotify_downloader,
        )
        tk.Label(
            panel,
            text="Credentials and paths are stored locally in your Windows user profile.",
            bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=650, justify="left",
        ).pack(anchor="w", pady=(12, 10))
        tk.Button(
            panel, text="Save settings", command=self.save_user_settings,
            relief="flat", bg=ACCENT, fg="#08120c", padx=13, pady=7,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        ).pack(anchor="w")

        app_section = self._section(self.page_frame, "Optional external downloader")
        self._tile_grid(app_section, [
            (
                "Spotify Downloader",
                "Set the installed Spotify Downloader.exe above to launch it here. "
                "It is a separate third-party app; review its project and release first.",
                "Open app / releases",
                self.open_external_downloader,
            ),
        ])

    def _path_row(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        browse,
    ) -> None:
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=5)
        tk.Label(
            row, text=label, bg=CARD, fg=MUTED, width=32, anchor="w",
            font=("Segoe UI", 9),
        ).pack(side="left")
        tk.Entry(
            row, textvariable=variable, bg="#0b1219", fg=FOREGROUND,
            insertbackground=FOREGROUND, relief="flat", font=("Segoe UI", 9),
        ).pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        tk.Button(
            row, text="Browse", command=browse, relief="flat",
            bg=CARD_HOVER, fg=FOREGROUND, padx=10, pady=5, cursor="hand2",
        ).pack(side="right")

    def choose_download_folder(self) -> None:
        folder = filedialog.askdirectory(
            title="Choose downloaded music folder",
            initialdir=self.root_var.get() or str(Path.home()),
        )
        if folder:
            self.root_var.set(folder)

    def choose_links_file(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="Choose Spotify URL list",
            initialdir=str(Path(self.links_var.get()).parent),
            initialfile=Path(self.links_var.get()).name,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if filename:
            self.links_var.set(filename)

    def choose_spotify_downloader(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select Spotify Downloader.exe",
            filetypes=[("Windows applications", "*.exe"), ("All files", "*.*")],
        )
        if filename:
            self.downloader_var.set(filename)

    def save_user_settings(self) -> None:
        if self.busy:
            self.status_label.configure(text="Wait for the active task to finish before changing settings.")
            return
        download_root = expand_path(self.root_var.get().strip())
        links_file = expand_path(self.links_var.get().strip())
        downloader = self.downloader_var.get().strip()
        if (
            not self.root_var.get().strip()
            or not self.links_var.get().strip()
            or not download_root.is_absolute()
            or not links_file.is_absolute()
        ):
            messagebox.showerror("Invalid folder", "Choose absolute paths for the download folder and URL list.")
            return
        self.settings.update({
            "download_root": str(download_root),
            "links_file": str(links_file),
            "spotify_downloader_exe": str(expand_path(downloader)) if downloader else "",
        })
        try:
            save_settings(self.settings)
        except RuntimeError as error:
            messagebox.showerror("Could not save settings", str(error))
            return
        self.status_label.configure(text="Settings saved. Applying the download folder to Zotify...")
        self._start_process(
            [
                sys.executable,
                str(SPOTIFY_ROOT / "setup.py"),
                "--root-path",
                str(download_root),
            ],
            "Apply Zotify settings",
        )

    def open_spotify(self) -> None:
        try:
            os.startfile("spotify:")
        except (AttributeError, OSError):
            self.open_url("https://open.spotify.com/")

    def open_url(self, url: str) -> None:
        if not webbrowser.open(url):
            messagebox.showerror("Could not open link", f"Open this address in your browser:\n{url}")

    def open_links_file(self) -> None:
        path = expand_path(self.settings["links_file"])
        if not path.exists():
            example = SPOTIFY_ROOT / "download-links.txt.example"
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            except OSError as error:
                messagebox.showerror("Could not create URL list", str(error))
                return
        try:
            os.startfile(str(path))
        except (AttributeError, OSError) as error:
            messagebox.showerror("Could not open URL list", str(error))

    def start_zotify_setup(self) -> None:
        self._start_process(
            [
                sys.executable,
                str(SPOTIFY_ROOT / "install.py"),
                "--root-path",
                self.settings["download_root"],
            ],
            "Install or update Zotify",
        )

    def start_zotify_download(self) -> None:
        path = expand_path(self.settings["links_file"])
        if not path.is_file():
            self.open_links_file()
            self.status_label.configure(text="Add Spotify URLs to the list, then start the download again.")
            return
        self._start_process(
            [sys.executable, str(SPOTIFY_ROOT / "download.py"), str(path)],
            "Download Spotify links",
        )

    def open_external_downloader(self) -> None:
        executable = self.settings["spotify_downloader_exe"]
        if not executable:
            self.open_url(SPOTIFY_DOWNLOADER_URL + "/releases")
            return
        path = expand_path(executable)
        if not path.is_file():
            messagebox.showerror(
                "Application not found",
                f"Spotify Downloader was not found here:\n{path}\n\n"
                "Update its path in Settings or open the project releases.",
            )
            return
        try:
            os.startfile(str(path))
        except (AttributeError, OSError) as error:
            messagebox.showerror("Could not start application", str(error))

    def _start_process(self, command: list[str], description: str) -> None:
        if self.busy:
            self.status_label.configure(text="Another task is still running.")
            return
        self.busy = True
        self.status_label.configure(text=f"{description}...")
        self._append_log(f">>> {description}")
        threading.Thread(
            target=self._run_process,
            args=(command, description),
            daemon=True,
        ).start()

    def _run_process(self, command: list[str], description: str) -> None:
        try:
            process = subprocess.Popen(
                command,
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            if process.stdout is None:
                raise RuntimeError("Could not capture task output.")
            for line in process.stdout:
                self.events.put(("output", line.rstrip()))
            exit_code = process.wait()
            self.events.put(("complete", description, exit_code, ""))
        except (OSError, RuntimeError) as error:
            self.events.put(("complete", description, 1, str(error)))

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event[0] == "output":
                self._append_log(event[1])
            else:
                _, description, exit_code, error = event
                self.busy = False
                if exit_code == 0:
                    self.status_label.configure(text=f"{description} completed.")
                else:
                    self.status_label.configure(text=f"{description} failed (exit code {exit_code}).")
                    self._append_log(error or f"Exit code: {exit_code}")
        self.root.after(100, self._poll_events)


def main() -> int:
    root = tk.Tk()
    try:
        settings = load_settings()
    except RuntimeError as error:
        messagebox.showerror("DJ Setup settings error", str(error), parent=root)
        root.destroy()
        return 1
    DJSetupApp(root, settings)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
