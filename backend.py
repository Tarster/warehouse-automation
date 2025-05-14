import os 
import cv2
from ultralytics import YOLO
import requests
import base64
import json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser


# Load .env file
load_dotenv(r".env")

class modelop(BaseModel):
    """
    This class is used to define the structure of the output data in JSON format.
    """
    location: str = Field(description="Location value: Only to be extracted when the label is LN_label")
    partCode: str = Field(description="Part code value extracted from the image: Only to be extracted when the label is WH_label")
    lot: str = Field(description="Lot code value extracted from the image: Only to be extracted when the label is WH_label")
    quantity: str = Field(description="Quantity value extracted from the image: : Only to be extracted when the label is WH_label")

parser = PydanticOutputParser(pydantic_object=modelop)

# print(parser.get_format_instructions())

class LabelDetector():
    def __init__(self, util_model, detector_model_path='label_detector.pt', ocr_model_path='ocr_model.pt'):
        self.model_path = detector_model_path
        self.ocr_model_path = ocr_model_path
        self.api_key = os.getenv("API_KEY")
        self.username = os.getenv("USERNAME_ID")
        self.password = os.getenv("PASSWORD")
        self.server_url = os.getenv("SERVER_URL")
        self.location_code = None
        self.ln_label = False
        self.wh_label = False
        self.util_obj = util_model
        # print(f"API_KEY: {self.api_key}", f"USERNAME: {self.username}", f"PASSWORD: {self.password}", f"SERVER_URL: {self.server_url}")
        if not self.api_key or not self.username or not self.password:
            raise ValueError("API_KEY not found in environment variables.")
        self.load_models()
        self.prompt =f"""
            You are a data extraction model. Your task is to extract relevant information from the image.
            The extracted information should include:
            {parser.get_format_instructions()}
            """
        # self.load_ocr_model()

    def call_api(self):
        params = {"locationCode": self.location_code}
        auth = HTTPBasicAuth(self.username, self.password)
        response = requests.get(self.server_url, params=params, auth=auth)
        if response.status_code == 200:
            final_dict = {}
            json_response = response.json()
            try:
                # Extract the relevant data from the JSON response
                for item in json_response[0].keys():
                    if item in ['partCode', 'lot']:
                        final_dict[item] = json_response[0][item]
                return final_dict
            except (KeyError, IndexError) as e:
                print(f"Error extracting data from response: {e}")
                return "no_data"
        else:
            return None

    def load_models(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file {self.model_path} not found.")
        # Load the label detection model
        self.detector_model = YOLO(self.model_path)
        print(f"Loaded model from {self.model_path}")
    
    def reset_data(self):
        self.location_code = None
        self.ln_label = False
        self.wh_label = False
        self.api_dict = None

    def detect_labels(self, image_path):
        image_obj = cv2.imread(image_path)
        # Predict with the model
        results = self.detector_model(image_path)  # predict on an image
        # Reset the data
        self.reset_data()
        # Access the results
        final_dict = {}
        for i, result in enumerate(results):
            xyxy = result.boxes.xyxy  # top-left-x, top-left-y, bottom-right-x, bottom-right-y
            names = [result.names[cls.item()] for cls in result.boxes.cls.int()]  # class name of each box
            # Loop through each detection
            for j, (box, name) in enumerate(zip(xyxy, names)):
                if name == 'LN_label':
                    print(f"Detected label: {name}")
                    self.ln_label = True
                    # Save the image that is in the bounding boxes
                    cropped_image = self.crop_image(image_obj, box)
                    cv2.imwrite(f"cropped_{i}_{j}_{name}.jpg", cropped_image)
                    # Call the OCR model
                    paddle_result = self.ocr_paddle(f"cropped_{i}_{j}_{name}.jpg", name)
                    if paddle_result['location'] is not None:
                        self.location_code = paddle_result["location"]
                    else:        
                        # If the OCR model fails, use the Gemini API
                        print("Paddle OCR failed, using Gemini API.")
                        result = self.ocr_gemini(f"cropped_{i}_{j}_{name}.jpg", name)
                        if result["location"] is not None:
                            self.location_code = result["location"]
                    if self.location_code is None:
                        return ["❌ No Location label is found."]
                
                elif name == 'WH_label':
                    if self.location_code is None:
                        return ["❌ No Location label is found."]
                    flag = False
                    print(f"Detected label: {name}")
                    self.wh_label = True
                    cropped_image = self.crop_image(image_obj, box)
                    cv2.imwrite(f"cropped_{i}_{j}_{name}.jpg", cropped_image)
                    
                    paddle_result = self.ocr_paddle(f"cropped_{i}_{j}_{name}.jpg", name)
                    
                    if paddle_result is not None:
                        result = self.compare_labels(paddle_result)
                        # print(f"result: {result}")
                        if result == "api_error":
                            return ["❌ API error occurred. Lost connection to the server."]
                        elif result == "no_loc":
                            return ["❌ No location code found in the image."]
                        elif result == "no_data":
                            return ["❌ No data found for the given location code."]
                        elif result == "mismatch":
                            flag = True
                    else:
                        flag = True       
                    # Finally call the Gemini API, if the paddle OCR fails or the data is not found
                    if flag:
                        result = self.ocr_gemini(f"cropped_{i}_{j}_{name}.jpg", name)
                        for key, value in result.items():
                            if key.lower() in ['partcode', 'lot', 'quantity']:
                                final_dict[key] = value
                        result = self.compare_labels(final_dict, caller='gemini')
                        flag = False
                    return result
                else:
                    return ["❌ Unknown label detected."]
    def compare_labels(self, comparison_dict, caller='paddle'):
        # Call the API to get the data
        if self.api_dict is None:
            self.api_dict = self.call_api()    
            if self.api_dict is None:
                return "api_error"
            elif self.api_dict == "no_data":
                return "no_data"
        
        display_list = []
        for key, value in self.api_dict.items():
            if key.lower() in ['partcode', 'lot', 'quantity']:
                # Compare the values
                if comparison_dict[key] == value:
                    display_list.append(f"✅ {key}: {value} (Match with OCR result)")    
                else:
                    if caller == 'paddle':
                        return "mismatch"
                    display_list(f"❌ {key}: {value} (Mismatch with OCR result)")
        
        return display_list
            

    def extract_data_from_images(self, image_path, name):
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
                    "text": self.prompt + f" Extract Based on label {name}"
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
    
    def ocr_paddle(self, image_path, name):
        try:
            # read the image
            image = cv2.imread(image_path)
            aligned_image = self.util_obj.align_image(image)
            #save the aligned image
            result = self.util_obj.ret_bounding_box(aligned_image, name=name)
            
            # Check if the data is correct
            if name == 'LN_label':
                # check if LN label is detected
                if result['location'] is not None:
                    return result
                else:
                    return None
            if name == 'WH_label':
                # check if WH label is detected
                if result['partCode'] is not None and result['lot'] is not None and result['quantity'] is not None:
                    del result['location']
                    return result
                else:
                    return None
        except Exception as e:
                print(f"Error: {str(e)}")
    
    def ocr_gemini(self, image_path, name):
        try:
            result = self.extract_data_from_images(image_path, name)
            # Extract and parse the JSON content from the response
            if "candidates" in result and len(result["candidates"]) > 0:
                content = result["candidates"][0]["content"]
                if "parts" in content and len(content["parts"]) > 0:
                    text_response = content["parts"][0]["text"]
                    # Try to parse the JSON if the response is in JSON format
                    try:
                        extracted_data = json.loads(text_response)
                        print("\nExtracted Data:")
                        print(json.dumps(extracted_data, indent=2))
                        # convert to dict 
                        return extracted_data
                    except json.JSONDecodeError:
                        print("\nText Response (might not be JSON):")
                        print(text_response)
        except Exception as e:
                print(f"Error: {str(e)}")
                

if __name__ == "__main__":
    detector = LabelDetector()
    print("Label detector initialized.")
    print(detector.detect_labels(r"Data/Test_Images/IMG_0305.JPG"))
    