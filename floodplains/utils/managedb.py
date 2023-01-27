import os

import arcpy
from arcpy import ClearWorkspaceCache_management
import floodplains.config as config

log = config.logging.getLogger(__name__)


def clear_cache(func):
    """Clears the workspace cache.

    Used as a decorator on any function that deals with version management.
    See this post for reasoning:
    https://community.esri.com/t5/geoprocessing-questions/createversion-tool-doesn-t-like-my-workspace/m-p/733989#M24189

    Parameters
    ----------
    func : function
        The decorated function
    """
    def wrapper(*args, **kwargs):
        log.debug("Clearing workspace cache...")
        ClearWorkspaceCache_management()
        value = func(*args, **kwargs)
        return value
    return wrapper

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


@clear_cache
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


@clear_cache
def remove_version(connection: str, version: str) -> None:
    """Removes the specified version from the database connection

    Parameters
    ----------
    connection : str
        File path to the sde connection file

    version : str
        Name of the version being deleted (without the owner prepended)
    """
    try:
        del_version = [v for v in arcpy.da.ListVersions(
            connection) if version.lower() in v.name.lower()][0]
        if del_version.isOwner:
            log.info("Removing old edit version.")
            arcpy.DeleteVersion_management(connection, del_version.name)
        else:
            log.warning(("The version could not be deleted through the "
                         "connection provided because it does not own the "
                         "version."))
    except IndexError:
        log.info(f"No edit version called {version} currently exists.")
