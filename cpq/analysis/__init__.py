"""
Módulos de análisis (terreno, límites, costes, urbanismo proxy)
"""

from .boundaries import ParcelBoundaryAnalyzer
from .terrain import (
    get_z_at_point,
    compute_volume_metrics,
    calc_pendiente,
    get_xyz_from_pad,
    dimensionar_muro_perimetral_real
)
from .costs import (
    compute_horizontal_access_costs,
    compute_vertical_access_costs,
    compute_construction_cost,
    compute_slab_cost,
    compute_earthworks_cost,
    compute_containment_cost,
    compute_fees_total
)
from .urbanismo_proxy import (
    compute_urbanismo_proxy,
    ProxyConfig,
    ProxyResult,
    ProxyStats
)

__all__ = [
    'ParcelBoundaryAnalyzer',
    'get_z_at_point',
    'compute_volume_metrics',
    'calc_pendiente',
    'get_xyz_from_pad',
    'dimensionar_muro_perimetral_real',
    'compute_horizontal_access_costs',
    'compute_vertical_access_costs',
    'compute_construction_cost',
    'compute_slab_cost',
    'compute_earthworks_cost',
    'compute_containment_cost',
    'compute_fees_total',
    'compute_urbanismo_proxy',
    'ProxyConfig',
    'ProxyResult',
    'ProxyStats'
]
