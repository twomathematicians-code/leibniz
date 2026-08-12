"""The pipeline stages (Discover, Prove, Verify, Align, Read, Formalize)."""

from .discover import discover
from .prove import prove
from .verify import verify
from .align import align
from .read import read
from .formalize import formalize, FormalizationResult

__all__ = ["discover", "prove", "verify", "align", "read", "formalize", "FormalizationResult"]
