import cv2
import re
from easyocr import Reader

easyreader = Reader(['en'], gpu=True, model_storage_directory='/Users/karanrnair/Desktop/XODE/AtlanTech AI Challenge/easyocrmodels')

image = cv2.imread(r'/Users/karanrnair/Desktop/XODE/AtlanTech AI Challenge/WhatsApp Image 2025-05-03 at 9.29.50 p.m..jpeg')

ocrdimage = easyreader.readtext(image, detail=0, paragraph=True, decoder='wordbeamsearch',
                                width_ths=2.0)

predef_labels = ['Part:', 'Receipt:', 'Customer:', 'Lot:', 'Quantity']

results = {}

# Pattern to match "Label: value" or "Label   value"
pattern = re.compile(r'(Part:|Receipt:|Customer:|Lot:|Quantity)[:\s]+([^\s].*?)(?=\s+[A-Z][a-z]+:|$)', re.IGNORECASE)

for line in ocrdimage:
    matches = pattern.findall(line)
    for label, value in matches:
        results[label.strip(':').capitalize()] = value.strip()

# Print extracted fields
for label in predef_labels:
    key = label.strip(':').capitalize()
    if key in results:
        print(f"{key}: {results[key]}")