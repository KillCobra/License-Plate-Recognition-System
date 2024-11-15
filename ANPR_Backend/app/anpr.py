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
        x, y, w, h, angle = plate
        plate_image = image[y:y + h, x:x + w]
        plate_text = extract_text_from_image(plate_image, angle)
        if plate_text:
            results.append({
                "plate": plate_text,
                "coordinates": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                "angle": float(angle)
            })

    return results

def recognize_license_plate_from_video(video_path: str):
    """
    Process a video to detect and recognize license plates in each frame.
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
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            plates = detect_license_plate_contours(gray, frame)

            for plate in plates:
                x, y, w, h, angle = plate
                plate_image = frame[y:y + h, x:x + w]
                plate_text = extract_text_from_image(plate_image, angle)
                if plate_text:
                    results.append({
                        "frame": processed_frames,
                        "plate": plate_text,
                        "coordinates": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                        "angle": float(angle)
                    })

    cap.release()
    return results

def recognize_license_plate_from_frame(frame):
    """
    Process a single frame to detect and recognize license plates.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    plates = detect_license_plate_contours(gray, frame)

    results = []

    for plate in plates:
        x, y, w, h, angle = plate
        plate_image = frame[y:y + h, x:x + w]
        plate_text = extract_text_from_image(plate_image, angle)
        if plate_text:
            results.append({
                "plate": plate_text,
                "coordinates": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                "angle": float(angle)
            })

    return results

def detect_license_plate_contours(gray, image):
    """
    Detect contours that potentially contain license plates, including tilted ones.
    """
    # Apply bilateral filter to reduce noise while keeping edges sharp
    blurred = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Edge detection on grayscale image
    edged = cv2.Canny(blurred, 30, 200)
    
    # Convert image to HSV color space for color-based detection
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Define range for yellow color in HSV
    lower_yellow = np.array([15, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    
    # Create a mask for yellow color
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    # Apply Canny edge detection on the yellow mask
    edged_yellow = cv2.Canny(mask_yellow, 30, 200)
    
    # Combine edged images from grayscale and yellow mask
    combined_edged = cv2.bitwise_or(edged, edged_yellow)
    
    # Find contours based on the combined edged image
    contours, _ = cv2.findContours(combined_edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours based on area, descending order
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
    
    plates = []
    for cnt in contours:
        # Approximate the contour
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.018 * peri, True)
        
        # Get rotated rectangle
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = np.array(box, dtype=np.int32)
        
        # Get width and height of the rotated rectangle
        width = rect[1][0]
        height = rect[1][1]
        
        # Ensure width is always greater than height
        if height > width:
            width, height = height, width
        
        aspect_ratio = width / float(height)
        
        # More lenient aspect ratio check for tilted plates
        if 1.5 < aspect_ratio < 7:
            angle = rect[2]
            
            # Normalize angle
            if width < height:
                angle = 90 + angle
            
            # Only consider angles within reasonable tilt range (-45 to 45 degrees)
            if -45 <= angle <= 45:
                # Get upright rectangle for region extraction
                x, y, w, h = cv2.boundingRect(cnt)
                
                # Add padding to ensure we capture the full plate
                padding = 5
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(image.shape[1] - x, w + 2 * padding)
                h = min(image.shape[0] - y, h + 2 * padding)
                
                plates.append((x, y, w, h, angle))
    
    return plates

def extract_text_from_image(plate_image, angle=0):
    """
    Extract text from the license plate image using EasyOCR, with rotation correction.
    """
    # Correct the rotation if needed
    if abs(angle) > 5:
        height, width = plate_image.shape[:2]
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        plate_image = cv2.warpAffine(plate_image, rotation_matrix, (width, height),
                                   flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # Convert image to RGB (EasyOCR expects RGB)
    plate_image = cv2.cvtColor(plate_image, cv2.COLOR_BGR2RGB)
    
    # Apply additional preprocessing
    # Increase contrast
    lab = cv2.cvtColor(plate_image, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    enhanced = cv2.merge((cl,a,b))
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
    
    # Use EasyOCR to read text
    result = reader.readtext(enhanced)
    
    # Extract the text results
    plate_texts = [res[1] for res in result if res[2] > 0.5]  # Confidence filtering
    
    # Join texts if multiple detections
    full_text = " ".join(plate_texts).replace(" ", "").upper()
    
    # Basic validation
    if len(full_text) >= 6:
        return full_text
    else:
        return None