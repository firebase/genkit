
import math

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculates the cosine similarity between two vectors."""
    if len(v1) != len(v2):
        raise ValueError("Vectors must have the same length")

    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))

    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0

    return dot_product / (norm_v1 * norm_v2)
