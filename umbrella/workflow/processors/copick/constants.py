"""Tomogram types copick can import, and the software whose tree owns each."""

from enum import Enum


class ImportTomoType(str, Enum):
    """Values of the import_tomo_type parameter (mirrors the schema.yaml enum)."""

    DCTF = "dctf"
    SART = "sart"
    WBP = "wbp"
    DENOISE = "denoise"

    @property
    def source_software(self) -> str:
        """The processor whose tree this type's tomograms live in."""
        return _SOURCE_SOFTWARE[self]

    @classmethod
    def values_for(cls, source: str) -> list[str]:
        """The parameter values whose tomograms live in `source`'s tree."""
        return [tomo_type.value for tomo_type in cls if tomo_type.source_software == source]


# A new type must be mapped here; ImportTomoType(value) already rejects unknown values.
_SOURCE_SOFTWARE = {
    ImportTomoType.DCTF: "aretomo3",
    ImportTomoType.SART: "aretomo3",
    ImportTomoType.WBP: "aretomo3",
    ImportTomoType.DENOISE: "denoiset",
}
