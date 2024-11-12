# app/anpr.py
import cv2
import easyocr
import numpy as np
import os
import tempfile

reader = easyocr.Reader(['en'])  # Initialize once to improve performance

def recognize_license_plate_from_image(image_path: str):
    """
    Process a single image to detect and recognize license plates.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Could not read the image.")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Use OpenCV to detect license plates based on contour analysis
    plates = detect_license_plate_contours(gray, image)

    results = []

    for plate in plates:
        x, y, w, h = plate
        plate_image = image[y:y + h, x:x + w]
        plate_text = extract_text_from_image(plate_image)
        if plate_text:
            results.append({
                "plate": plate_text,
                "coordinates": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
            })

    return results

def recognize_license_plate_from_video(video_path: str):
    """
    Process a video to detect and recognize license plates in each frame.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open the video.")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    results = []
    processed_frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        processed_frames += 1

        # Process every nth frame to reduce computation
        if processed_frames % 30 == 0:  # Adjust the frame rate as needed
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            plates = detect_license_plate_contours(gray, frame)

            for plate in plates:
                x, y, w, h = plate
                plate_image = frame[y:y + h, x:x + w]
                plate_text = extract_text_from_image(plate_image)
                if plate_text:
                    results.append({
                        "frame": processed_frames,
                        "plate": plate_text,
                        "coordinates": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
                    })

    cap.release()
    return results

def detect_license_plate_contours(gray, image):
    """
    Detect contours that potentially contain license plates.
    """
    # Apply some preprocessing
    blurred = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(blurred, 30, 200)

    # Find contours based on edges detected
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plates = []
    for cnt in contours:
        # Approximate the contour
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.018 * peri, True)

        # The license plate should be a rectangle (4 sides)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = w / float(h)
            if 2 < aspect_ratio < 6:  # Typical aspect ratio for license plates
                plates.append((x, y, w, h))

    return plates

def extract_text_from_image(plate_image):
    """
    Extract text from the license plate image using EasyOCR.
    """
    # Convert image to RGB (EasyOCR expects RGB)
    plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2RGB)
    
    # Optional: Further preprocessing to improve OCR accuracy
    # e.g., thresholding, resizing, etc.
    # resized = cv2.resize(plate_image, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    # _, thresh = cv2.threshold(resized, 150, 255, cv2.THRESH_BINARY)

    # Use EasyOCR to read text
    result = reader.readtext(plate_image)

    # Extract the text results
    plate_texts = [res[1] for res in result if res[2] > 0.5]  # Confidence filtering

    # Join texts if multiple detections
    full_text = " ".join(plate_texts).replace(" ", "").upper()

    # Basic validation (you can enhance this with regex)
    if len(full_text) >= 6:
        return full_text
    else:
        return None