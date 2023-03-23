#!/usr/env/bin python
"""Generic metadata handler.

This module is adapted from the original implementation at:

https://github.com/neutronimaging/python_notebooks/blob/next/notebooks/__code/metadata_handler.py
"""
from PIL import Image
import datetime
import os
from typing import Optional
from collections import OrderedDict
from tqdm import tqdm

class MetadataHandler:
    """Generic metadata handler."""

    @staticmethod
    def get_time_stamp(file_name: str = "", ext: str = "tif") -> int:
        """Get time stamp from file name.

        Parameters
        ----------
        file_name : str
            file name
        ext : str
            file extension

        Returns
        -------
        time_stamp : int
        """
        if ext in ["tif", "tiff"]:
            try:
                o_image = Image.open(file_name)
                o_dict = dict(o_image.tag_v2)
                try:
                    time_stamp_s = o_dict[65002]
                    time_stamp_ns = o_dict[65003]
                    time_stamp = time_stamp_s + time_stamp_ns * 1e-9
                except:
                    time_stamp = o_dict[65000]

                time_stamp = (
                    MetadataHandler._convert_epics_timestamp_to_rfc3339_timestamp(
                        time_stamp
                    )
                )

            except:
                time_stamp = os.path.getctime(file_name)
        elif ext == "fits":
            time_stamp = os.path.getctime(file_name)
        elif ext == "jpg":
            time_stamp = os.path.getctime(file_name)

        else:
            raise NotImplemented

        return

    @staticmethod
    def _convert_epics_timestamp_to_rfc3339_timestamp(epics_timestamp: int) -> int:
        """
        Convert an EPICS timestamp to an RFC3339 timestamp.

        Parameters
        ----------
        epics_timestamp : int
            The timestamp to convert.

        Returns
        -------
        unix_epoch_timestamp : int
            The timestamp in seconds since the UNIX epoch.

        Notes
        -----
        TIFF files from CG1D have EPICS timestamps.  From the Controls
        Wiki:

        > EPICS timestamp. The timestamp is made when the image is read
        > out from the camera. Format is seconds.nanoseconds since Jan 1st
        > 00:00 1990.

        Convert seconds since "EPICS epoch" to seconds since the "UNIX
        epoch" so that Python can understand it.  I got the offset by
        calculating the number of seconds between the two epochs at
        https://www.epochconverter.com/
        """
        EPOCH_OFFSET = 631152000
        unix_epoch_timestamp = EPOCH_OFFSET + epics_timestamp

        return unix_epoch_timestamp

    @staticmethod
    def convert_to_human_readable_format(timestamp: int) -> str:
        """Convert the unix time stamp into a human readable time format
        Format return will look like  "2018-01-29 10:30:25"
        """
        return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def get_metadata(filename: str = "", list_metadata: list = []) -> dict:
        """Get metadata from a file.

        Parameters
        ----------
        filename : str
            file name
        list_metadata : list
            list of metadata to extract

        Returns
        -------
        result : dict
        """
        if filename == "":
            return {}

        image = Image.open(filename)
        metadata = image.tag_v2
        result = {}
        if list_metadata == []:
            for _key in metadata.keys():
                result[_key] = metadata.get(_key)
            return result

        for _meta in list_metadata:
            result[_meta] = metadata.get(_meta.value)

        image.close()
        return result

    @staticmethod
    def retrieve_metadata(list_files: list = [], list_metadata: list = []) -> dict:
        """Retrieve metadata from a list of files.

        Parameters
        ----------
        list_files : list
            list of files
        list_metadata : list
            list of metadata to extract

        Returns
        -------
        _dict : dict"""
        if list_files == []:
            return {}

        _dict = OrderedDict()
        for _file in list_files:
            _meta = MetadataHandler.get_metadata(
                filename=_file, list_metadata=list_metadata
            )
            _dict[_file] = _meta

        return _dict

    @staticmethod
    def get_value_of_metadata_key(
        filename: str = "", list_key: Optional[list] = None
    ) -> dict:
        """Get value of metadata key.

        Parameters
        ----------
        filename : str
            file name
        list_key : list
            list of metadata key to extract

        Returns
        -------
        result : dict
        """
        if filename == "":
            return {}

        result = {}
        with Image.open(filename) as image:
            metadata = image.tag_v2
            if list_key is None or list_key == []:
                for _key in metadata.keys():
                    result[_key] = metadata.get(_key)
            else:
                for _meta in list_key:
                    result[_meta] = metadata.get(_meta)

        return result

    @staticmethod
    def retrieve_value_of_metadata_key(
        list_files: list=[], list_key: list=[]
    ) -> dict:
        """Retrieve value of metadata key.

        Parameters
        ----------
        list_files : list
            list of files
        list_key : list
            list of metadata key to extract

        Returns
        -------
        _dict : dict
        """
        if list_files == []:
            return {}

        _dict = OrderedDict()
        for _file in tqdm(list_files):
            _meta = MetadataHandler.get_value_of_metadata_key(
                filename=_file, list_key=list_key
            )
            _dict[_file] = _meta

        return _dict
