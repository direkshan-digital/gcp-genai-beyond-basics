from typing import Optional, List, Iterable, Any

from google.cloud.firestore_v1 import CollectionReference, Client
from google.cloud.firestore_v1.base_query import BaseFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from langchain_core.embeddings import Embeddings
from langchain_google_firestore import FirestoreVectorStore


class ImageEnabledFirestoreVectorStore(FirestoreVectorStore):
    """Extends FirestoreVectorStore to add image handling capabilities."""

    def __init__(self,
                 collection: CollectionReference | str,
                 embedding_service: Embeddings,
                 client: Optional[Client] = None,
                 content_field: str = "content",
                 metadata_field: str = "metadata",
                 embedding_field: str = "embedding",
                 distance_strategy: Optional[DistanceMeasure] = DistanceMeasure.COSINE,
                 filters: Optional[BaseFilter] = None
                 ):
        super().__init__(collection, embedding_service, client, content_field,
                         metadata_field, embedding_field, distance_strategy, filters)

    def add_images(
            self,
            image_paths: Iterable[str],
            metadatas: Optional[List[dict]] = None,
            ids: Optional[List[str]] = None,
            **kwargs: Any,
    ) -> List[str]:
        """Adds image embeddings to Firestore vector store.

        Args:
            image_paths: A list of image paths (local, Google Cloud Storage or web)
            metadatas: The metadata to add to the vector store. Defaults to None.
            ids: The document ids to use for the new documents. If not provided, new
            document ids will be generated.

        Returns:
            List[str]: The list of document ids added to the vector store.
        """
        images_len = len(list(image_paths))
        ids_len_match = not ids or len(ids) == images_len
        metadatas_len_match = not metadatas or len(metadatas) == images_len

        if images_len == 0:
            raise ValueError("No images provided to add to the vector store.")

        if not metadatas_len_match:
            raise ValueError(
                "The length of metadatas must be the same as the length of images or zero."
            )

        if not ids_len_match:
            raise ValueError(
                "The length of ids must be the same as the length of images or zero."
            )

        _ids: List[str] = []
        db_batch = self.client.batch()

        for i, image_path in enumerate(image_paths):
            image_embs = self.embedding_service.embed_image(image_path)  # TODO: Set contextual_text too?
            doc_id = ids[i] if ids else None
            doc = self.collection.document(doc_id)
            _ids.append(doc.id)

            data = {
                self.content_field: "",
                self.embedding_field: Vector(image_embs),
                self.metadata_field: metadatas[i] if metadatas else None,
            }

            db_batch.set(doc, data, merge=True)

        db_batch.commit()
        return _ids
