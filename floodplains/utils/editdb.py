import arcpy
import os

import floodplains.config as config

log = config.logging.getLogger(__name__)


def _cut_polys():
    # Cuts the city flood polygons
    pass


def _inactivate_polys():
    # Make all existing polys inside the LOMR boundaries 'Inactive'
    pass


def _add_new_polys():
    # Add new transformed polygons from FEMA
    pass


def _dissolve_polys():
    # Dissolve polygons inside the new LOMR by DRAINAGE, FEMAZONE, FLOODPLAIN,
    # and LIFECYCLE
    pass


def perform_edits(workspace: str, fc: str, fields: str, where_clause: str):
    # Make all edits to the city floodplains
    fc_path = os.path.join(workspace, fc)
    try:
        session = arcpy.da.Editor(workspace)
        session.startEditing(False, True)
        session.startOperation()

        # open an insert cursor for edits
        insert = arcpy.da.InsertCursor(fc_path, fields)

        session.stopOperation()
        session.stopEditing(True)
        del session, insert
    except Exception:
        log.error("The edit operation failed.")
