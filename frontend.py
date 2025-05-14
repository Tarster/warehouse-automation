import streamlit as st
from backend import LabelDetector
from PIL import ImageOps, Image
from utility import utilClass
import os
@st.cache_resource
def load_model():
    # Load the model
    detector = LabelDetector(utilClass())
    return detector

st.title("Warehouse Automation")
# Make a simple form that accepts a file upload which is a single image
uploaded_file = st.file_uploader("Choose an image...", type="jpg")  # 50MB limit
process_image = st.button("Process Image", key="process_image")
if uploaded_file is not None and process_image:

    # To read file as bytes:
    bytes_data = uploaded_file.read()
    
    # Save the uploaded file to a temporary location
    path = r""
    new_path = os.path.join(path, "temp_image.jpg")
    print(new_path)
    with open(new_path, "wb") as f:
        f.write(bytes_data)

    image = Image.open(new_path)
    image = ImageOps.exif_transpose(image)
    st.image(image, caption='Uploaded Image.', use_container_width =True)
    st.success("Image saved successfully!")
    # Now you can use the saved image for further processing
    # Initialize the LabelDetector
    detector = load_model()

    # Detect labels in the uploaded image
    result = detector.detect_labels(new_path)
    st.image("cropped_0_0_LN_label.jpg", caption='Cropped LN Label', use_container_width=True)
    st.image("cropped_0_1_WH_label.jpg", caption='Cropped WH Label', use_container_width=True)
    # Display the results
    for result_line in result:
        st.write(result_line)