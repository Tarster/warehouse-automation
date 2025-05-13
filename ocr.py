import cv2
import re
import numpy as np
from easyocr import Reader

easyreader = Reader(['en'], gpu=True, model_storage_directory='/Users/karanrnair/Desktop/XODE/AtlanTech AI Challenge/easyocrmodels')

image = cv2.imread(r'/Users/karanrnair/XODE/AtlanTech AI Challenge/t1.jpeg')

ocrdimage = easyreader.readtext(image, paragraph=True, decoder='wordbeamsearch',
                                width_ths=2.0, height_ths=0.2)

def visualize_easyocr_boxes(image, ocr_results):
    img = image.copy()
    
    for box_data in ocr_results:
        # Extract quadrilateral coordinates and text
        quadrilateral = box_data[0]
        text = box_data[1]
        
        # Convert coordinates to numpy array
        pts = np.array(quadrilateral, dtype=np.int32).reshape((-1, 1, 2))
        
        # Draw bounding box
        cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
        
        # Optional: Add text label
        cv2.putText(img, text, tuple(pts[0][0]), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
    
    return img

# Assuming 'results' contains your OCR output
annotated_image = visualize_easyocr_boxes(image, ocrdimage)
cv2.imwrite("annotated_output.jpg", annotated_image)