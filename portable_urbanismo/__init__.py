"""Paquete portable: proxy urbanístico por contexto (análisis del entorno)."""

from .urbanismo_proxy import (
    compute_urbanismo_proxy,
    ProxyConfig,
    ProxyResult,
    ProxyStats,
)

__all__ = [
    "compute_urbanismo_proxy",
    "ProxyConfig",
    "ProxyResult",
    "ProxyStats",
]
