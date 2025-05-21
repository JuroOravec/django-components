# DO NOT MODIFY, ONLY UPDATE THE MODULE NAME WHEN NEEDED!
# This file is what maturin auto-generates. But it seems maturin omits it when we have a __init__.pyi file.
# So we have to manually include it here.

from .djc_template_parser import *

__doc__ = djc_template_parser.__doc__
if hasattr(djc_template_parser, "__all__"):
    __all__ = djc_template_parser.__all__
