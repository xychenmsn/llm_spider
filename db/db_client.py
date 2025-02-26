"""
Database client for LLM Spider.

This module provides a robust database client that handles detached objects properly
and provides a clean interface for database operations.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Generic
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import DeclarativeMeta

from db.models import Base, get_engine

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for generic type hints
T = TypeVar('T', bound=Base)

class DBClient:
    """
    Database client for LLM Spider.
    
    This class provides methods for common database operations and handles
    detached objects properly.
    """
    
    def __init__(self, engine=None):
        """
        Initialize the database client.
        
        Args:
            engine: SQLAlchemy engine to use. If None, the default engine from models.py is used.
        """
        self.engine = engine or get_engine()
        self.session_factory = sessionmaker(bind=self.engine)
        self.scoped_session = scoped_session(self.session_factory)
    
    @contextmanager
    def session_scope(self) -> Session:
        """
        Context manager for database sessions.
        
        Usage:
            with db_client.session_scope() as session:
                # Use session here
                results = session.query(Model).all()
        
        The session will be automatically committed on success and
        rolled back on exception.
        """
        session = self.scoped_session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            self.scoped_session.remove()
    
    def _to_dict(self, obj: T) -> Dict[str, Any]:
        """
        Convert a SQLAlchemy model instance to a dictionary.
        
        Args:
            obj: SQLAlchemy model instance
            
        Returns:
            Dictionary representation of the model instance
        """
        if obj is None:
            return None
            
        result = {}
        for c in inspect(obj).mapper.column_attrs:
            value = getattr(obj, c.key)
            # Handle JSON fields
            if c.key in ('meta_data', 'chat_data') and value is not None:
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
            result[c.key] = value
        return result
    
    def _from_dict(self, model_class: Type[T], data: Dict[str, Any]) -> T:
        """
        Create a SQLAlchemy model instance from a dictionary.
        
        Args:
            model_class: SQLAlchemy model class
            data: Dictionary of attributes
            
        Returns:
            SQLAlchemy model instance
        """
        if data is None:
            return None
            
        # Handle JSON fields
        for key in ('meta_data', 'chat_data'):
            if key in data and data[key] is not None and not isinstance(data[key], str):
                data[key] = json.dumps(data[key])
                
        return model_class(**data)
    
    def create(self, obj: T) -> T:
        """
        Create a new record in the database.
        
        Args:
            obj: SQLAlchemy model instance to create
            
        Returns:
            The created record with its ID populated
        """
        with self.session_scope() as session:
            session.add(obj)
            session.flush()
            # Convert to dictionary to detach from session
            obj_dict = self._to_dict(obj)
            return self._from_dict(obj.__class__, obj_dict)
    
    def get_by_id(self, model_class: Type[T], record_id: int) -> Optional[T]:
        """
        Get a record by its ID.
        
        Args:
            model_class: SQLAlchemy model class
            record_id: ID of the record to retrieve
            
        Returns:
            The record if found, None otherwise
        """
        with self.session_scope() as session:
            obj = session.query(model_class).filter(model_class.id == record_id).first()
            if obj:
                # Convert to dictionary to detach from session
                obj_dict = self._to_dict(obj)
                return self._from_dict(model_class, obj_dict)
            return None
    
    def get_all(self, model_class: Type[T]) -> List[T]:
        """
        Get all records of a specific model.
        
        Args:
            model_class: SQLAlchemy model class
            
        Returns:
            List of all records
        """
        with self.session_scope() as session:
            objs = session.query(model_class).all()
            # Convert each object to dictionary to detach from session
            return [self._from_dict(model_class, self._to_dict(obj)) for obj in objs]
    
    def update(self, model_class: Type[T], record_id: int, **kwargs) -> Optional[T]:
        """
        Update a record by its ID.
        
        Args:
            model_class: SQLAlchemy model class
            record_id: ID of the record to update
            **kwargs: Fields to update
            
        Returns:
            The updated record if found, None otherwise
        """
        with self.session_scope() as session:
            obj = session.query(model_class).filter(model_class.id == record_id).first()
            if obj:
                # Handle JSON fields
                for key in ('meta_data', 'chat_data'):
                    if key in kwargs and kwargs[key] is not None and not isinstance(kwargs[key], str):
                        kwargs[key] = json.dumps(kwargs[key])
                
                for key, value in kwargs.items():
                    setattr(obj, key, value)
                session.flush()
                # Convert to dictionary to detach from session
                obj_dict = self._to_dict(obj)
                return self._from_dict(model_class, obj_dict)
            return None
    
    def delete(self, model_class: Type[T], record_id: int) -> bool:
        """
        Delete a record by its ID.
        
        Args:
            model_class: SQLAlchemy model class
            record_id: ID of the record to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self.session_scope() as session:
            obj = session.query(model_class).filter(model_class.id == record_id).first()
            if obj:
                session.delete(obj)
                return True
            return False
    
    def query(self, model_class: Type[T], **filters) -> List[T]:
        """
        Query records with filters.
        
        Args:
            model_class: SQLAlchemy model class
            **filters: Field filters (field_name=value)
            
        Returns:
            List of matching records
        """
        with self.session_scope() as session:
            query = session.query(model_class)
            for field, value in filters.items():
                query = query.filter(getattr(model_class, field) == value)
            objs = query.all()
            # Convert each object to dictionary to detach from session
            return [self._from_dict(model_class, self._to_dict(obj)) for obj in objs]
    
    def execute_raw_query(self, query_string: str, **params) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query.
        
        Args:
            query_string: SQL query string
            **params: Query parameters
            
        Returns:
            List of dictionaries representing the query results
        """
        with self.session_scope() as session:
            result = session.execute(query_string, params)
            return [dict(row) for row in result]

# Create a global instance of the database client
db_client = DBClient() 