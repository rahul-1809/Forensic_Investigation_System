import os
import cv2
import mediapipe as mp
import numpy as np
import pickle
from PIL import Image
import torch

# Import our existing function for generating embeddings
from src.embedding import get_embedding

# --- Configuration ---
PHOTOS_DIR = 'data/photos'
OUTPUT_DB_PATH = 'component_db.pkl'

# --- Initialize MediaPipe Face Mesh ---
# This model is excellent for finding detailed facial landmarks.
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, min_detection_confidence=0.5)

# --- Define Facial Landmark Indices for Cropping ---
# These specific numbers correspond to points around each feature on the MediaPipe model.
LANDMARK_INDICES = {
    'eyes': [33, 246, 7, 163, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7],
    'nose': [6, 197, 195, 5, 4, 1, 48, 49, 50, 51, 278, 279, 280, 281, 325, 419, 420, 2, 95, 96, 168, 193],
    'mouth': [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
}

def preprocess_component_for_embedding(component_image):
    """
    Prepares a cropped component image (as a PIL Image)
    for the FaceNet embedding model.
    """
    # Resize to the model's expected input size (160x160)
    resized_img = component_image.resize((160, 160))
    
    # Convert PIL image to a PyTorch tensor
    np_img = np.array(resized_img)
    tensor_img = torch.tensor(np_img).permute(2, 0, 1).float() / 255.0
    
    # Add a batch dimension, as the model expects it
    return tensor_img.unsqueeze(0)

def build_database():
    """
    Scans the photos directory, extracts facial components,
    generates an embedding for each, and saves them to a new database file.
    """
    component_database = {}
    print("🚀 Starting component database build...")

    for filename in os.listdir(PHOTOS_DIR):
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue

        person_name = os.path.splitext(filename)[0] # e.g., 'real1'
        image_path = os.path.join(PHOTOS_DIR, filename)
        
        # Read the image with OpenCV and convert to RGB
        image = cv2.imread(image_path)
        # Handle cases where the image file might be corrupted or unreadable
        if image is None:
            print(f"⚠️ Could not read {filename}. Skipping.")
            continue
            
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        results = face_mesh.process(image_rgb)
        
        if not results.multi_face_landmarks:
            print(f"⚠️ Could not find face landmarks in {filename}. Skipping.")
            continue

        print(f"Processing: {person_name}")
        component_database[person_name] = {}
        landmarks = results.multi_face_landmarks[0].landmark
        h, w, _ = image.shape

        # Process each defined component (eyes, nose, mouth)
        for part, indices in LANDMARK_INDICES.items():
            points = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in indices]).astype(int)
            
            # Get a simple bounding box around the component
            x, y, w_box, h_box = cv2.boundingRect(points)
            
            # Crop the component and add some padding to ensure we get the full feature
            padding = 10
            cropped_component = image_rgb[y-padding:y+h_box+padding, x-padding:x+w_box+padding]

            if cropped_component.size == 0:
                print(f"  - Could not crop {part}. Skipping.")
                continue

            try:
                pil_image = Image.fromarray(cropped_component)
            except ValueError as e:
                print(f"  - Error creating PIL image for {part}: {e}. Skipping.")
                continue
            
            # Get the embedding for this specific part
            tensor = preprocess_component_for_embedding(pil_image)
            embedding = get_embedding(tensor)
            
            component_database[person_name][f'{part}_embedding'] = embedding
            print(f"  - Generated embedding for {part}.")

    # Save the final database to a file
    with open(OUTPUT_DB_PATH, 'wb') as f:
        pickle.dump(component_database, f)

    print(f"\n✅ Component database build complete! Saved to {OUTPUT_DB_PATH}")

if __name__ == "__main__":
    build_database()