import cv2
import numpy as np
from easyocr import Reader
from paddleocr import PaddleOCR

Paddle = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, show_log=False)

def crop_image(detections, image):
    cropped_images=[]
    for box, _ in detections:
        x, y, w, h = cv2.boundingRect(np.array(box, dtype=np.int32))
        cropped_images.append(image[y:y+h, x:x+w])
    return cropped_images

def ret_bounding_box(image, ocr_model_path='./easyocr_model'):
    easyreader = Reader(['en'], gpu=True, model_storage_directory=ocr_model_path)
    detections = easyreader.readtext(image, paragraph=True, decoder='wordbeamsearch', width_ths=2.0, height_ths=0.2)

    detected_subimages = crop_image(detections, image)
    map_dictionary = {'Part': 'partCode', 'Lot': 'lot', 'Quantity': 'quantity'}
    return_dictionary = {}

    for sub_images in detected_subimages:
        result = Paddle.ocr(sub_images, rec=True, det=False, cls=False)
        context = result[0][0][0]
        if ':' in context:
            key, value = context.split(':')
            return_dictionary[key] = value

    return return_dictionary

def align_image(image, name:str):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    
    otsu_thresh, _ = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    lower = 0.5 * otsu_thresh
    upper = otsu_thresh
    
    edges = cv2.Canny(blur, lower, upper)
    
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image
    
    largest_contour = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(largest_contour)
    (center_x, center_y), (width, height), angle = rect

    # Drawing Part optional
    # # box = cv2.boxPoints(rect)
    # # box = np.int64(box)
    # 
    # # boxed_image = image.copy()
    # # cv2.drawContours(boxed_image, [box], 0, (0, 255, 0), 2)

    # cv2.imshow("boxed_image", boxed_image)
    # cv2.imshow("cannny", edges)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    
    (h, w) = image.shape[:2]
    image_center = (w//2, h//2)
    
    tx, ty = image_center[0] - center_x, image_center[1] - center_y
    
    translation_matrix = np.float32([
        [1,0,tx],
        [0,1,ty]
        ])
    translated = cv2.warpAffine(image, translation_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    if angle > 45:
        angle = -(90 - angle)

    rotation_matrix = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    rotated = cv2.warpAffine(translated, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return rotated