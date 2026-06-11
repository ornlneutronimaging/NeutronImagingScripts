# type: ignore
__description__ = "Neutron Imaging Reduction"
__url__ = "https://github.com/ornlneutronimaging/NeutronImagingScripts"

__author__ = "C.Zhang"
__email__ = "zhangc@ornl.gov"

try:
    from ._version import __version__  # noqa: F401
except ImportError:
    __version__ = "unknown"
