import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import requests
from PIL import Image, ImageTk
import os
import threading
import json
import websocket

API_URL = "http://localhost:8000/upload/"  # Update if your backend is hosted elsewhere
WEBSOCKET_URL = "ws://localhost:8000/live/"  # WebSocket endpoint for live camera

class ANPRFrontend:
    def __init__(self, root):
        self.root = root
        self.root.title("ANPR System")
        self.root.geometry("800x700")

        # Main container with padding
        main_container = tk.Frame(root, padx=20, pady=15)
        main_container.pack(fill=tk.BOTH, expand=True)

        # File Selection Frame
        file_frame = tk.LabelFrame(main_container, text="File Selection", padx=10, pady=10)
        file_frame.pack(fill=tk.X, pady=(0, 15))

        self.select_button = tk.Button(file_frame, text="Select Image/Video", command=self.select_file,
                                     width=15, relief=tk.GROOVE)
        self.select_button.pack(side=tk.LEFT, padx=5)

        self.upload_button = tk.Button(file_frame, text="Upload and Analyze", command=self.upload_file,
                                     state=tk.DISABLED, width=15, relief=tk.GROOVE)
        self.upload_button.pack(side=tk.LEFT, padx=5)

        self.file_label = tk.Label(file_frame, text="No file selected", fg="gray")
        self.file_label.pack(side=tk.LEFT, padx=10)

        # Live Camera Frame
        camera_frame = tk.LabelFrame(main_container, text="Live Camera Control", padx=10, pady=10)
        camera_frame.pack(fill=tk.X, pady=(0, 15))

        self.start_live_button = tk.Button(camera_frame, text="Start Live Camera", command=self.start_live_camera, width=15, relief=tk.GROOVE)
        self.start_live_button.pack(side=tk.LEFT, padx=5)

        self.stop_live_button = tk.Button(camera_frame, text="Stop Live Camera", command=self.stop_live_camera, state=tk.DISABLED, width=15, relief=tk.GROOVE)
        self.stop_live_button.pack(side=tk.LEFT, padx=5)

        # Results Frame
        results_frame = tk.LabelFrame(main_container, text="Recognition Results", padx=10, pady=10)
        results_frame.pack(fill=tk.BOTH, expand=True)

        # ScrolledText with better styling
        self.result_text = scrolledtext.ScrolledText(
            results_frame, 
            width=80, 
            height=25,
            font=('Consolas', 10),
            wrap=tk.WORD,
            padx=5,
            pady=5
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_bar = tk.Label(main_container, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, pady=(10, 0))

        # WebSocket thread control
        self.ws = None
        self.ws_thread = None
        self.running = False

        # Handle window closing to ensure threads are properly terminated
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def select_file(self):
        filetypes = (
            ("Image files", "*.jpg *.jpeg *.png"),
            ("Video files", "*.mp4 *.avi *.mov *.mkv"),
            ("All files", "*.*")
        )
        filepath = filedialog.askopenfilename(title="Open a file", initialdir=os.getcwd(), filetypes=filetypes)
        if filepath:
            self.file_path = filepath
            self.file_label.config(text=os.path.basename(filepath))
            self.upload_button.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "File selected. Ready to upload.\n")
            self.status_bar.config(text=f"Selected: {os.path.basename(filepath)}")
        else:
            self.file_label.config(text="No file selected")
            self.upload_button.config(state=tk.DISABLED)
            self.status_bar.config(text="Ready")

    def upload_file(self):
        if not self.file_path:
            messagebox.showwarning("No File", "Please select a file to upload.")
            return

        self.status_bar.config(text="Uploading file...")
        self.result_text.insert(tk.END, f"Uploading {os.path.basename(self.file_path)}...\n")
        try:
            with open(self.file_path, "rb") as f:
                files = {"file": (os.path.basename(self.file_path), f)}
                response = requests.post(API_URL, files=files)
            
            if response.status_code == 200:
                data = response.json()
                self.display_results(data)
                self.status_bar.config(text="Analysis complete")
            else:
                self.result_text.insert(tk.END, f"Error {response.status_code}: {response.json().get('detail')}\n")
                self.status_bar.config(text="Error during upload")
        except Exception as e:
            self.result_text.insert(tk.END, f"An error occurred: {str(e)}\n")
            self.status_bar.config(text="Error during upload")

    def display_results(self, data):
        self.result_text.insert(tk.END, f"Filename: {data.get('filename')}\n")
        results = data.get("results", [])
        if not results:
            self.result_text.insert(tk.END, "No license plates recognized.\n")
            return
        for idx, plate in enumerate(results, start=1):
            plate_text = plate.get("plate")
            coords = plate.get("coordinates")
            self.result_text.insert(tk.END, f"Plate {idx}: {plate_text}\n")
            self.result_text.insert(tk.END, f"Coordinates: x={coords.get('x')}, y={coords.get('y')}, width={coords.get('width')}, height={coords.get('height')}\n\n")

    def start_live_camera(self):
        if self.running:
            messagebox.showinfo("Live Camera", "Live camera is already running.")
            return

        self.result_text.insert(tk.END, "Starting live camera...\n")
        self.start_live_button.config(state=tk.DISABLED)
        self.stop_live_button.config(state=tk.NORMAL)
        self.running = True

        self.ws_thread = threading.Thread(target=self.run_websocket, daemon=True)
        self.ws_thread.start()

    def run_websocket(self):
        def on_open(ws):
            self.result_text.after(0, lambda: self.result_text.insert(tk.END, "WebSocket connection established\n"))

        def on_message(ws, message):
            data = json.loads(message)
            if "results" in data:
                results = data["results"]
                if results:
                    for plate in results:
                        plate_text = plate.get("plate")
                        coords = plate.get("coordinates")
                        display_text = f"Live Plate: {plate_text}\nCoordinates: x={coords.get('x')}, y={coords.get('y')}, width={coords.get('width')}, height={coords.get('height')}\n\n"
                        self.result_text.after(0, lambda: self.result_text.insert(tk.END, display_text))
            elif "error" in data:
                error_msg = f"Error: {data['error']}\n"
                self.result_text.after(0, lambda: self.result_text.insert(tk.END, error_msg))

        def on_error(ws, error):
            error_msg = f"WebSocket error: {error}\n"
            self.result_text.after(0, lambda: self.result_text.insert(tk.END, error_msg))
            # Reset UI state
            self.root.after(0, lambda: self.start_live_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_live_button.config(state=tk.DISABLED))
            self.running = False

        def on_close(ws, close_status_code, close_msg):
            self.result_text.after(0, lambda: self.result_text.insert(tk.END, "Live camera stopped.\n"))
            self.root.after(0, lambda: self.start_live_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_live_button.config(state=tk.DISABLED))
            self.running = False

        self.ws = websocket.WebSocketApp(
            WEBSOCKET_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        try:
            self.ws.run_forever()
        except Exception as e:
            error_msg = f"WebSocket exception: {str(e)}\n"
            self.result_text.after(0, lambda: self.result_text.insert(tk.END, error_msg))

    def stop_live_camera(self):
        if not self.running:
            messagebox.showinfo("Live Camera", "Live camera is not running.")
            return

        self.result_text.insert(tk.END, "Stopping live camera...\n")
        self.stop_live_button.config(state=tk.DISABLED)
        if self.ws:
            self.ws.close()
        self.running = False

    def on_closing(self):
        if self.running and self.ws:
            self.ws.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ANPRFrontend(root)
    root.mainloop()