from src.preprocess import preprocess_image
from src.embedding import get_embedding
from src.database import find_best_match

def recognize_sketch(sketch_path, database):
    """
    Recognizes a sketch by comparing it against the provided database.
    """
    sketch_face = preprocess_image(sketch_path)
    if sketch_face is None:
        return None, None, None
    
    sketch_emb = get_embedding(sketch_face)
    name, profile, dist, cos_sim = find_best_match(sketch_emb, database)

    return name, profile, dist, cos_sim