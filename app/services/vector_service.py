"""
Vector Database Service for Ticket Embeddings
Handles ticket embeddings generation and vector storage/retrieval in Qdrant
"""

import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os

logger = logging.getLogger(__name__)


class VectorService:
    """Service for managing ticket embeddings and vector search with Qdrant"""

    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.qdrant_url = qdrant_url
        self.client: Optional[QdrantClient] = None
        self.openai_client: Optional[OpenAI] = None
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimensions = 1536

        # Collection names
        self.TICKETS_COLLECTION = "support_tickets"
        self.KNOWLEDGE_BASE_COLLECTION = "knowledge_base"

    async def initialize(self):
        """Initialize Qdrant client and OpenAI client"""
        try:
            # Initialize Qdrant client
            self.client = QdrantClient(url=self.qdrant_url)
            logger.info(f"✅ Connected to Qdrant at {self.qdrant_url}")

            # Test connection
            collections = self.client.get_collections()
            logger.info(f"📊 Qdrant collections: {[c.name for c in collections.collections]}")

            # Initialize OpenAI client for embeddings
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info(f"✅ OpenAI client initialized for embeddings")
            else:
                logger.warning("⚠️  OpenAI API key not found - embeddings disabled")

            # Create collections if they don't exist
            await self._create_collections()

            return True

        except Exception as e:
            logger.error(f"❌ Error initializing Vector Service: {e}")
            return False

    async def _create_collections(self):
        """Create Qdrant collections if they don't exist"""
        try:
            existing_collections = [c.name for c in self.client.get_collections().collections]

            # Create support_tickets collection
            if self.TICKETS_COLLECTION not in existing_collections:
                self.client.create_collection(
                    collection_name=self.TICKETS_COLLECTION,
                    vectors_config=VectorParams(
                        size=self.embedding_dimensions,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created collection: {self.TICKETS_COLLECTION}")
            else:
                logger.info(f"📊 Collection already exists: {self.TICKETS_COLLECTION}")

            # Create knowledge_base collection
            if self.KNOWLEDGE_BASE_COLLECTION not in existing_collections:
                self.client.create_collection(
                    collection_name=self.KNOWLEDGE_BASE_COLLECTION,
                    vectors_config=VectorParams(
                        size=self.embedding_dimensions,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created collection: {self.KNOWLEDGE_BASE_COLLECTION}")
            else:
                logger.info(f"📊 Collection already exists: {self.KNOWLEDGE_BASE_COLLECTION}")

        except Exception as e:
            logger.error(f"❌ Error creating collections: {e}")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            if not self.openai_client:
                raise Exception("OpenAI client not initialized")

            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            return []

    async def add_ticket(
        self,
        ticket_id: str,
        subject: str,
        description: str,
        classification: Dict[str, Any]
    ) -> bool:
        """
        Add a classified ticket to the vector database

        Args:
            ticket_id: Unique ticket ID
            subject: Ticket subject
            description: Ticket description
            classification: Classification results (urgency, intent, product, confidence)
        """
        try:
            # Generate combined text for embedding
            combined_text = f"{subject}\n\n{description}"
            embedding = self.generate_embedding(combined_text)

            if not embedding:
                return False

            # Create unique point ID
            point_id = abs(hash(ticket_id)) % (10 ** 10)

            # Prepare payload
            payload = {
                "ticket_id": ticket_id,
                "subject": subject,
                "description": description,
                "urgency": classification.get("urgency"),
                "intent": classification.get("intent"),
                "product": classification.get("product"),
                "confidence": classification.get("confidence"),
                "reasoning": classification.get("reasoning")
            }

            # Upsert to Qdrant
            self.client.upsert(
                collection_name=self.TICKETS_COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )

            logger.info(f"✅ Added ticket to vector DB: {ticket_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error adding ticket to vector DB: {e}")
            return False

    async def search_similar_tickets(
        self,
        query: str,
        limit: int = 5,
        urgency_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Find tickets similar to the query

        Args:
            query: Search query text
            limit: Maximum number of results
            urgency_filter: Optional filter by urgency level
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)

            if not query_embedding:
                return []

            # Build filter if needed
            query_filter = None
            if urgency_filter:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="urgency",
                            match=MatchValue(value=urgency_filter)
                        )
                    ]
                )

            # Search for similar tickets
            search_results = self.client.search(
                collection_name=self.TICKETS_COLLECTION,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
                with_payload=True
            )

            # Format results
            results = []
            for hit in search_results:
                results.append({
                    "similarity_score": hit.score,
                    "ticket_id": hit.payload.get("ticket_id"),
                    "subject": hit.payload.get("subject"),
                    "description": hit.payload.get("description"),
                    "urgency": hit.payload.get("urgency"),
                    "intent": hit.payload.get("intent"),
                    "product": hit.payload.get("product"),
                    "confidence": hit.payload.get("confidence")
                })

            logger.info(f"🔍 Found {len(results)} similar tickets")
            return results

        except Exception as e:
            logger.error(f"❌ Error searching similar tickets: {e}")
            return []

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about collections"""
        try:
            tickets_info = self.client.get_collection(self.TICKETS_COLLECTION)
            kb_info = self.client.get_collection(self.KNOWLEDGE_BASE_COLLECTION)

            return {
                "tickets_count": tickets_info.points_count,
                "knowledge_base_count": kb_info.points_count,
                "total_vectors": tickets_info.points_count + kb_info.points_count
            }

        except Exception as e:
            logger.error(f"❌ Error getting collection stats: {e}")
            return {"tickets_count": 0, "knowledge_base_count": 0, "total_vectors": 0}


# Global instance
vector_service = VectorService()
