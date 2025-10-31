import os
import pickle
import json
import numpy as np
from numpy.linalg import norm
from src.preprocess import preprocess_image
from src.embedding import get_embedding
import pickle

DB_PATH = "face_db.pkl"

def load_database():
    """Loads the face database from a pickle file if it exists."""
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'rb') as f:
            return pickle.load(f)
    return {}

def save_database(db):
    """Saves the face database to a pickle file."""
    with open(DB_PATH, 'wb') as f:
        pickle.dump(db, f)

def build_database_from_photos(photos_dir="data/photos", metadata_path="data/metadata.json"):
    """
    Scans a directory of photos, generates embeddings, and builds the database.
    """
    database = {}
    
    # Load metadata
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Metadata file not found at {metadata_path}. Profiles will have limited info.")
        metadata = {}

    for filename in os.listdir(photos_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(photos_dir, filename)
            
            # Use filename as the key to link to metadata
            person_info = metadata.get(filename, {})
            name = person_info.get("name", os.path.splitext(filename)[0]) # Fallback to filename
            
            print(f"Processing {name}...")
            face_tensor = preprocess_image(image_path)
            
            if face_tensor is not None:
                emb = get_embedding(face_tensor)
                
                # Store the full profile in the database
                database[name] = {
                    "embedding": emb,
                    "age": person_info.get("age", "N/A"),
                    "criminal_record": person_info.get("criminal_record", "N/A"),
                    "photo_path": image_path
                }
    
    return database

def l2_normalize(x, eps=1e-10):
    x = np.asarray(x)
    n = norm(x)
    if n < eps:
        return x
    return x / n


def find_best_match(sketch_embedding, database):
    """Finds the best match for a sketch embedding in the database.

    Returns (name, profile, distance, cosine_similarity)
    - distance: Euclidean (L2) distance (lower is better)
    - cosine_similarity: cosine similarity between normalized vectors (higher is better, typically 0..1)
    """
    best_match_name = None
    best_match_profile = None
    best_dist = float("inf")
    best_cos = -1.0

    # Normalize the sketch embedding once for cosine comparisons
    sketch_emb = np.asarray(sketch_embedding).ravel()
    sketch_norm = l2_normalize(sketch_emb)

    for name, profile in database.items():
        db_emb = np.asarray(profile["embedding"]).ravel()

        # Euclidean distance
        dist = norm(sketch_emb - db_emb)

        # Cosine similarity (on L2-normalized vectors)
        db_norm = l2_normalize(db_emb)
        cos_sim = float(np.dot(sketch_norm, db_norm))

        # Update best by Euclidean distance (primary) and also track best cosine
        if dist < best_dist:
            best_dist = dist
            best_match_name = name
            best_match_profile = profile
            best_cos = cos_sim

    return best_match_name, best_match_profile, best_dist, best_cos


def load_component_database(path='component_db.pkl'):
    """Loads a component (eyes/nose/mouth) database produced by build_component_db.py."""
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
    return {}


def find_best_component_match(sketch_embedding, component_db, part):
    """Finds the best match for a component embedding (e.g., 'eyes', 'nose', 'mouth').

    Returns (name, profile, distance, cosine_similarity)
    """
    best_name = None
    best_profile = None
    best_dist = float('inf')
    best_cos = -1.0

    sketch_emb = np.asarray(sketch_embedding).ravel()
    sketch_norm = l2_normalize(sketch_emb)

    key = f'{part}_embedding'
    for name, parts in component_db.items():
        emb = parts.get(key)
        if emb is None:
            continue
        db_emb = np.asarray(emb).ravel()
        dist = norm(sketch_emb - db_emb)
        db_norm = l2_normalize(db_emb)
        cos_sim = float(np.dot(sketch_norm, db_norm))
        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_profile = parts  # parts contains only component embeddings
            best_cos = cos_sim

    # Try to return profile info (if available in the main DB) - keep minimal
    return best_name, best_profile, best_dist, best_cos