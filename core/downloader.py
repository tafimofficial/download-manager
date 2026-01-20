import os
import requests
import threading
import time
import json
from urllib.parse import urlparse
import shutil

class Downloader:
    # Optimized session for massive concurrency
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=500, 
        pool_maxsize=500, 
        max_retries=3,
        pool_block=False
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    def __init__(self, url, save_path, threads=32):
        self.url = url
        self.original_save_path = save_path
        self.threads = threads
        self.file_size = 0
        self.filename = ""
        self.stop_event = threading.Event()
        self.chunk_info = [] 
        self.downloaded_size = 0
        self.status = "idle" 
        self.speed = 0
        self.last_update_time = time.time() # For precise speed calc
        self.speed_history = [] # For smoothing speed display
        
        # Dynamic chunk size optimization
        # Start with 1MB, can be adjusted based on network conditions if needed
        self.chunk_size = 1024 * 1024
        
        # Determine filename
        if os.path.isdir(save_path):
             parsed_url = urlparse(url)
             self.filename = os.path.basename(parsed_url.path)
             if not self.filename:
                 self.filename = "downloaded_file"
             self.save_path = os.path.join(save_path, self.filename)
        else:
             self.filename = os.path.basename(save_path)
             self.save_path = save_path

        self._update_temp_paths()

    def _update_temp_paths(self):
        self.base_dir = os.path.dirname(self.save_path)
        self.temp_dir = os.path.join(self.base_dir, ".tafim_tmp", f"{self.filename}_{int(time.time())}") 
        # Added timestamp to handle same-name downloads cleanly or just use filename if we want resume?
        # Resume needs stable path.
        self.temp_dir = os.path.join(self.base_dir, ".tafim_tmp", self.filename)
        self.state_file = os.path.join(self.temp_dir, "state.json")
        if not os.path.exists(self.temp_dir):
            try: 
                os.makedirs(self.temp_dir, exist_ok=True)
                # Hide the folder on Windows
                if os.name == 'nt':
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    ret = ctypes.windll.kernel32.SetFileAttributesW(self.temp_dir, FILE_ATTRIBUTE_HIDDEN)
            except: pass

    def get_file_info(self):
        try:
            # High-speed optimized headers
            headers = {
                'Accept-Encoding': 'identity',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = self.session.head(self.url, allow_redirects=True, headers=headers, timeout=10)
            
            # Try to get filename from Content-Disposition
            cd = response.headers.get('content-disposition')
            if cd and 'filename=' in cd:
                fname = cd.split('filename=')[-1].strip(' "')
                if fname:
                    self.filename = fname
                    # Re-evaluate save path if filename changed
                    self.save_path = os.path.join(os.path.dirname(self.save_path), self.filename)
                    self._update_temp_paths()
                    # If we already had state, we might need to move it? 
                    # For now assume new download or we find it in new path.

            self.file_size = int(response.headers.get('content-length', 0))
            accept_ranges = response.headers.get('accept-ranges', 'none')
            return self.file_size, accept_ranges == 'bytes'
        except Exception as e:
            print(f"Error getting file info: {e}")
            return 0, False

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.chunk_info = data['chunks']
                    self.file_size = data['file_size']
                    # Calculate downloaded size from existing part files if possible, or trust state
                    self.downloaded_size = sum(c['current'] for c in self.chunk_info)
                    return True
            except:
                return False
        return False

    def save_state(self):
        try:
            data = {
                'url': self.url,
                'file_size': self.file_size,
                'chunks': self.chunk_info
            }
            # Ensure directory exists just in case
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            # Non-critical failure, just print warning
            print(f"Warning: Could not save state: {e}")
            
    def download_chunk(self, chunk_index, start, end):
        current_offset = self.chunk_info[chunk_index]['current']
        # If already done
        if current_offset >= (end - start + 1):
             self.chunk_info[chunk_index]['status'] = 'completed'
             return

        headers = {
            'Range': f'bytes={start + current_offset}-{end}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            # Using a larger chunk size (1MB) for high-speed transfer via session
            with self.session.get(self.url, headers=headers, stream=True, timeout=15) as r:
                r.raise_for_status()
                part_file = os.path.join(self.temp_dir, f"part{chunk_index}")
                mode = 'ab' if current_offset > 0 else 'wb'
                with open(part_file, mode) as f:
                    for chunk in r.iter_content(chunk_size=self.chunk_size): # Dynamic chunk size
                        if self.stop_event.is_set():
                            return
                        if chunk:
                            f.write(chunk)
                            length = len(chunk)
                            self.chunk_info[chunk_index]['current'] += length
                            with threading.Lock():
                                self.downloaded_size += length
            self.chunk_info[chunk_index]['status'] = 'completed'
        except Exception as e:
            print(f"Error in chunk {chunk_index}: {e}")
            self.chunk_info[chunk_index]['status'] = 'error'

    def start(self):
        if self.status == "downloading":
             return

        self.status = "downloading"
        self.stop_event.clear()

        # Try to resume
        if not self.load_state():
            size, resumable = self.get_file_info()
            if size == 0:
                self.status = "error"
                print("Could not get file size.")
                return
            
            self.file_size = size
            if resumable and self.threads > 1:
                chunk_size = size // self.threads
                self.chunk_info = []
                for i in range(self.threads):
                    start = i * chunk_size
                    end = (i + 1) * chunk_size - 1 if i < self.threads - 1 else size - 1
                    self.chunk_info.append({'start': start, 'end': end, 'current': 0, 'status': 'pending'})
            else:
                 self.chunk_info = [{'start': 0, 'end': size - 1, 'current': 0, 'status': 'pending'}]
        
        self.save_state()
        
        # EXPLICITLY ensure temp directory exists before spawning threads
        try: 
            os.makedirs(self.temp_dir, exist_ok=True)
        except Exception as e:
            print(f"Critical Error: Could not create temp dir: {e}")
            self.status = "error"
            return

        self.threads_list = []
        for i, chunk in enumerate(self.chunk_info):
            if chunk['status'] != 'completed':
                t = threading.Thread(target=self.download_chunk, args=(i, chunk['start'], chunk['end']), daemon=True)
                self.threads_list.append(t)
                t.start()
        
        # Monitor thread
        monitor = threading.Thread(target=self.monitor_progress, daemon=True)
        monitor.start()

    def monitor_progress(self):
        last_downloaded = self.downloaded_size
        self.last_update_time = time.time()
        
        while not self.stop_event.is_set():
             time.sleep(0.1)
             now = time.time()
             elapsed = now - self.last_update_time
             current_downloaded = self.downloaded_size
             
             # Instantaneous speed
             instant_speed = (current_downloaded - last_downloaded) / elapsed if elapsed > 0 else 0
             
             # Rolling average smoothing (IDM style)
             self.speed_history.append(instant_speed)
             if len(self.speed_history) > 10: # 1s window (10 * 0.1s)
                 self.speed_history.pop(0)
             
             self.speed = sum(self.speed_history) / len(self.speed_history)
             
             last_downloaded = current_downloaded
             self.last_update_time = now
             self.save_state()

             # Check completion
             if all(c['status'] == 'completed' for c in self.chunk_info):
                 self.status = "merging"
                 self.merge_files()
                 self.status = "completed"
                 if os.path.exists(self.state_file):
                     os.remove(self.state_file)
                 self.stop_event.set()
                 break
             
             # Check for active threads. If all died but not completed, we might have an error or need retry logic.
             # For this simple v1, we just let it sit or user can pause/resume.

    def pause(self):
        self.stop_event.set()
        self.status = "paused"
        self.save_state()

    def cancel(self):
        self.stop_event.set()
        self.status = "cancelled"
        # Give threads time to stop
        time.sleep(0.5) 
        
        # Remove temp dir
        for _ in range(5):
            if os.path.exists(self.temp_dir):
                 try:
                     shutil.rmtree(self.temp_dir)
                     break
                 except:
                     time.sleep(0.5)

    def merge_files(self):
        try:
            if len(self.chunk_info) == 1:
                 part_file = os.path.join(self.temp_dir, "part0")
                 if os.path.exists(part_file):
                     if os.path.exists(self.save_path):
                         os.remove(self.save_path)
                     shutil.move(part_file, self.save_path)
            else:
                with open(self.save_path, 'wb') as outfile:
                    for i in range(len(self.chunk_info)):
                        part_file = os.path.join(self.temp_dir, f"part{i}")
                        if os.path.exists(part_file):
                            with open(part_file, 'rb') as infile:
                                # Copy in chunks to avoid memory issues with huge files
                                while True:
                                    chunk = infile.read(10 * 1024 * 1024) # 10MB buffer
                                    if not chunk:
                                        break
                                    outfile.write(chunk)
            
            # Cleanup temp dir after successful merge
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error merging: {e}")
            self.status = "error"

    def get_progress(self):
        if self.file_size == 0:
            return 0
        return self.downloaded_size / self.file_size
