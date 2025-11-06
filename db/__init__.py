# db/__init__.py
from .connection import get_connection, execute_query

__all__ = ['get_connection', 'execute_query']
