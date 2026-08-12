"""The five pipeline stages (Discover, Prove, Verify, Align, Read)."""

from .discover import discover
from .prove import prove
from .verify import verify
from .align import align
from .read import read

__all__ = ["discover", "prove", "verify", "align", "read"]
