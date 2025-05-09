import cv2
from easyocr import Reader

easyreader = Reader(['en'], gpu=True)

image = cv2.imread(r'/Users/karanrnair/Desktop/XODE/AtlanTech AI Challenge/WhatsApp Image 2025-05-03 at 9.28.59 p.m..jpeg')

ocrdimage = easyreader.readtext(image)

for (box, text, probs) in ocrdimage:
    print(text)