import logging
import threading
from typing import List, Union, Optional
import numpy as np

logger = logging.getLogger(__name__)

_model_lock = threading.Lock()
_text_model_instance = None
_visual_model_instance = None
_clip_available = None


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """Normalize vectors to unit length for exact cosine similarity with inner product."""
    if len(vectors.shape) == 1:
        vectors = vectors.reshape(1, -1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype("float32")


class EmbeddingEngine:
    """
    Singleton Embedding Engine for LENS.
    Reuses models across all indexing and search operations.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with _model_lock:
                if not cls._instance:
                    cls._instance = super(EmbeddingEngine, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if getattr(self, "_initialized", False):
            return
        self.model_name = model_name
        self._text_model = None
        self._initialized = True

    @property
    def text_model(self):
        if self._text_model is None:
            with _model_lock:
                if self._text_model is None:
                    from sentence_transformers import SentenceTransformer
                    logger.info(f"Loading SentenceTransformer: {self.model_name}")
                    self._text_model = SentenceTransformer(self.model_name)
        return self._text_model

    def encode_texts(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        """
        Encode a list of text strings into normalized 384-dimensional embeddings.
        """
        if not texts:
            return np.empty((0, 384), dtype="float32")

        cleaned = [t if t.strip() else "empty document" for t in texts]
        embeddings = self.text_model.encode(
            cleaned,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return normalize_vectors(np.array(embeddings, dtype="float32"))

    def encode_query(self, query: str) -> np.ndarray:
        """
        Encode a single search query into a normalized 1D or 2D vector.
        """
        if not query.strip():
            query = "empty"
        emb = self.text_model.encode([query], show_progress_bar=False, convert_to_numpy=True)
        return normalize_vectors(np.array(emb, dtype="float32"))

    def encode_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Encode an image using CLIP if available, or generate visual embedding from image metadata.
        """
        global _clip_available, _visual_model_instance
        try:
            from PIL import Image
            img = Image.open(image_path).convert("RGB")
            
            # Check if clip is available
            if _clip_available is not False:
                try:
                    if _visual_model_instance is None:
                        from sentence_transformers import SentenceTransformer
                        # Use clip-ViT-B-32 for visual embeddings if possible
                        logger.info("Initializing visual CLIP model...")
                        _visual_model_instance = SentenceTransformer("clip-ViT-B-32")
                        _clip_available = True
                    
                    emb = _visual_model_instance.encode(img, show_progress_bar=False, convert_to_numpy=True)
                    return normalize_vectors(np.array(emb, dtype="float32"))
                except Exception as clip_err:
                    logger.info(f"CLIP model not available or download failed: {clip_err}. Using text embedding fallback.")
                    _clip_available = False

            # Fallback: create descriptive text from image properties and encode via text_model
            desc = f"Image {img.filename or ''} size {img.width}x{img.height} format {img.format}"
            return self.encode_query(desc)
        except Exception as e:
            logger.warning(f"Failed to encode image {image_path}: {e}")
            return None


def get_embedding_engine() -> EmbeddingEngine:
    return EmbeddingEngine()
