"""Base repository with common CRUD operations."""
from typing import List, Optional, TypeVar, Generic
from config.database import db

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository implementing common database operations.
    
    Follows Repository Pattern for data access abstraction.
    """
    
    def __init__(self, model: type):
        """Initialize repository with model class."""
        self.model = model
    
    def create(self, **kwargs) -> T:
        """Create a new entity."""
        entity = self.model(**kwargs)
        db.session.add(entity)
        db.session.commit()
        return entity
    
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get entity by ID."""
        return self.model.query.get(entity_id)
    
    def get_all(self) -> List[T]:
        """Get all entities."""
        return self.model.query.all()
    
    def update(self, entity_id: int, **kwargs) -> Optional[T]:
        """Update an entity."""
        entity = self.get_by_id(entity_id)
        if entity:
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            db.session.commit()
        return entity
    
    def delete(self, entity_id: int) -> bool:
        """Delete an entity."""
        entity = self.get_by_id(entity_id)
        if entity:
            db.session.delete(entity)
            db.session.commit()
            return True
        return False
    
    def save(self, entity: T) -> T:
        """Save an entity (for updates)."""
        db.session.add(entity)
        db.session.commit()
        return entity
    
    def commit(self):
        """Commit current transaction."""
        db.session.commit()
    
    def rollback(self):
        """Rollback current transaction."""
        db.session.rollback()
