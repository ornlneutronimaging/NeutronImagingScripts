#!/usr/env/bin python

"""Metadata Handler for MARS."""

import logging
import numpy as np
from enum import Enum
from neutronimaging.metadata_handler import MetadataHandler


class MetadataName(Enum):
    EXPOSURE_TIME = 65027
    DETECTOR_MANUFACTURER = 65026
    APERTURE_HR = 65068
    APERTURE_HL = 65070
    APERTURE_VT = 65066
    APERTURE_VB = 65064

    def __str__(self):
        return self.value


METADATA_KEYS = {
    "ob": [
        MetadataName.EXPOSURE_TIME,
        MetadataName.DETECTOR_MANUFACTURER,
        MetadataName.APERTURE_HR,
        MetadataName.APERTURE_HL,
        MetadataName.APERTURE_VT,
        MetadataName.APERTURE_VB,
    ],
    "df": [
        MetadataName.EXPOSURE_TIME,
        MetadataName.DETECTOR_MANUFACTURER,
    ],
    "dc": [
        MetadataName.EXPOSURE_TIME,
        MetadataName.DETECTOR_MANUFACTURER,
    ],
    "all": [
        MetadataName.EXPOSURE_TIME,
        MetadataName.DETECTOR_MANUFACTURER,
        MetadataName.APERTURE_HR,
        MetadataName.APERTURE_HL,
        MetadataName.APERTURE_VT,
        MetadataName.APERTURE_VB,
    ],
}
