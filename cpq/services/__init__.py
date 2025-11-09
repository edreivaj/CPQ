"""
Servicios externos (Catastro, MDT, OSM)
"""

from .catastro import CatastroService
from .mdt import MDTService
from .osm import OSMService

__all__ = ['CatastroService', 'MDTService', 'OSMService']
