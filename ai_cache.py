"""
AI Response Caching System for PhysiologicPRISM

This module implements intelligent caching of Azure OpenAI API responses to:
1. Reduce API costs by reusing responses for similar queries
2. Speed up response times for cached queries
3. Build a knowledge base for future LLM training
4. Track AI usage patterns and effectiveness

All cached data is PHI-safe (sanitized before storage).
Now using Azure Cosmos DB (HIPAA BAA compliant).
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Azure Cosmos DB (replaces Firebase Firestore)
from azure_cosmos_db import SERVER_TIMESTAMP

logger = logging.getLogger("app.ai_cache")


class AICache:
    """
    Manages AI response caching in Azure Cosmos DB.

    Collections:
    - ai_cache: Stores cached responses
    - ai_analytics: Tracks cache performance metrics
    - ai_training_data: Stores training data for future improvements
    """

    def __init__(self, db):
        """
        Initialize the AI cache.

        Args:
            db: Cosmos DB client instance
        """
        self.db = db
        self.cache_collection = 'ai_cache'
        self.analytics_collection = 'ai_analytics'
        self.training_data_collection = 'ai_training_data'

        # Cache configuration
        self.cache_ttl_days = 90  # Cache expires after 90 days
        self.enable_semantic_matching = False  # Future: match similar prompts


    def _generate_cache_key(self, prompt: str, model: str = "gpt-4o", patient_context: str = "") -> str:
        """
        Generate a unique cache key for a prompt.

        Uses SHA-256 hash of prompt + model name + patient context.

        Args:
            prompt: The sanitized prompt text
            model: The AI model name (e.g., "gpt-4o")
            patient_context: Patient-specific context (age/sex demographics) to ensure unique responses per patient profile

        Returns:
            str: Hexadecimal hash suitable as Cosmos DB document ID
        """
        # For patient-specific queries, do NOT normalize to preserve uniqueness
        # Only normalize the prompt structure, keep patient data intact
        if patient_context:
            # Include patient context to ensure different patients get different cache entries
            cache_input = f"{model}:{prompt}:{patient_context}"
        else:
            # For generic queries, normalize to improve cache hit rate
            normalized = ' '.join(prompt.lower().strip().split())
            cache_input = f"{model}:{normalized}"

        # Generate SHA-256 hash
        hash_obj = hashlib.sha256(cache_input.encode('utf-8'))
        return hash_obj.hexdigest()


    def get_cached_response(self, prompt: str, model: str = "gpt-4o", patient_context: str = "") -> Optional[str]:
        """
        Retrieve a cached AI response if available and not expired.

        Args:
            prompt: The sanitized prompt text
            model: The AI model name
            patient_context: Patient-specific context for cache key uniqueness

        Returns:
            str: Cached response text, or None if not found/expired
        """
        try:
            cache_key = self._generate_cache_key(prompt, model, patient_context)

            # Query Cosmos DB for cached response
            cache_doc = self.db.collection(self.cache_collection).document(cache_key).get()

            if not cache_doc.exists:
                logger.info(f"Cache miss: {cache_key[:16]}...")
                self._record_cache_miss(cache_key)
                return None

            cache_data = cache_doc.to_dict()

            # Check if cache has expired
            created_at = cache_data.get('created_at')
            if created_at:
                try:
                    # Handle Firestore timestamp conversion
                    if hasattr(created_at, 'seconds'):
                        # Firestore Timestamp object - convert to datetime
                        created_at = datetime.utcfromtimestamp(created_at.seconds)

                    expiry_date = created_at + timedelta(days=self.cache_ttl_days)
                    if datetime.utcnow() > expiry_date:
                        logger.info(f"Cache expired: {cache_key[:16]}...")
                        self._record_cache_miss(cache_key, reason='expired')
                        return None
                except Exception as ts_error:
                    # If timestamp comparison fails, treat as non-expired (safer)
                    logger.warning(f"Timestamp comparison error (treating as valid): {ts_error}")

            # Cache hit!
            response = cache_data.get('response')
            if not response:
                logger.warning(f"Cache hit but response is empty: {cache_key[:16]}...")
                return None

            logger.info(f"Cache hit: {cache_key[:16]}... (saved ${cache_data.get('cost_saved', 0):.4f})")

            # Update cache statistics
            self._record_cache_hit(cache_key, cache_data)

            return response

        except Exception as e:
            logger.error(f"Error retrieving cached response: {e}", exc_info=True)
            return None


    def save_response(
        self,
        prompt: str,
        response: str,
        model: str = "gpt-4o",
        metadata: Optional[Dict[str, Any]] = None,
        patient_context: str = "",
        user_id: Optional[str] = None
    ) -> bool:
        """
        Save an AI response to the cache and training data collection.

        Args:
            prompt: The sanitized prompt text (PHI-safe)
            response: The AI response text
            model: The AI model name
            metadata: Optional metadata (endpoint, user type, etc.)
            patient_context: Patient-specific context for cache key uniqueness
            user_id: User ID for GDPR "Right to be Forgotten" compliance

        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(prompt, model, patient_context)

            # Calculate estimated cost saved per reuse
            # Model-specific pricing (as of January 2025)
            # Prices are per million tokens in USD
            model_pricing = {
                # OpenAI Models (legacy/fallback)
                'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
                'gpt-4o': {'input': 2.50, 'output': 10.00},
                'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
                'gpt-4': {'input': 30.00, 'output': 60.00},

                # Claude Models on Vertex AI (primary)
                'claude-sonnet-4-5@20250929': {'input': 3.00, 'output': 15.00},
                'claude-sonnet-4-5': {'input': 3.00, 'output': 15.00},
                'claude-opus-4@20250929': {'input': 5.00, 'output': 25.00},
                'claude-opus-4-5': {'input': 5.00, 'output': 25.00},
                'claude-3.5-sonnet': {'input': 3.00, 'output': 15.00},

                # Gemini Models (for reference)
                'gemini-2.5-pro': {'input': 1.25, 'output': 10.00},
                'gemini-2.5-flash': {'input': 0.15, 'output': 0.60},
            }

            # Default to Claude Sonnet 4.5 pricing if model not recognized
            pricing = model_pricing.get(
                model,
                model_pricing.get('claude-sonnet-4-5@20250929', {'input': 3.00, 'output': 15.00})
            )

            input_tokens = len(prompt.split()) * 1.3  # Rough estimate
            output_tokens = len(response.split()) * 1.3
            cost_per_call = (input_tokens / 1_000_000 * pricing['input']) + (output_tokens / 1_000_000 * pricing['output'])

            # Calculate expiration date (90 days from now)
            expires_at = datetime.utcnow() + timedelta(days=self.cache_ttl_days)

            # Prepare cache document
            cache_doc = {
                'cache_key': cache_key,
                'prompt': prompt,  # PHI-safe sanitized prompt
                'response': response,
                'model': model,
                'created_at': SERVER_TIMESTAMP,
                'expires_at': expires_at,  # Explicit expiration date for compliance
                'last_accessed': SERVER_TIMESTAMP,
                'access_count': 0,  # Number of times this cache was hit
                'cost_saved': cost_per_call,  # Estimated cost saved per hit
                'total_savings': 0.0,  # Total savings from all hits
                'user_id': user_id,  # For GDPR "Right to be Forgotten" compliance
                'metadata': metadata or {},
                'version': 1,  # For future cache versioning
            }

            # Save to cache collection
            self.db.collection(self.cache_collection).document(cache_key).set(cache_doc)

            # Also save to training data collection (for future LLM training)
            self._save_to_training_data(prompt, response, model, metadata)

            logger.info(f"Cached response: {cache_key[:16]}... (cost/reuse: ${cost_per_call:.4f})")
            return True

        except Exception as e:
            logger.error(f"Error saving response to cache: {e}", exc_info=True)
            return False


    def _save_to_training_data(
        self,
        prompt: str,
        response: str,
        model: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Save prompt-response pair to training data collection.

        This builds a dataset for future fine-tuning or training your own LLM.

        Args:
            prompt: Sanitized prompt
            response: AI response
            model: Model name
            metadata: Additional context
        """
        try:
            training_doc = {
                'prompt': prompt,
                'response': response,
                'model': model,
                'metadata': metadata or {},
                'created_at': SERVER_TIMESTAMP,
                'quality_score': None,  # Future: manual quality rating
                'reviewed': False,  # Future: human review flag
                'tags': self._extract_tags(metadata),  # Categorize by type
            }

            # Add to training data collection (auto-generated ID)
            self.db.collection(self.training_data_collection).add(training_doc)

        except Exception as e:
            logger.error(f"Error saving to training data: {e}", exc_info=True)


    def _extract_tags(self, metadata: Optional[Dict[str, Any]]) -> List[str]:
        """
        Extract tags from metadata for categorizing training data.

        Args:
            metadata: Metadata dictionary

        Returns:
            List of tags (e.g., ['subjective', 'diagnosis', 'treatment'])
        """
        if not metadata:
            return []

        tags = []

        # Extract endpoint type
        endpoint = metadata.get('endpoint', '')
        if 'subjective' in endpoint:
            tags.append('subjective_examination')
        elif 'diagnosis' in endpoint:
            tags.append('diagnosis')
        elif 'treatment' in endpoint:
            tags.append('treatment_plan')
        elif 'goals' in endpoint:
            tags.append('smart_goals')
        elif 'perspective' in endpoint:
            tags.append('patient_perspective')
        elif 'patho' in endpoint:
            tags.append('pathophysiology')
        elif 'flags' in endpoint:
            tags.append('clinical_flags')
        elif 'objective' in endpoint:
            tags.append('objective_assessment')
        elif 'followup' in endpoint:
            tags.append('followup')

        # Extract clinical area
        if metadata.get('clinical_area'):
            tags.append(metadata['clinical_area'])

        return tags


    def _record_cache_hit(self, cache_key: str, cache_data: Dict[str, Any]):
        """
        Update cache statistics when a cache hit occurs.

        Args:
            cache_key: The cache key
            cache_data: Existing cache document data
        """
        try:
            # Update cache document
            cache_ref = self.db.collection(self.cache_collection).document(cache_key)

            access_count = cache_data.get('access_count', 0) + 1
            cost_saved = cache_data.get('cost_saved', 0)
            total_savings = cost_saved * access_count

            cache_ref.update({
                'last_accessed': SERVER_TIMESTAMP,
                'access_count': access_count,
                'total_savings': total_savings
            })

            # Record in analytics
            self._record_analytics('cache_hit', {
                'cache_key': cache_key[:16],
                'access_count': access_count,
                'savings': cost_saved
            })

        except Exception as e:
            logger.error(f"Error recording cache hit: {e}", exc_info=True)


    def _record_cache_miss(self, cache_key: str, reason: str = 'not_found'):
        """
        Record a cache miss for analytics.

        Args:
            cache_key: The cache key
            reason: Reason for miss ('not_found' or 'expired')
        """
        try:
            self._record_analytics('cache_miss', {
                'cache_key': cache_key[:16],
                'reason': reason
            })
        except Exception as e:
            logger.error(f"Error recording cache miss: {e}", exc_info=True)


    def _record_analytics(self, event_type: str, data: Dict[str, Any]):
        """
        Record analytics event to Firestore.

        Args:
            event_type: Type of event ('cache_hit', 'cache_miss', etc.)
            data: Event data
        """
        try:
            analytics_doc = {
                'event_type': event_type,
                'data': data,
                'timestamp': SERVER_TIMESTAMP
            }
            self.db.collection(self.analytics_collection).add(analytics_doc)
        except Exception as e:
            logger.error(f"Error recording analytics: {e}", exc_info=True)


    def get_cache_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Args:
            days: Number of days to analyze

        Returns:
            dict: Statistics including hit rate, total savings, etc.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get all cache hits and misses
            analytics_ref = self.db.collection(self.analytics_collection)

            # Use filter parameter to avoid deprecation warnings
            from google.cloud.firestore_v1.base_query import FieldFilter

            try:
                hits_query = analytics_ref.where(filter=FieldFilter('event_type', '==', 'cache_hit')).where(filter=FieldFilter('timestamp', '>=', cutoff_date))
                misses_query = analytics_ref.where(filter=FieldFilter('event_type', '==', 'cache_miss')).where(filter=FieldFilter('timestamp', '>=', cutoff_date))
                hits = list(hits_query.stream())
                misses = list(misses_query.stream())
            except Exception as query_error:
                # Fallback: If composite index doesn't exist, just count from simpler queries
                logger.warning(f"Cache statistics query failed (may need composite index): {query_error}")
                hits = []
                misses = []

            total_hits = len(hits)
            total_misses = len(misses)
            total_requests = total_hits + total_misses

            hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

            # Calculate total savings
            total_savings = sum(
                hit.to_dict().get('data', {}).get('savings', 0)
                for hit in hits
            )

            # Get most used cache entries
            try:
                cache_entries = self.db.collection(self.cache_collection).order_by('access_count', direction=firestore.Query.DESCENDING).limit(10).stream()
                top_cached = [
                    {
                        'prompt_preview': entry.to_dict().get('prompt', '')[:100],
                        'access_count': entry.to_dict().get('access_count', 0),
                        'savings': entry.to_dict().get('total_savings', 0)
                    }
                    for entry in cache_entries
                ]
            except Exception as cache_error:
                logger.warning(f"Could not get top cached entries: {cache_error}")
                top_cached = []

            return {
                'period_days': days,
                'total_requests': total_requests,
                'cache_hits': total_hits,
                'cache_misses': total_misses,
                'hit_rate_percent': round(hit_rate, 2),
                'total_savings_usd': round(total_savings, 4),
                'top_cached_responses': top_cached
            }

        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}", exc_info=True)
            # Return default stats structure instead of empty dict
            return {
                'period_days': days,
                'total_requests': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'hit_rate_percent': 0,
                'total_savings_usd': 0,
                'top_cached_responses': []
            }


    def export_training_data(
        self,
        output_format: str = 'jsonl',
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Export training data for fine-tuning or training your own LLM.

        Args:
            output_format: Format for export ('jsonl', 'csv', 'json')
            filters: Optional filters (e.g., {'tags': ['diagnosis']})

        Returns:
            List of training examples in the specified format
        """
        try:
            query = self.db.collection(self.training_data_collection)

            # Apply filters
            if filters:
                if 'tags' in filters:
                    # Filter by tag (array contains)
                    for tag in filters['tags']:
                        query = query.where('tags', 'array_contains', tag)

                if 'reviewed_only' in filters and filters['reviewed_only']:
                    query = query.where('reviewed', '==', True)

            # Fetch documents
            docs = query.stream()

            training_examples = []
            for doc in docs:
                data = doc.to_dict()

                if output_format == 'jsonl':
                    # OpenAI fine-tuning format
                    example = {
                        "messages": [
                            {"role": "system", "content": "You are a helpful clinical reasoning assistant."},
                            {"role": "user", "content": data['prompt']},
                            {"role": "assistant", "content": data['response']}
                        ]
                    }
                elif output_format == 'json':
                    # Simple JSON format
                    example = {
                        "prompt": data['prompt'],
                        "response": data['response'],
                        "metadata": data.get('metadata', {})
                    }
                else:  # csv
                    example = {
                        "prompt": data['prompt'],
                        "response": data['response']
                    }

                training_examples.append(example)

            logger.info(f"Exported {len(training_examples)} training examples in {output_format} format")
            return training_examples

        except Exception as e:
            logger.error(f"Error exporting training data: {e}", exc_info=True)
            return []


    def clear_expired_cache(self) -> int:
        """
        Remove expired cache entries to save storage costs.

        Returns:
            int: Number of entries deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.cache_ttl_days)

            # Query expired entries
            expired_query = self.db.collection(self.cache_collection).where('created_at', '<', cutoff_date)

            expired_docs = list(expired_query.stream())

            # Delete in batch
            batch = self.db.batch()
            for doc in expired_docs:
                batch.delete(doc.reference)

            batch.commit()

            logger.info(f"Cleared {len(expired_docs)} expired cache entries")
            return len(expired_docs)

        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}", exc_info=True)
            return 0


    def delete_user_cache(self, user_id: str) -> int:
        """
        Delete all AI cache entries for a specific user.

        GDPR/HIPAA "Right to be Forgotten" compliance:
        When a user requests data deletion, this removes all their cached AI interactions.

        Args:
            user_id: The user ID whose cache should be deleted

        Returns:
            int: Number of cache entries deleted
        """
        try:
            if not user_id:
                logger.warning("delete_user_cache called with empty user_id")
                return 0

            # Query all cache entries for this user
            user_cache_query = self.db.collection(self.cache_collection).where('user_id', '==', user_id)
            user_cache_docs = list(user_cache_query.stream())

            if not user_cache_docs:
                logger.info(f"No cache entries found for user {user_id}")
                return 0

            # Delete in batches (Firestore batch limit is 500 operations)
            deleted_count = 0
            batch = self.db.batch()
            batch_count = 0

            for doc in user_cache_docs:
                batch.delete(doc.reference)
                batch_count += 1
                deleted_count += 1

                # Commit batch every 500 operations
                if batch_count >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    batch_count = 0

            # Commit remaining deletions
            if batch_count > 0:
                batch.commit()

            logger.info(f"Deleted {deleted_count} cache entries for user {user_id} (Right to be Forgotten)")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting user cache for {user_id}: {e}", exc_info=True)
            return 0


    def delete_user_training_data(self, user_id: str) -> int:
        """
        Delete all training data entries for a specific user.

        Part of GDPR/HIPAA "Right to be Forgotten" compliance.

        Args:
            user_id: The user ID whose training data should be deleted

        Returns:
            int: Number of training data entries deleted
        """
        try:
            if not user_id:
                logger.warning("delete_user_training_data called with empty user_id")
                return 0

            # Query all training data for this user
            # Note: Training data doesn't currently store user_id directly
            # This is a placeholder for future implementation
            logger.warning("Training data deletion not fully implemented - user_id not tracked in training_data collection")

            # TODO: Add user_id to training_data_collection documents
            # For now, we can't delete training data without user_id tracking

            return 0

        except Exception as e:
            logger.error(f"Error deleting user training data for {user_id}: {e}", exc_info=True)
            return 0


# ─── HELPER FUNCTIONS FOR EASY INTEGRATION ────────────────────────────

def get_ai_suggestion_with_cache(
    db,
    prompt: str,
    model: str = "gpt-4o",
    openai_client = None,
    metadata: Optional[Dict[str, Any]] = None,
    patient_context: str = "",
    user_id: Optional[str] = None
) -> str:
    """
    Get AI suggestion with intelligent caching.

    This function wraps the Azure OpenAI API call with cache lookup and storage.

    Args:
        db: Cosmos DB client
        prompt: Sanitized prompt (PHI-safe)
        model: AI model name (default: gpt-4o)
        openai_client: Azure OpenAI client instance
        metadata: Optional metadata for analytics
        patient_context: Patient-specific context (e.g., age/sex demographics) to ensure unique cache per patient profile
        user_id: User ID for GDPR "Right to be Forgotten" compliance

    Returns:
        str: AI response (from cache or fresh API call)
    """
    cache = AICache(db)

    # Try to get from cache first
    cached_response = cache.get_cached_response(prompt, model, patient_context)
    if cached_response:
        return cached_response

    # Cache miss - call AI API (Vertex AI or OpenAI)
    try:
        if not openai_client:
            return "AI service not configured."

        # Use create_chat_completion for both Vertex AI and OpenAI compatibility
        resp = openai_client.create_chat_completion(
            model=model,
            messages=[{
                "role": "system",
                "content": "You are a helpful clinical reasoning assistant."
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0.2,  # Low temperature for consistent, deterministic clinical responses
            max_tokens=1500  # Increased from 200 to allow complete clinical responses
        )

        response = resp['choices'][0]['message']['content']

        # Save to cache for future use
        cache.save_response(prompt, response, model, metadata, patient_context, user_id)

        return response

    except Exception as e:
        logger.error(f"Error calling AI API: {e}", exc_info=True)
        return "AI service temporarily unavailable. Please try again."
