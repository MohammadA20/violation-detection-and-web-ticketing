# Traffic Violation Detection System

A computer vision–based system that analyzes CCTV footage to detect traffic violations in real time. The system identifies over-speeding vehicles, drivers without seatbelts, motorcyclists without helmets, mobile phone usage while driving, and extracts license plate numbers. Detected violations are automatically sent to a web dashboard for monitoring and enforcement.

## Features
- Speed estimation
- Helmet detection
- Seatbelt detection
- Mobile phone usage detection
- License plate recognition

## How It Works
1. CCTV camera captures live or recorded video.
2. Video frames are analyzed using deep learning and computer vision models.
3. Violations are detected and logged with images, timestamps, and license plates.
4. Reports are sent to a web platform for review.

## Technologies
- Python, OpenCV, PyTorch/TensorFlow
- YOLO/CNN models for object detection
- OCR for license plate recognition
- TypeScript/Node.js/React for web dashboard

## Installation
```bash
git clone https://github.com/your-username/traffic-violation-detection.git
cd traffic-violation-detection
python -m venv venv
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate       # Windows
pip install -r requirements.txt

# Web dashboard
cd web
npm install
