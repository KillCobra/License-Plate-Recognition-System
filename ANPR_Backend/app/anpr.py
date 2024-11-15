# app/anpr.py
import cv2
import easyocr
import numpy as np
import torch
from yolov5 import YOLOv5  # Ensure yolov5 is correctly installed
import os

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])  # Initialize once to improve performance

# Load the trained YOLOv5 model
MODEL_PATH = 'path/to/your/trained_model.pt'  # Replace with your model path
yolo_model = YOLOv5(MODEL_PATH, device='cuda' if torch.cuda.is_available() else 'cpu')

def recognize_license_plate_from_image(image_path: str):
    """
    Process a single image to detect and recognize license plates using YOLOv5 and EasyOCR.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Could not read the image.")

    # Perform detection using YOLOv5
    detections = yolo_model.predict(image)

    results = []

    for det in detections.xyxy[0]:  # assuming one class
        x1, y1, x2, y2, confidence, cls = det
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

        # Extract the license plate region
        plate_image = image[y1:y2, x1:x2]

        # Extract text from the plate image
        plate_text = extract_text_from_image(plate_image)

        if plate_text:
            results.append({
                "plate": plate_text,
                "confidence": float(confidence),
                "coordinates": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}
            })

    return results

def recognize_license_plate_from_video(video_path: str):
    """
    Process a video to detect and recognize license plates in each frame using YOLOv5 and EasyOCR.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open the video.")

    results = []
    processed_frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        processed_frames += 1

        if processed_frames % 30 == 0:
            detections = yolo_model.predict(frame)

            for det in detections.xyxy[0]:
                x1, y1, x2, y2, confidence, cls = det
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

                plate_image = frame[y1:y2, x1:x2]
                plate_text = extract_text_from_image(plate_image)
                if plate_text:
                    results.append({
                        "frame": processed_frames,
                        "plate": plate_text,
                        "confidence": float(confidence),
                        "coordinates": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}
                    })

    cap.release()
    return results

def recognize_license_plate_from_frame(frame):
    """
    Process a single frame to detect and recognize license plates using YOLOv5 and EasyOCR.
    """
    detections = yolo_model.predict(frame)

    results = []

    for det in detections.xyxy[0]:
        x1, y1, x2, y2, confidence, cls = det
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

        plate_image = frame[y1:y2, x1:x2]
        plate_text = extract_text_from_image(plate_image)
        if plate_text:
            results.append({
                "plate": plate_text,
                "confidence": float(confidence),
                "coordinates": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}
            })

    return results

def extract_text_from_image(plate_image):
    """
    Extract text from the license plate image using EasyOCR.
    """
    if plate_image.size == 0:
        return None

    # Convert image to RGB (EasyOCR expects RGB)
    plate_image_rgb = cv2.cvtColor(plate_image, cv2.COLOR_BGR2RGB)

    # Apply additional preprocessing if needed
    # Example: Increase contrast, apply filters, etc.

    # Use EasyOCR to read text
    result = reader.readtext(plate_image_rgb)

    # Extract the text results
    plate_texts = [res[1] for res in result if res[2] > 0.5]  # Confidence filtering

    # Join texts if multiple detections
    full_text = " ".join(plate_texts).replace(" ", "").upper()

    # Basic validation
    if len(full_text) >= 6:
        return full_text
    else:
        return None