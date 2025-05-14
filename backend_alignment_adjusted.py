import os 
import cv2
from ultralytics import YOLO
import requests
import base64
from paddleocr import PaddleOCR
from typing import List, Dict, Any
import json
from alignment import align_image

class LabelDetector:
    def __init__(self, detector_model_path='/Users/karanrnair/XODE/AtlanTech AI Challenge/best.pt', ocr_model_path='ocr_model.pt'):
        self.model_path = detector_model_path
        self.ocr_model_path = ocr_model_path
        self.api_key = 'AIzaSyCHpnXqrIc1lC95p9iQdlc6ufZ9MglSgc4'
        self.load_models()
        self.img_count = 0
        self.paddle_model = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False)
        self.prompt ="""
            Extract all relevant data from this image and return it in a structured JSON format.
            Return only the JSON data without any additional text or markdown formatting.
            """
        # self.load_ocr_model()
        
    def load_models(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file {self.model_path} not found.")
        # Load the label detection model
        self.detector_model = YOLO(self.model_path)
        print(f"Loaded model from {self.model_path}")

    def detect_labels(self, image_path):
        image_obj = cv2.imread(image_path)
        # Predict with the model
        results = self.detector_model(image_path)  # predict on an image

        # Access the results
        final_dict = {}
        for i, result in enumerate(results):
            xyxy = result.boxes.xyxy  # top-left-x, top-left-y, bottom-right-x, bottom-right-y
            names = [result.names[cls.item()] for cls in result.boxes.cls.int()]  # class name of each box
            # Loop through each detection
            for j, (box, name) in enumerate(zip(xyxy, names)):
                if name == 'LN_label':
                    print(f"Detected label: {name}")
                    # Save the image that is in the bounding boxes
                    cropped_image = self.crop_image(image_obj, box)
                    align_rectified_image =  align_image(cropped_image, name)
                    cv2.imwrite(f"cropped_{self.img_count}_{name}.jpg", align_rectified_image)
                    result = self.ocr_gemini(f"cropped_{self.img_count}_{name}.jpg")
                    # print("LN_TYPE", type(result))
                    # if "product_code" in result:
                    #     final_dict['loc'] = result["product_code"]
                elif name == 'WH_label':
                    print(f"Detected label: {name}")
                    cropped_image = self.crop_image(image_obj, box)
                    cv2.imwrite(f"skewed_{self.img_count}_{name}.jpg", cropped_image)
                    align_rectified_image =  align_image(cropped_image, name)
                    cv2.imwrite(f"rectified_{self.img_count}_{name}.jpg", align_rectified_image)
                    result = self.ocr_gemini(f"rectified_{self.img_count}_{name}.jpg")
                    # for key, value in result.items():
                    #     if key.lower() in ['part', 'lot', 'quantity']:
                    #         final_dict[key] = value
                self.img_count += 1
        return final_dict

    # PART: LOT :QUANTITY

    def extract_data_from_images(self, image_path):
        """
        Extract data from images using the Gemini API.
        
        Args:
            api_key: Your Gemini API key
            image_paths: List of paths to image files
            prompt: The prompt instructing what data to extract
        Returns:
            Dictionary containing the API response
        """
        
        # Gemini API endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        
        # Read and encode the image
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        # Create content part for this image
        content = {
            "parts": [
                {
                    "text": self.prompt
                },
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",  # Adjust if using PNG or other formats
                        "data": encoded_image
                    }
                }
            ]
        }
        
        # Create the full request payload
        payload = {
            "contents": content,
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }
        
        # Make the API request
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")        
        return response.json()
    
    def crop_image(self, image, box):
        # Convert tensor to numpy array and get coordinates
        box = box.cpu().numpy()  # if box is on GPU, move to CPU first
        x1, y1, x2, y2 = box
        return image[int(y1):int(y2), int(x1):int(x2)]

    def ocr_gemini(self, image_path):
        try:
            # image = cv2.imread(image_path)
            result = self.paddle_model.ocr(image_path, rec=True, det=True, cls=False)
            print(result)








        #     result = self.extract_data_from_images(image_path)
        #     # Extract and parse the JSON content from the response
        #     if "candidates" in result and len(result["candidates"]) > 0:
        #         content = result["candidates"][0]["content"]
        #         if "parts" in content and len(content["parts"]) > 0:
        #             text_response = content["parts"][0]["text"]
        #             # Try to parse the JSON if the response is in JSON format
        #             try:
        #                 extracted_data = json.loads(text_response)
        #                 print("\nExtracted Data:")
        #                 print(json.dumps(extracted_data, indent=2))
        #                 # convert to dict 
        #                 return extracted_data
        #             except json.JSONDecodeError:
        #                 print("\nText Response (might not be JSON):")
        #                 print(text_response)
        except Exception as e:
            print(f"Error: {str(e)}")
            pass

if __name__ == "__main__":
    detector = LabelDetector()
    print("Label detector initialized.")
    detector.detect_labels(r"/Users/karanrnair/XODE/AtlanTech AI Challenge/1.jpeg")
    