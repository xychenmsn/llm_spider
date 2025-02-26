"""
Database models for the LLM Spider application.
"""

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create the SQLAlchemy base
Base = declarative_base()

class URLParser(Base):
    """
    Model for storing URL parsing patterns and their associated parsers.
    
    Attributes:
        id: Primary key
        name: Name of the parser
        url_pattern: Regex pattern to match URLs
        parser: Name of the parser function or class to use
        meta_data: JSON metadata for the parser
        chat_data: JSON data for chat configuration
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """
    __tablename__ = 'url_parser'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    url_pattern = Column(String(255), nullable=False)
    parser = Column(String(255), nullable=False)
    meta_data = Column(JSON, nullable=True)
    chat_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<URLParser(name='{self.name}', url_pattern='{self.url_pattern}')>"


# Function to get the database engine
def get_engine():
    """
    Create and return a SQLAlchemy engine using the DATABASE_URL from environment variables.
    """
    database_url = os.getenv('DATABASE_URL', 'sqlite:///db/llm_spider.db')
    return create_engine(database_url) 