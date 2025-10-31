import torch
from facenet_pytorch import MTCNN
from PIL import Image

# Device setup
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Initialize MTCNN
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, device=device)

def preprocess_image(image_path):
    """Load image, detect & align face using MTCNN."""
    img = Image.open(image_path).convert('RGB')
    face = mtcnn(img)
    if face is None:
        print(f"⚠️ No face detected in {image_path}")
        return None
    return face.unsqueeze(0).to(device)  # Add batch dimension


def preprocess_component_image(image_path):
    """Preprocess a single-component image (eye/nose/mouth).

    This resizes the image to 160x160 and converts it to the same tensor
    shape the embedding model expects: (1, 3, 160, 160) on the correct device.
    """
    img = Image.open(image_path).convert('RGB')
    img = img.resize((160, 160))
    # Convert to tensor in the same scale used elsewhere (0..1)
    np_img = __import__('numpy').array(img)
    import torch as _torch
    tensor_img = _torch.tensor(np_img).permute(2, 0, 1).float() / 255.0
    return tensor_img.unsqueeze(0).to(device)
