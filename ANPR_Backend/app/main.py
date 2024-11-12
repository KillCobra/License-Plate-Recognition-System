# app/main.py
import os
import shutil
import cv2
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from app.anpr import recognize_license_plate_from_image, recognize_license_plate_from_video, recognize_license_plate_from_frame
import asyncio
from fastapi import WebSocketDisconnect

app = FastAPI(
    title="Automatic Number Plate Recognition API",
    description="API for uploading images or videos to detect and recognize license plates.",
    version="1.0.0"
)

# CORS settings
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5500",  # Added frontend origin
    # Add other origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Update as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to store uploaded files temporarily
UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint to handle image or video uploads for license plate recognition.
    """
    filename = file.filename
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Save the uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Determine file type and process accordingly
    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension in [".jpg", ".jpeg", ".png"]:
        try:
            results = recognize_license_plate_from_image(file_path)
            os.remove(file_path)  # Clean up
            return JSONResponse(content={"filename": filename, "results": results})
        except Exception as e:
            os.remove(file_path)
            raise HTTPException(status_code=500, detail=str(e))
    elif file_extension in [".mp4", ".avi", ".mov", ".mkv"]:
        try:
            results = recognize_license_plate_from_video(file_path)
            os.remove(file_path)
            return JSONResponse(content={"filename": filename, "results": results})
        except Exception as e:
            os.remove(file_path)
            raise HTTPException(status_code=500, detail=str(e))
    else:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload an image or video file.")

@app.websocket("/live/")
async def live_camera(websocket: WebSocket):
    """
    WebSocket endpoint to stream live camera feed and send detected license plate details.
    """
    await websocket.accept()
    print("WebSocket connection accepted")
    
    # Initialize camera with a higher resolution
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        await websocket.send_json({"error": "Could not access the camera."})
        await websocket.close()
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                await websocket.send_json({"error": "Failed to read from camera."})
                break

            # Process the frame to detect license plates
            results = recognize_license_plate_from_frame(frame)
            
            # Always send a response, whether plates are detected or not
            if results:
                await websocket.send_json({"status": "success", "results": results})
            else:
                await websocket.send_json({"status": "scanning", "message": "No plates detected"})
            
            # Add a small delay to prevent overwhelming the connection
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in WebSocket: {str(e)}")
        await websocket.send_json({"error": str(e)})
    finally:
        cap.release()
        await websocket.close()