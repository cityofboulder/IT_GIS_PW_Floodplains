import os
from datetime import datetime

import arcgis
import arcpy
import floodplains.config as config
import pandas as pd

log = config.logging.getLogger(__name__)


def _edit_existing_polys(fc, fields, where_clause, polygon, date, cursor):
    """Cuts polygons inside the feature class that cross the supplied
    geometry boundary, and updates attributes of the resulting polygons.

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
    date : datetime
        The effective date of the lomr
    cursor : arcpy.da.InsertCursor
        The insert cursor used to insert new geometries to the feature
        class
    """
    # Enumerate fields to make cursor access easier to understand
    i = {field: index for index, field in enumerate(fields)}
    with arcpy.da.UpdateCursor(fc, fields, where_clause) as update:
        for row in update:
            if row[i["SHAPE@"]].overlaps(polygon):
                # save all attributes (other than geometry) before cutting
                row_dict = {index: value for index, value in enumerate(row)}
                # save a list of clipped floodplain geometries
                geoms = row[i["SHAPE@"]].cut(polygon.boundary())
                # delete the geometry that got cut to avoid duplicates
                update.deleteRow()
                for g in geoms:
                    if g.area > 0:
                        # create a new row dict
                        new_record = row_dict
                        # insert the new geometry
                        new_record[i["SHAPE@"]] = g
                        # change LIFECYCLE and INEFFDATE of the inner geom
                        if polygon.contains(g.centroid):
                            new_record[i["INEFFDATE"]] = date
                        # convert back to a list in the proper order
                        new_row = tuple(new_record.values())
                        # add the new row to the layer
                        cursor.insertRow(new_row)


def _add_new_polys(records, fields, polygon, cursor):
    """Inserts newly transformed records into the cursor opened on
    a feature class.

    Parameters
    ----------
    records : list
        A list of dicts, where every dict is one row of the dataframe
    fields : list
        The list of field names ordered based on how they appear in the
        cursor object
    polygon : arcpy.Polygon()
        The polygon of the lomr being investigated
    cursor : arcpy.da.InsertCursor
        An insert cursor opened on the versioned feature class being
        edited
    """
    for record in records:
        point = record["SHAPE@"].labelPoint
        if polygon.contains(point):
            row = [record[column_name] for column_name in fields]
            cursor.insertRow(row)


def sdf_to_dict(sdf):
    """Transform the spatial dataframe coming from the esri api into
    a list of dicts that can be easily consumed into an update cursor.

    Parameters
    ----------
    sdf : pandas.DataFrame
        The spatial dataframe of new flood areas

    Returns
    -------
    list
        A list of dicts, where every dict is one row of the dataframe
    """
    records = sdf.to_dict("records")
    for record in records:
        # Convert timestamps to datetime
        if pd.notnull(record["EFFDATE"]):
            record["EFFDATE"] = record["EFFDATE"].to_pydatetime()
        else:
            record["EFFDATE"] = None
        if pd.notnull(record["INEFFDATE"]):
            record["INEFFDATE"] = record["INEFFDATE"].to_pydatetime()
        else:
            record["INEFFDATE"] = None
        # Convert geometry to arcpy
        record["SHAPE@"] = record["SHAPE"].as_arcpy
    return records


def perform_edits(workspace: str, fc: str, fields: list, where_clause: str,
                  lomr_layer, records):
    """Makes all the versioned edits necessary to insert new polygons
    into the floodplain feature class inside city databases.

    1: Cuts polygons that cross the lomr. This ensures that
    when new FEMA polygons are dropped in, they don't overlap with
    existing geometries. This also ensures that polygons tie in properly
    at confluences.

    2: Changes the LIFECYCLE of existing floodplains within the LOMR
    to "Inactive", and alters the INEFFDATE to match that of the LOMR

    3: Inserts new FEMA geometries with associated attributes

    Parameters
    ----------
    workspace : str
        The file path to the sde connection
    fc : str
        The name of the feature class
    fields : list
        The fields used in various update and insert cursors
    where_clause : str
        A SQL query used to edit specific records in various cursors
    lomr_layer : arcgis.features.Layer
        A Layer object representing one LOMR geometry and its attributes
    records : list
        A list of dicts, where every dict is one row of the dataframe
    """
    # Path to floodplain feature class
    fc_path = os.path.join(workspace, fc)
    # LOMR effective date
    lomr_date = datetime.fromtimestamp(lomr_layer.attributes["EFF_DATE"]/1000)
    # Deconstruct lomr layer into a linear boundary
    lomr_geom = arcgis.geometry.Geometry(lomr_layer.geometry).as_arcpy

    # try:
    session = arcpy.da.Editor(workspace)
    session.startEditing(False, True)
    session.startOperation()

    # Open an insert cursor for edits
    log.info("Creating Insert cursor.")
    insert = arcpy.da.InsertCursor(fc_path, fields)

    # Edit existing polygons in the feature class
    log.info("Editing existing polygons within the LOMR.")
    _edit_existing_polys(fc=fc_path, fields=fields, where_clause=where_clause,
                         polygon=lomr_geom, date=lomr_date, cursor=insert)

    # Add the transformed polygons
    log.info("Adding new polygons into the LOMR area.")
    _add_new_polys(records=records, fields=fields,
                   polygon=lomr_geom, cursor=insert)

    session.stopOperation()
    session.stopEditing(True)
    del session, insert
    # except Exception:
    #     log.error("The edit operation failed.")
