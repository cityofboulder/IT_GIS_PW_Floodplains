import os

import arcpy

import floodplains.config as config

log = config.logging.getLogger(__name__)


def _create_version(version_kwargs: dict):
    """Creates a version using the dict variables defined in the project
    config.

    The tool uses status codes provided by ESRI to keep trying a version
    creation until the tool succeeds (status code = 4). Status codes can
    be found here:

    https://pro.arcgis.com/en/pro-app/arcpy/classes/result.htm

    Parameters
    ----------
    version_kwargs : dict
        Parameters required for the arcpy.CreateVersion_management
        function
    """
    log.info("Creating a new version.")
    status = 0
    while status != 4:
        result = arcpy.CreateVersion_management(**version_kwargs)
        status = result.status
        if status != 4:
            log.warning((f"Version creation failed with ESRI code {status}. "
                         "Retrying."))


def create_versioned_connection(version_kwargs: dict,
                                connect_kwargs: dict) -> str:
    """Creates an sde connection on disk and returns the path to that
    file.

    Parameters
    ----------
    version_kwargs : dict
        Parameters required for the arcpy.CreateVersion func

    connect_kwargs : dict
        Parameters required for the arcpy.CreateDatabaseConnection func

    Returns
    -------
    str
        File path to the new database connection file
    """
    _create_version(version_kwargs)

    log.info("Creating a versioned database connection.")
    arcpy.CreateDatabaseConnection_management(**connect_kwargs)
    filepath = os.path.join(connect_kwargs["out_folder_path"],
                            connect_kwargs["out_name"])

    return filepath


def remove_version():
    pass
