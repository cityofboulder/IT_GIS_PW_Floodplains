import arcpy

import floodplains.config as config

log = config.logging.getLogger(__name__)


def create_version(version_kwargs: dict):
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


def create_versioned_connection():
    pass


def remove_version():
    pass
