"""
Backward compatibility stub for mikrotik_client.

This module re-exports MikrotikClient from the new mikrotik package location.
Existing imports of `from mikrotik_client import MikrotikClient` will continue to work.

DEPRECATED: Please update imports to use `from mikrotik import MikrotikClient` instead.
"""

import warnings

from mikrotik import MikrotikClient

# Issue deprecation warning
warnings.warn(
    "Importing from mikrotik_client is deprecated. "
    "Please update to: from mikrotik import MikrotikClient",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["MikrotikClient"]