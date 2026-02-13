"""
Azure Cosmos DB Service Layer
Replaces Firebase Firestore with Azure Cosmos DB
Provides Firestore-compatible API for minimal code changes
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from azure.cosmos import CosmosClient, PartitionKey, exceptions

logger = logging.getLogger("app.azure_cosmos_db")


class CosmosDBDocument:
    """Wrapper class to mimic Firestore DocumentSnapshot"""

    def __init__(self, document_id: str, data: Dict[str, Any], exists: bool = True):
        self.id = document_id
        self._data = data
        self._exists = exists

    @property
    def exists(self) -> bool:
        """Check if document exists"""
        return self._exists

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary (Firestore compatibility)"""
        if not self._exists:
            return {}
        # Remove Cosmos DB metadata fields
        data = {k: v for k, v in self._data.items()
                if not k.startswith('_') and k != 'id'}
        return data

    def get(self, field: str) -> Any:
        """Get a specific field value"""
        return self._data.get(field)


class CosmosDBQuery:
    """Query builder for Cosmos DB (Firestore compatibility)"""

    def __init__(self, container, base_query: str = None, parameters: List = None):
        self.container = container
        self.query_parts = []
        self.parameters = parameters or []
        self.order_field = None
        self.order_direction = "ASC"
        self.limit_count = None

        if base_query:
            self.query_parts.append(base_query)

    def where(self, field: str, op: str, value: Any) -> 'CosmosDBQuery':
        """Add WHERE clause (Firestore compatibility)"""
        param_name = f"@param{len(self.parameters)}"

        # Map Firestore operators to SQL operators
        op_map = {
            '==': '=',
            '!=': '!=',
            '<': '<',
            '<=': '<=',
            '>': '>',
            '>=': '>=',
            'array-contains': 'ARRAY_CONTAINS',
            'in': 'IN'
        }

        sql_op = op_map.get(op, op)

        if sql_op == 'ARRAY_CONTAINS':
            condition = f"ARRAY_CONTAINS(c.{field}, {param_name})"
        elif sql_op == 'IN':
            condition = f"c.{field} IN {param_name}"
        else:
            condition = f"c.{field} {sql_op} {param_name}"

        self.query_parts.append(condition)
        self.parameters.append({"name": param_name, "value": value})

        return self

    def order_by(self, field: str, direction: str = "ASCENDING") -> 'CosmosDBQuery':
        """Add ORDER BY clause (Firestore compatibility)"""
        self.order_field = field
        self.order_direction = "ASC" if direction == "ASCENDING" else "DESC"
        return self

    def limit(self, count: int) -> 'CosmosDBQuery':
        """Add LIMIT clause (Firestore compatibility)"""
        self.limit_count = count
        return self

    def get(self) -> List[CosmosDBDocument]:
        """Execute query and return documents"""
        # Build full SQL query
        query = "SELECT * FROM c"

        if self.query_parts:
            query += " WHERE " + " AND ".join(self.query_parts)

        if self.order_field:
            query += f" ORDER BY c.{self.order_field} {self.order_direction}"

        if self.limit_count:
            query += f" OFFSET 0 LIMIT {self.limit_count}"

        # Execute query
        try:
            items = list(self.container.query_items(
                query=query,
                parameters=self.parameters,
                enable_cross_partition_query=True
            ))

            return [CosmosDBDocument(item['id'], item, True) for item in items]
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Cosmos DB query error: {e}", exc_info=True)
            return []

    def stream(self):
        """Stream query results (Firestore compatibility)"""
        return self.get()


class CosmosDBDocumentReference:
    """Document reference for Cosmos DB (Firestore compatibility)"""

    def __init__(self, container, document_id: str):
        self.container = container
        self.id = document_id

    def get(self) -> CosmosDBDocument:
        """Get document by ID"""
        try:
            # For users collection, partition key is /userId (same as id/email)
            # For other collections, partition key is /id
            item = self.container.read_item(
                item=self.id,
                partition_key=self.id  # Works for both /id and /userId when userId == id
            )
            return CosmosDBDocument(self.id, item, True)
        except exceptions.CosmosResourceNotFoundError:
            # Document not found with direct read, try query as fallback
            try:
                query = f"SELECT * FROM c WHERE c.id = @id"
                parameters = [{"name": "@id", "value": self.id}]
                items = list(self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                if items:
                    return CosmosDBDocument(self.id, items[0], True)
                else:
                    return CosmosDBDocument(self.id, {}, False)
            except Exception:
                return CosmosDBDocument(self.id, {}, False)
        except Exception as e:
            # Log the actual error for debugging
            logger.error(f"Error reading document {self.id}: {e} (type: {type(e).__name__})", exc_info=True)
            return CosmosDBDocument(self.id, {}, False)

    def set(self, data: Dict[str, Any], merge: bool = False) -> None:
        """Set document data"""
        try:
            # Add metadata
            doc_data = data.copy()
            doc_data['id'] = self.id

            # Handle Increment objects - need to read current value first
            increment_fields = {k: v for k, v in doc_data.items() if isinstance(v, Increment)}
            if increment_fields:
                existing = self.get()
                if existing.exists:
                    existing_data = existing.to_dict()
                    for field, increment_obj in increment_fields.items():
                        current_value = existing_data.get(field, 0)
                        doc_data[field] = current_value + increment_obj.value
                else:
                    # Document doesn't exist, treat as 0 + increment
                    for field, increment_obj in increment_fields.items():
                        doc_data[field] = increment_obj.value

            # Handle SERVER_TIMESTAMP
            if 'timestamp' in doc_data and doc_data['timestamp'] == 'SERVER_TIMESTAMP':
                doc_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            if 'created_at' in doc_data and doc_data['created_at'] == 'SERVER_TIMESTAMP':
                doc_data['created_at'] = datetime.now(timezone.utc).isoformat()
            if 'updated_at' in doc_data and doc_data['updated_at'] == 'SERVER_TIMESTAMP':
                doc_data['updated_at'] = datetime.now(timezone.utc).isoformat()

            if merge:
                # Merge with existing document
                existing = self.get()
                if existing.exists:
                    merged_data = existing.to_dict()
                    merged_data.update(doc_data)
                    doc_data = merged_data
                    doc_data['id'] = self.id

            # Handle DELETE_FIELD (None values) - remove those fields
            doc_data = {k: v for k, v in doc_data.items() if v is not None}

            self.container.upsert_item(body=doc_data)
        except Exception as e:
            logger.error(f"Error setting document {self.id}: {e}", exc_info=True)
            raise

    def update(self, data: Dict[str, Any]) -> None:
        """Update document fields"""
        self.set(data, merge=True)

    def delete(self) -> None:
        """Delete document"""
        try:
            self.container.delete_item(
                item=self.id,
                partition_key=self.id
            )
        except exceptions.CosmosResourceNotFoundError:
            pass  # Document doesn't exist, ignore
        except Exception as e:
            logger.error(f"Error deleting document {self.id}: {e}", exc_info=True)
            raise


class CosmosDBCollection:
    """Collection reference for Cosmos DB (Firestore compatibility)"""

    def __init__(self, database, container_name: str):
        self.database = database
        self.container_name = container_name

        # Get or create container
        try:
            self.container = database.get_container_client(container_name)
            # Test if container exists
            self.container.read()
        except exceptions.CosmosResourceNotFoundError:
            # Container doesn't exist, create it
            logger.info(f"Container {container_name} not found, creating...")
            self.container = database.create_container(
                id=container_name,
                partition_key=PartitionKey(path="/id")
            )

    def document(self, document_id: str) -> CosmosDBDocumentReference:
        """Get document reference by ID"""
        return CosmosDBDocumentReference(self.container, document_id)

    def add(self, data: Dict[str, Any]) -> tuple:
        """Add new document with auto-generated ID (Firestore compatibility)"""
        doc_id = str(uuid.uuid4())
        doc_ref = self.document(doc_id)

        # Handle SERVER_TIMESTAMP
        doc_data = data.copy()
        if 'timestamp' in doc_data and doc_data['timestamp'] == 'SERVER_TIMESTAMP':
            doc_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        if 'created_at' in doc_data and doc_data['created_at'] == 'SERVER_TIMESTAMP':
            doc_data['created_at'] = datetime.now(timezone.utc).isoformat()

        doc_ref.set(doc_data)
        return (None, doc_ref)  # Firestore returns (update_time, doc_ref)

    def where(self, field: str, op: str, value: Any) -> CosmosDBQuery:
        """Start query with WHERE clause"""
        return CosmosDBQuery(self.container).where(field, op, value)

    def order_by(self, field: str, direction: str = "ASCENDING") -> CosmosDBQuery:
        """Start query with ORDER BY clause"""
        return CosmosDBQuery(self.container).order_by(field, direction)

    def limit(self, count: int) -> CosmosDBQuery:
        """Limit query results"""
        return CosmosDBQuery(self.container).limit(count)

    def stream(self):
        """Stream all documents in collection"""
        try:
            items = list(self.container.read_all_items())
            return [CosmosDBDocument(item['id'], item, True) for item in items]
        except Exception as e:
            logger.error(f"Error streaming collection {self.container_name}: {e}", exc_info=True)
            return []

    def get(self) -> List[CosmosDBDocument]:
        """Get all documents in collection"""
        return self.stream()


class CosmosDB:
    """Main Cosmos DB client (Firestore compatibility)"""

    def __init__(self, endpoint: str = None, key: str = None, database_name: str = None):
        """Initialize Cosmos DB client"""
        self.endpoint = endpoint or os.getenv('COSMOS_DB_ENDPOINT')
        self.key = key or os.getenv('COSMOS_DB_KEY')
        self.database_name = database_name or os.getenv('COSMOS_DB_DATABASE_NAME', 'physiologicprism')

        if not self.endpoint or not self.key:
            raise ValueError("COSMOS_DB_ENDPOINT and COSMOS_DB_KEY must be set")

        # Initialize Cosmos client
        self.client = CosmosClient(self.endpoint, self.key)

        # Get or create database
        try:
            self.database = self.client.get_database_client(self.database_name)
            # Test if database exists
            self.database.read()
        except exceptions.CosmosResourceNotFoundError:
            logger.info(f"Database {self.database_name} not found, creating...")
            self.database = self.client.create_database(self.database_name)

    def collection(self, collection_name: str) -> CosmosDBCollection:
        """Get collection reference (Firestore compatibility)"""
        return CosmosDBCollection(self.database, collection_name)

    def batch(self):
        """Create batch for multiple operations (simplified for Cosmos DB)"""
        return CosmosBatch(self.database)


class CosmosBatch:
    """Batch operations for Cosmos DB (Firestore compatibility)"""

    def __init__(self, database):
        self.database = database
        self.operations = []

    def set(self, doc_ref: CosmosDBDocumentReference, data: Dict[str, Any]):
        """Add set operation to batch"""
        self.operations.append(('set', doc_ref, data))
        return self

    def update(self, doc_ref: CosmosDBDocumentReference, data: Dict[str, Any]):
        """Add update operation to batch"""
        self.operations.append(('update', doc_ref, data))
        return self

    def delete(self, doc_ref: CosmosDBDocumentReference):
        """Add delete operation to batch"""
        self.operations.append(('delete', doc_ref, None))
        return self

    def commit(self):
        """Execute all batched operations"""
        for op_type, doc_ref, data in self.operations:
            if op_type == 'set':
                doc_ref.set(data)
            elif op_type == 'update':
                doc_ref.update(data)
            elif op_type == 'delete':
                doc_ref.delete()

        self.operations = []


# Constants for Firestore compatibility
SERVER_TIMESTAMP = 'SERVER_TIMESTAMP'
DELETE_FIELD = None  # Cosmos DB: setting to None deletes the field


class Increment:
    """Increment a numeric field (Firestore compatibility)"""
    def __init__(self, value: int = 1):
        self.value = value


# Singleton instance
_cosmos_db_instance = None


def get_cosmos_db() -> CosmosDB:
    """Get or create Cosmos DB instance (singleton)"""
    global _cosmos_db_instance
    if _cosmos_db_instance is None:
        _cosmos_db_instance = CosmosDB()
    return _cosmos_db_instance
