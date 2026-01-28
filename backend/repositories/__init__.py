"""Base Repository - Abstract data access patterns"""
from typing import Dict, List, Optional, Any, TypeVar, Generic
from abc import ABC, abstractmethod

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Abstract base class for all repositories"""
    
    @property
    @abstractmethod
    def collection_name(self) -> str:
        """Return the MongoDB collection name"""
        pass
    
    @property
    @abstractmethod
    def id_field(self) -> str:
        """Return the primary ID field name"""
        pass
    
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[T]:
        """Find a document by ID"""
        pass
    
    @abstractmethod
    async def find_all(self, query: Dict = None, limit: int = 100) -> List[T]:
        """Find all documents matching query"""
        pass
    
    @abstractmethod
    async def create(self, data: Dict) -> T:
        """Create a new document"""
        pass
    
    @abstractmethod
    async def update(self, id: str, data: Dict) -> bool:
        """Update a document"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a document"""
        pass
