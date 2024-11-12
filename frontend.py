import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import requests
from PIL import Image, ImageTk
import os

API_URL = "http://localhost:8000/upload/"  # Update if your backend is hosted elsewhere

class ANPRFrontend:
    def __init__(self, root):
        self.root = root
        self.root.title("ANPR Frontend")
        self.root.geometry("600x500")

        # Selected file path
        self.file_path = None

        # Button to select file
        self.select_button = tk.Button(root, text="Select Image/Video", command=self.select_file)
        self.select_button.pack(pady=10)

        # Label to display selected file
        self.file_label = tk.Label(root, text="No file selected")
        self.file_label.pack(pady=5)

        # Button to upload file
        self.upload_button = tk.Button(root, text="Upload and Analyze", command=self.upload_file, state=tk.DISABLED)
        self.upload_button.pack(pady=10)

        # ScrolledText to display results
        self.result_text = scrolledtext.ScrolledText(root, width=70, height=20)
        self.result_text.pack(pady=10)

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
        else:
            self.file_label.config(text="No file selected")
            self.upload_button.config(state=tk.DISABLED)

    def upload_file(self):
        if not self.file_path:
            messagebox.showwarning("No File", "Please select a file to upload.")
            return

        self.result_text.insert(tk.END, f"Uploading {os.path.basename(self.file_path)}...\n")
        try:
            with open(self.file_path, "rb") as f:
                files = {"file": (os.path.basename(self.file_path), f)}
                response = requests.post(API_URL, files=files)
            
            if response.status_code == 200:
                data = response.json()
                self.display_results(data)
            else:
                self.result_text.insert(tk.END, f"Error {response.status_code}: {response.json().get('detail')}\n")
        except Exception as e:
            self.result_text.insert(tk.END, f"An error occurred: {str(e)}\n")

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

if __name__ == "__main__":
    root = tk.Tk()
    app = ANPRFrontend(root)
    root.mainloop()