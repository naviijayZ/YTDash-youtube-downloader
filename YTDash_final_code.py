import os
import time
import yt_dlp
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
from queue import Queue
from PIL import Image, ImageTk
import webbrowser
import base64
with open("CodeZence-removebg-preview.png", "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')


class YTDash:
    def __init__(self, root):
        self.root = root
        self.root.title("YTDash YouTube Downloader")
        self.root.geometry("900x450")
        self.root.resizable(False, False)

        # Variables
        self.url = tk.StringVar()
        self.folder = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.quality = tk.StringVar(value="720p")
        self.speed_limit = tk.StringVar(value="0")
        self.start_time = None

        # Download control
        self.download_queue = Queue()
        self.queue_list = []
        self.current_download = None
        self.current_quality = None
        self.downloading = False
        self.cancel_requested = False
        self.paused = False
        self.pause_event = threading.Event()
        self.ydl = None
        self.current_filename = None

        # Progress tracking
        self.download_speed = tk.StringVar(value="0 KB/s")
        self.eta = tk.StringVar(value="--:--")
        self.time_taken = tk.StringVar(value="00:00:00")
        self.file_size = tk.StringVar(value="0 B")

        # Setup GUI
        self.setup_gui()
        self.root.after(100, self.check_queue)

    def setup_gui(self):
        tab_control = ttk.Notebook(self.root)

        # Download Tab
        self.download_tab = ttk.Frame(tab_control)
        tab_control.add(self.download_tab, text='Download')

        # URL Entry
        url_frame = ttk.Frame(self.download_tab)
        url_frame.pack(fill='x', pady=(10, 5))
        ttk.Label(url_frame, text="YouTube URL:").pack(side='left')
        ttk.Entry(url_frame, textvariable=self.url, width=60).pack(side='left', padx=5, expand=True, fill='x')

        # Quality and Folder
        control_frame = ttk.Frame(self.download_tab)
        control_frame.pack(fill='x', pady=5)

        ttk.Label(control_frame, text="Quality:").pack(side='left')
        qualities = ["144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p (4K)", "MP3"]
        ttk.Combobox(control_frame, textvariable=self.quality, values=qualities, width=10, state="readonly").pack(
            side='left', padx=5)

        ttk.Label(control_frame, text="Save to:").pack(side='left', padx=(10, 0))
        ttk.Entry(control_frame, textvariable=self.folder, width=40).pack(side='left', expand=True, fill='x')
        ttk.Button(control_frame, text="Browse", command=self.browse_folder, width=8).pack(side='left', padx=5)

        # Speed Limit
        speed_frame = ttk.Frame(self.download_tab)
        speed_frame.pack(fill='x', pady=5)
        ttk.Label(speed_frame, text="Speed Limit (KB/s):").pack(side='left')
        ttk.Entry(speed_frame, textvariable=self.speed_limit, width=8).pack(side='left', padx=5)
        ttk.Button(speed_frame, text="Clear", command=self.clear_speed_limit, width=8).pack(side='left')

        # Progress Bar and Stats
        progress_frame = ttk.Frame(self.download_tab)
        progress_frame.pack(fill='x', pady=5)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient='horizontal',
            mode='determinate',
            style='green.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill='x', expand=True)

        stats_frame = ttk.Frame(self.download_tab)
        stats_frame.pack(fill='x', pady=5)

        ttk.Label(stats_frame, text="Speed:").pack(side='left')
        ttk.Label(stats_frame, textvariable=self.download_speed, width=10).pack(side='left', padx=5)

        ttk.Label(stats_frame, text="ETA:").pack(side='left')
        ttk.Label(stats_frame, textvariable=self.eta, width=8).pack(side='left', padx=5)

        ttk.Label(stats_frame, text="Taken:").pack(side='left')
        ttk.Label(stats_frame, textvariable=self.time_taken, width=8).pack(side='left', padx=5)

        ttk.Label(stats_frame, text="Size:").pack(side='left')
        ttk.Label(stats_frame, textvariable=self.file_size, width=10).pack(side='left', padx=5)

        # Buttons
        btn_frame = ttk.Frame(self.download_tab)
        btn_frame.pack(fill='x', pady=5)

        self.download_btn = ttk.Button(btn_frame, text="Start Download", command=self.start_download)
        self.download_btn.pack(side='left', padx=2)

        self.pause_btn = ttk.Button(btn_frame, text="Pause", command=self.toggle_pause, state='disabled')
        self.pause_btn.pack(side='left', padx=2)

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.cancel_download, state='disabled')
        self.cancel_btn.pack(side='left', padx=2)

        self.queue_btn = ttk.Button(btn_frame, text="Add to Queue", command=self.add_to_queue)
        self.queue_btn.pack(side='left', padx=2)

        self.remove_btn = ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected, state='disabled')
        self.remove_btn.pack(side='left', padx=2)

        # Queue List
        queue_frame = ttk.Frame(self.download_tab)
        queue_frame.pack(fill='x', pady=5)
        ttk.Label(queue_frame, text="Download Queue:").pack(side='left')

        self.queue_listbox = tk.Listbox(queue_frame, height=4, selectmode='single', exportselection=False)
        self.queue_listbox.pack(fill='x', expand=True, padx=5)
        self.queue_listbox.bind('<<ListboxSelect>>', lambda e: self.update_button_states())

        # Log Output
        self.log_text = scrolledtext.ScrolledText(
            self.download_tab,
            height=8,
            state='disabled',
            font=('Consolas', 10)
        )
        self.log_text.pack(fill='both', expand=True)

        # About Tab
        about_tab = ttk.Frame(tab_control)
        tab_control.add(about_tab, text='About')

        # About Tab Content
        about_frame = ttk.Frame(about_tab)
        about_frame.pack(expand=True, fill='both', padx=20, pady=20)

        try:
            from io import BytesIO
            import base64

            # Your base64 encoded image string
            logo_data = base64.b64decode(encoded_string)
            logo_img = Image.open(BytesIO(logo_data))
            logo_img = logo_img.resize((150, 150), Image.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            logo_label = ttk.Label(about_frame, image=self.logo_photo)
            logo_label.pack(pady=10)
        except:
            ttk.Label(about_frame, text="CodeZence", font=('Helvetica', 16)).pack(pady=10)

        ttk.Label(about_frame,
                  text="YTDash YouTube Downloader",
                  font=('Helvetica', 16, 'bold'),
                  foreground="#2b6cb0").pack(pady=5)

        ttk.Label(about_frame, text="by CodeZence", font=('Helvetica', 10, 'italic')).pack(pady=5)

        github_frame = ttk.Frame(about_frame)
        github_frame.pack(pady=10)
        ttk.Label(github_frame, text="GitHub:").pack(side='left')
        github_link = ttk.Label(github_frame,
                                text="github.com/naviijayZ",
                                foreground="blue",
                                cursor="hand2")
        github_link.pack(side='left')
        github_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/naviijayZ"))

        ttk.Label(about_frame, text="Version: 2.0").pack(pady=5)

        tab_control.pack(expand=1, fill='both')

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.set(folder)
            self.log(f"Download folder set to: {folder}")

    def clear_speed_limit(self):
        self.speed_limit.set("0")
        self.log("Speed limit cleared")

    def add_to_queue(self):
        url = self.url.get().strip()
        if url:
            try:
                if "playlist?list=" in url or "&list=" in url:
                    self.process_playlist(url)
                else:
                    self.queue_list.append({
                        'url': url,
                        'quality': self.quality.get()
                    })
                    self.log(f"Added to queue: {url} ({self.quality.get()})")
            except Exception as e:
                self.log(f"Error processing URL: {str(e)}")

            if not self.downloading:
                self.start_download()
            self.update_queue_listbox()

    def process_playlist(self, playlist_url):
        try:
            ydl_opts = {
                'extract_flat': True,
                'quiet': True,
                'no_warnings': True,
                'cookiefile': 'cookies.txt'
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                if 'entries' in info:
                    quality = self.quality.get()
                    for entry in info['entries']:
                        if entry:
                            video_url = f"https://youtube.com/watch?v={entry.get('id', '')}"
                            if video_url:
                                self.queue_list.append({
                                    'url': video_url,
                                    'quality': quality
                                })
                    self.log(f"Added {len(info['entries'])} videos from playlist")
        except Exception as e:
            self.log(f"Playlist error: {str(e)}")

    def remove_selected(self):
        selection = self.queue_listbox.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.queue_list):
                removed_item = self.queue_list.pop(index)
                self.update_queue_listbox()
                self.log(f"Removed from queue: {removed_item['url']}")
                self.update_button_states()

    def update_queue_listbox(self):
        self.queue_listbox.delete(0, tk.END)
        for item in self.queue_list:
            display_text = f"{item['url']} ({item['quality']})"
            self.queue_listbox.insert(tk.END, display_text)

    def start_download(self):
        if not self.downloading:
            url = self.url.get().strip()
            if url and not any(item['url'] == url for item in self.queue_list):
                self.queue_list.append({
                    'url': url,
                    'quality': self.quality.get()
                })

            if self.queue_list:
                queue_item = self.queue_list.pop(0)
                self.current_download = queue_item['url']
                self.current_quality = queue_item['quality']
                self.update_queue_listbox()
                self.download_thread = threading.Thread(target=self.download_video, daemon=True)
                self.download_thread.start()

    def check_queue(self):
        if not self.downloading and self.queue_list:
            self.start_download()
        self.root.after(1000, self.check_queue)

    def download_video(self):
        self.start_time = time.time()
        self.downloading = True
        self.cancel_requested = False
        self.paused = False
        self.update_button_states()

        try:
            speed_limit = int(self.speed_limit.get()) if self.speed_limit.get().isdigit() else 0
            rate_limit = speed_limit * 1024 if speed_limit > 0 else None

            ydl_opts = {
                'format': self.get_format_string(self.current_quality),
                'outtmpl': os.path.join(self.folder.get(), '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'ratelimit': rate_limit,
                'quiet': True,
                'no_warnings': True,
                'retries': 10,
                'fragment_retries': 10,
                'cookiefile': 'cookies.txt',
                'merge_output_format': 'mp4',  # Ensure merged output is MP4
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }],
                'extractor_args': {
                    'youtube': {
                        'skip': ['authcheck'],
                        'format': 'mp4'  # Prefer MP4 formats
                    }
                },
                'nopart': True,
                'continuedl': False
            }

            if self.current_quality == "MP3":
                ydl_opts.update({
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    }],
                    'keepvideo': False,
                    'format': 'bestaudio/best'
                })

            self.ydl = yt_dlp.YoutubeDL(ydl_opts)
            info = self.ydl.extract_info(self.current_download, download=False)
            self.current_filename = yt_dlp.utils.sanitize_filename(info.get('title', 'video'))

            self.log(f"Starting download: {self.current_download} ({self.current_quality})")
            self.ydl.download([self.current_download])

            self.log(f"✓ Download completed: {self.current_download}")

        except Exception as e:
            if not self.cancel_requested:
                self.log(f"❌ Download failed: {str(e)}")
            self.cleanup_temp_files()
        finally:
            self.downloading = False
            self.current_download = None
            self.current_quality = None
            self.current_filename = None
            self.ydl = None
            self.update_button_states()
            self.reset_progress_stats()

    def cleanup_temp_files(self):
        if not self.current_filename:
            return

        folder = self.folder.get()
        if not os.path.exists(folder):
            return

        base_name = os.path.splitext(self.current_filename)[0]
        temp_extensions = ['.part', '.ytdl', '.temp', '.tmp', '.download']

        for filename in os.listdir(folder):
            if (filename.startswith(base_name) and
                    any(filename.endswith(ext) for ext in temp_extensions)):
                file_path = os.path.join(folder, filename)
                try:
                    os.remove(file_path)
                    self.log(f"✅ Deleted temporary file: {filename}")
                except Exception as e:
                    self.log(f"❌ Failed to delete {filename}: {str(e)}")

    def get_format_string(self, quality=None):
        q = quality if quality else self.quality.get()
        if q == "MP3":
            return "bestaudio/best"
        elif "(4K)" in q:
            return "bestvideo[height>=2160][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        else:
            h = ''.join(filter(str.isdigit, q))
            return f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    def progress_hook(self, d):
        if self.cancel_requested:
            raise yt_dlp.DownloadError("Download cancelled by user")

        while self.paused and not self.cancel_requested:
            time.sleep(0.1)

        if d.get('status') == 'downloading':
            elapsed = time.time() - self.start_time
            hours, rem = divmod(elapsed, 3600)
            minutes, seconds = divmod(rem, 60)
            self.time_taken.set(f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")

            percent_str = d.get('_percent_str', '').replace('%', '').strip()
            if percent_str:
                try:
                    self.progress_bar['value'] = float(percent_str)
                except ValueError:
                    pass

            self.download_speed.set(d.get('_speed_str', '0 KB/s').strip())
            self.eta.set(d.get('_eta_str', '--:--').strip())

            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                if total_bytes < 1024:
                    size_str = f"{total_bytes} B"
                elif total_bytes < 1024 ** 2:
                    size_str = f"{total_bytes / 1024:.1f} KB"
                elif total_bytes < 1024 ** 3:
                    size_str = f"{total_bytes / (1024 ** 2):.1f} MB"
                else:
                    size_str = f"{total_bytes / (1024 ** 3):.1f} GB"
                self.file_size.set(size_str)

            self.root.update_idletasks()

    def reset_progress_stats(self):
        self.progress_bar['value'] = 0
        self.download_speed.set("0 KB/s")
        self.eta.set("--:--")
        self.time_taken.set("00:00:00")
        self.file_size.set("0 B")
        self.root.update_idletasks()

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.config(text="Resume" if self.paused else "Pause")
        self.pause_event.set() if self.paused else self.pause_event.clear()
        self.log("Download paused" if self.paused else "Download resumed")

        if self.paused and self.ydl:
            try:
                self.ydl.cancel_download()
            except:
                pass

    def cancel_download(self):
        self.cancel_requested = True
        self.pause_event.set()
        if self.ydl:
            try:
                self.ydl.cancel_download()
            except Exception as e:
                self.log(f"Error during cancel: {str(e)}")

        self.cleanup_temp_files()
        self.log("Download cancelled")
        self.reset_progress_stats()

    def update_button_states(self):
        self.download_btn.config(state='normal' if not self.downloading and self.queue_list else 'disabled')
        self.pause_btn.config(state='normal' if self.downloading else 'disabled')
        self.cancel_btn.config(state='normal' if self.downloading else 'disabled')
        self.queue_btn.config(state='normal')
        has_selection = bool(self.queue_listbox.curselection())
        self.remove_btn.config(state='normal' if has_selection and not self.downloading else 'disabled')

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.config(state='disabled')
        self.log_text.see('end')


if __name__ == "__main__":
    root = tk.Tk()
    app = YTDash(root)
    root.mainloop()