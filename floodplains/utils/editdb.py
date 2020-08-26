import arcpy
import os

import arcgis

import floodplains.config as config

log = config.logging.getLogger(__name__)


def _cut_polys(fc, fields, where_clause, boundary, cursor):
    """Cuts polygons inside the feature class that cross the supplied
    geometry boundary.

    Parameters
    ----------
    fc : str
        The full path to the feature class
    fields : list
        The fields to include in the update cursor
    where_clause : str
        A SQL statement used to filter the contents of the database
        cursor
    boundary : arcpy.Geometry()
        The geometry boundary used to cut polygons in the feature class
    cursor : arcpy.da.InsertCursor
        The insert cursor used to insert new geometries to the feature
        class
    """
    # Enumerate fields to make cursor access easier to understand
    i = {field: index for index, field in fields}
    with arcpy.da.UpdateCursor(fc, fields, where_clause) as update:
        for row in update:
            if row[i["SHAPE"]].overlaps(boundary):
                # save all attributes (other than geometry) before cutting
                row_dict = {index: value for index, value in enumerate(row)}
                # save a list of clipped floodplain geometries
                geoms = row[i["SHAPE"]].cut(boundary)
                # delete the geometry that got cut to avoid duplicates
                update.deleteRow()
                for g in geoms:
                    if g.area > 0:
                        # create a new row dict
                        new_record = row_dict
                        # insert the new geometry
                        new_record[i["SHAPE"]] = g
                        # convert back to a list in the proper order
                        new_row = tuple(new_record.values())
                        # add the new row to the layer
                        cursor.insertRow(new_row)


def _inactivate_polys(fc, fields, where_clause, polygon, date):
    """Inactivate all polygons that are being replaced, and make the
    ineffective date the same as the LOMR's effective date.

    Parameters
    ----------
    fc : str
        The full path to the feature class
    fields : list
        The fields to include in the update cursor
    where_clause : str
        A SQL statement used to filter the contents of the database
        cursor
    polygon : arcpy.Polygon()
        The polygon of the lomr being investigated
    date : int
        The effective date of the lomr
    """
    # Enumerate fields to make cursor access easier to understand
    i = {field: index for index, field in fields}
    with arcpy.da.UpdateCursor(fc, fields, where_clause) as update:
        for row in update:
            point = row[i["SHAPE"]].labelPoint
            if polygon.contains(point):
                row[i["LIFECYCLE"]] = "Inactive"
                row[i["INEFFDATE"]] = date
                update.updateRow(row)


def _add_new_polys():
    # Add new transformed polygons from FEMA
    pass


def _dissolve_polys():
    # Dissolve polygons inside the new LOMR by DRAINAGE, FEMAZONE, FLOODPLAIN,
    # and LIFECYCLE
    pass


def perform_edits(workspace: str, fc: str, fields: list, where_clause: str,
                  lomr_layer):
    # Path to floodplain feature class
    fc_path = os.path.join(workspace, fc)
    # Deconstruct lomr layer into a linear boundary
    lomr_geom = arcgis.geometry.Geometry(lomr_layer.geometry).as_arcpy
    boundary = lomr_geom.boundary()

    try:
        session = arcpy.da.Editor(workspace)
        session.startEditing(False, True)
        session.startOperation()

        # Open an insert cursor for edits
        insert = arcpy.da.InsertCursor(fc_path, fields)

        # Cut polygons in the feature class
        _cut_polys(fc=fc_path, fields=fields, where_clause=where_clause,
                   boundary=boundary, cursor=insert)

        session.stopOperation()
        session.stopEditing(True)
        del session, insert
    except Exception:
        log.error("The edit operation failed.")
