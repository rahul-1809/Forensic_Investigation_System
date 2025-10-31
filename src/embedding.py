import torch
from facenet_pytorch import InceptionResnetV1

# Load InceptionResnetV1 (pretrained on VGGFace2)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

def get_embedding(face_tensor):
    """
    Generates a 512-dimensional embedding for a given face tensor.
    """
    if face_tensor is None:
        return None
        
    with torch.no_grad():
        # Pass the tensor directly to the model
        embedding = resnet(face_tensor)
        
    return embedding.cpu().numpy()