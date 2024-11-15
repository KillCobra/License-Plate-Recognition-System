import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import requests
from PIL import Image, ImageTk
import os
import threading
import json
import websocket
import cv2
import numpy as np
from websocket import ABNF

API_URL = "http://localhost:8000/upload/"  
WEBSOCKET_URL = "ws://localhost:8000/live/"  # WebSocket endpoint for live camera

class ANPRFrontend:
    def __init__(self, root):
        self.root = root
        self.root.title("License Plate Recognition System")
        self.root.geometry("1000x800")
        self.root.configure(bg='#f0f0f0')  # Light gray background

        # Main container with padding
        main_container = tk.Frame(root, padx=25, pady=20, bg='#f0f0f0')
        main_container.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(main_container, 
                             text="License Plate Recognition System",
                             font=('Helvetica', 16, 'bold'),
                             bg='#f0f0f0',
                             pady=10)
        title_label.pack()

        # File Selection and Image Preview Frame
        file_preview_frame = tk.Frame(main_container, bg='#f0f0f0')
        file_preview_frame.pack(fill=tk.X, pady=(0, 15))

        # File Selection Frame with improved styling
        file_frame = tk.LabelFrame(
            file_preview_frame,
            text="Image/Video Upload",
            padx=10,
            pady=10,
            font=('Helvetica', 10, 'bold'),
            bg='#ffffff',
            relief=tk.GROOVE
        )
        file_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.select_button = tk.Button(
            file_frame,
            text="Select File",
            command=self.select_file,
            width=15,
            relief=tk.GROOVE,
            bg='#4a90e2',
            fg='white',
            font=('Helvetica', 9),
            cursor='hand2'
        )
        self.select_button.grid(row=0, column=0, padx=5, pady=5)

        self.upload_button = tk.Button(
            file_frame,
            text="Upload & Analyze",
            command=self.upload_file,
            state=tk.DISABLED,
            width=15,
            relief=tk.GROOVE,
            bg='#4a90e2',
            fg='white',
            font=('Helvetica', 9),
            cursor='hand2'
        )
        self.upload_button.grid(row=0, column=1, padx=5, pady=5)

        self.file_label = tk.Label(
            file_frame,
            text="No file selected",
            fg="#666666",
            bg='#ffffff',
            font=('Helvetica', 9)
        )
        self.file_label.grid(row=0, column=2, padx=10, pady=5, sticky='w')

        # Image Preview Section
        preview_frame = tk.LabelFrame(
            file_preview_frame,
            text="Image Preview",
            padx=10,
            pady=10,
            font=('Helvetica', 10, 'bold'),
            bg='#ffffff',
            relief=tk.GROOVE
        )
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self.image_preview_label = tk.Label(preview_frame, bg='#ffffff')
        self.image_preview_label.pack()

        # Live Camera Frame with improved styling
        camera_frame = tk.LabelFrame(main_container, 
                                   text="Live Camera Detection", 
                                   padx=15, 
                                   pady=15,
                                   font=('Helvetica', 10, 'bold'),
                                   bg='#ffffff',
                                   relief=tk.GROOVE)
        camera_frame.pack(fill=tk.X, pady=(0, 15))

        self.start_live_button = tk.Button(camera_frame, 
                                         text="▶ Start Camera", 
                                         command=self.start_live_camera,
                                         width=15, 
                                         relief=tk.GROOVE,
                                         bg='#2ecc71',
                                         fg='black',
                                         font=('Helvetica', 9),
                                         cursor='hand2')
        self.start_live_button.pack(side=tk.LEFT, padx=5)

        self.stop_live_button = tk.Button(camera_frame, 
                                        text="⬛ Stop Camera", 
                                        command=self.stop_live_camera,
                                        state=tk.DISABLED, 
                                        width=15, 
                                        relief=tk.GROOVE,
                                        bg='#e74c3c',
                                        fg='black',
                                        font=('Helvetica', 9),
                                        cursor='hand2')
        self.stop_live_button.pack(side=tk.LEFT, padx=5)

        # Video Display Frame
        self.video_frame = tk.LabelFrame(
            main_container,
            text="Camera Preview",
            padx=0,
            pady=0,
            font=('Helvetica', 10, 'bold'),
            bg='#ffffff',
            relief=tk.GROOVE
        )
        self.video_frame.pack(fill=tk.X, pady=(0, 15))

        self.video_label = tk.Label(self.video_frame, bg='#ffffff')
        self.video_label.pack(padx=0, pady=0)

        # Results Frame with improved styling
        results_frame = tk.LabelFrame(main_container, 
                                    text="Detection Results", 
                                    padx=15, 
                                    pady=15,
                                    font=('Helvetica', 10, 'bold'),
                                    bg='#ffffff',
                                    relief=tk.GROOVE)
        results_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = scrolledtext.ScrolledText(
            results_frame, 
            width=80, 
            height=10,
            font=('Consolas', 10),
            wrap=tk.WORD,
            padx=10,
            pady=10,
            bg='#ffffff',
            relief=tk.SOLID
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # Status bar with improved styling
        self.status_bar = tk.Label(main_container, 
                                 text="Ready", 
                                 bd=1, 
                                 relief=tk.SUNKEN, 
                                 anchor=tk.W,
                                 bg='#e8e8e8',
                                 font=('Helvetica', 9),
                                 padx=10,
                                 pady=5)
        self.status_bar.pack(fill=tk.X, pady=(10, 0))

        # Configure tags for text styling
        self.result_text.tag_configure('grey_text', foreground='#666666')
        self.result_text.tag_configure('success', foreground='#2ecc71')
        self.result_text.tag_configure('error', foreground='#e74c3c')

        # Initialize video related variables
        self.video_capture = None
        self.update_id = None

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

            # Display image preview if the file is an image
            file_extension = os.path.splitext(filepath)[1].lower()
            if file_extension in [".jpg", ".jpeg", ".png"]:
                try:
                    image = Image.open(filepath)
                    image.thumbnail((400, 400))
                    self.preview_image = ImageTk.PhotoImage(image)
                    self.image_preview_label.config(image=self.preview_image)
                except Exception as e:
                    self.result_text.insert(tk.END, f"Failed to load image preview: {str(e)}\n")
                    self.image_preview_label.config(image='')
            else:
                # Clear image preview if not an image
                self.image_preview_label.config(image='')
        else:
            self.file_label.config(text="No file selected")
            self.upload_button.config(state=tk.DISABLED)
            self.status_bar.config(text="Ready")
            self.image_preview_label.config(image='')

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
        # Get current content and make it grey
        current_content = self.result_text.get("1.0", tk.END)
        if current_content.strip():
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, current_content, 'grey_text')
        
        # Add new results in black
        self.result_text.insert(tk.END, f"Filename: {data.get('filename')}\n")
        results = data.get("results", [])
        if not results:
            self.result_text.insert(tk.END, "No license plates recognized.\n")
        else:
            for idx, plate in enumerate(results, start=1):
                plate_text = plate.get("plate")
                coords = plate.get("coordinates")
                self.result_text.insert(tk.END, f"Plate {idx}: {plate_text}\n")
                self.result_text.insert(tk.END, f"Coordinates: x={coords.get('x')}, y={coords.get('y')}, width={coords.get('width')}, height={coords.get('height')}\n\n")
        
        # Scroll to bottom
        self.scroll_to_bottom()

    def start_live_camera(self):
        if self.running:
            messagebox.showinfo("Live Camera", "Live camera is already running.")
            return

        # Initialize video capture
        self.video_capture = cv2.VideoCapture(0)
        if not self.video_capture.isOpened():
            messagebox.showerror("Error", "Could not access the camera.")
            return

        # Set camera resolution
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.result_text.insert(tk.END, "Starting live camera...\n")
        self.start_live_button.config(state=tk.DISABLED)
        self.stop_live_button.config(state=tk.NORMAL)
        self.running = True

        # Start video feed update
        self.update_video_feed()

        # Start WebSocket connection
        self.ws_thread = threading.Thread(target=self.run_websocket, daemon=True)
        self.ws_thread.start()

    def run_websocket(self):
        def on_open(ws):
            self.result_text.after(0, lambda: self.result_text.insert(tk.END, "WebSocket connection established\n"))

        def on_message(ws, message):
            data = json.loads(message)
            if "results" in data:
                results = data["results"]
                # Store the latest results for drawing rectangles
                self.latest_results = results
                if results:
                    # Grey out existing content
                    current_content = self.result_text.get("1.0", tk.END)
                    if current_content.strip():
                        self.result_text.after(0, lambda: (
                            self.result_text.delete("1.0", tk.END),
                            self.result_text.insert(tk.END, current_content, 'grey_text')
                        ))
                    
                    # Add new results in black
                    for plate in results:
                        plate_text = plate.get("plate")
                        coords = plate.get("coordinates")
                        display_text = f"Live Plate: {plate_text}\nCoordinates: x={coords.get('x')}, y={coords.get('y')}, width={coords.get('width')}, height={coords.get('height')}\n\n"
                        self.result_text.after(0, lambda t=display_text: (
                            self.result_text.insert(tk.END, t),
                            self.scroll_to_bottom()
                        ))
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
        self.running = False
        
        # Stop video feed updates
        if self.update_id:
            self.root.after_cancel(self.update_id)
            self.update_id = None

        # Release video capture
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None

        # Clear the video label
        self.video_label.config(image='')
        
        # Close WebSocket connection
        if self.ws:
            self.ws.close()

    def on_closing(self):
        self.stop_live_camera()
        self.root.destroy()

    def update_video_feed(self):
        if self.video_capture is not None and self.running:
            ret, frame = self.video_capture.read()
            if ret:
                # Resize frame to fit nicely in the GUI
                frame = cv2.resize(frame, (640, 360))
                
                # Draw rectangles for any detected plates
                if hasattr(self, 'latest_results') and self.latest_results:
                    for result in self.latest_results:
                        coords = result.get('coordinates', {})
                        # Scale coordinates to match resized frame
                        x = int(coords.get('x', 0) * 640 / 1280)
                        y = int(coords.get('y', 0) * 360 / 720)
                        w = int(coords.get('width', 0) * 640 / 1280)
                        h = int(coords.get('height', 0) * 360 / 720)
                        
                        # Draw rectangle
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                        # Draw text above rectangle
                        cv2.putText(frame, result.get('plate', ''), (x, y - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # Convert to RGB for tkinter
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(image=image)
                self.video_label.config(image=photo)
                self.video_label.image = photo
                
                # Process and send frames at a lower rate (every 5th frame)
                if hasattr(self, 'frame_count'):
                    self.frame_count += 1
                else:
                    self.frame_count = 0
                    
                if self.frame_count % 5 == 0:  # Process every 5th frame
                    # Create a copy of the original frame for processing
                    process_frame = cv2.resize(frame, (1280, 720))
                    _, buffer = cv2.imencode('.jpg', process_frame)
                    jpg_as_text = buffer.tobytes()
                    
                    # Send frame to WebSocket if connection is active
                    if self.ws and self.ws.sock and self.ws.sock.connected:
                        try:
                            self.ws.send(jpg_as_text, opcode=websocket.ABNF.OPCODE_BINARY)
                        except Exception as e:
                            print(f"Error sending frame: {e}")
                
                # Schedule the next update at a reasonable rate (30 FPS)
                self.update_id = self.root.after(33, self.update_video_feed)  # ~30 FPS

    def scroll_to_bottom(self):
        """Scroll the result text widget to the bottom"""
        self.result_text.see(tk.END)
        self.result_text.update()

if __name__ == "__main__":
    root = tk.Tk()
    app = ANPRFrontend(root)
    root.mainloop()