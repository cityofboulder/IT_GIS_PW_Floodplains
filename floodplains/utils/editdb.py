import os
from datetime import datetime

import arcgis
import arcpy
import floodplains.config as config
import pandas as pd

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
    i = {field: index for index, field in enumerate(fields)}
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
    date : datetime
        The effective date of the lomr
    """
    # Enumerate fields to make cursor access easier to understand
    i = {field: index for index, field in enumerate(fields)}
    with arcpy.da.UpdateCursor(fc, fields, where_clause) as update:
        for row in update:
            point = row[i["SHAPE"]].labelPoint
            if polygon.contains(point):
                row[i["LIFECYCLE"]] = "Inactive"
                row[i["INEFFDATE"]] = date
                update.updateRow(row)


def _add_new_polys(sfha_sdf, fields, cursor):
    """Inserts newly transformed records into the cursor opened on
    a feature class.

    Parameters
    ----------
    sfha_sdf : pandas.DataFrame
        The pandas DataFrame contained transformed SFHA delineations
        from FEMA
    fields : list
        The list of field names ordered based on how they appear in the
        cursor object
    cursor : arcpy.da.InsertCursor
        An insert cursor opened on the versioned feature class being
        edited
    """
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
        records = sfha_sdf.to_dict("records")
        for record in records:
            # Convert timestamps to datetime
            if pd.notnull(record["ADOPTDATE"]):
                record["ADOPTDATE"] = datetime.fromtimestamp(
                    record["ADOPTDATE"]/1000)
            else:
                record["ADOPTDATE"] = None
            if pd.notnull(record["INEFFDATE"]):
                record["INEFFDATE"] = datetime.fromtimestamp(
                    record["INEFFDATE"]/1000)
            else:
                record["INEFFDATE"] = None
            # Convert geometry to arcpy
            record["SHAPE"] = record["SHAPE"].as_arcpy
        return records

    new_records = sdf_to_dict(sfha_sdf)
    for record in new_records:
        row = [record[column_name] for column_name in fields]
        cursor.insertRow(row)


def perform_edits(workspace: str, fc: str, fields: list, where_clause: str,
                  lomr_layer, sfha_sdf):
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
    sfha_sdf : pandas.DataFrame
        The spatial dataframe of new flood areas
    """
    # Path to floodplain feature class
    fc_path = os.path.join(workspace, fc)
    # LOMR effective date
    lomr_date = datetime.fromtimestamp(lomr_layer.attributes["EFF_DATE"]/1000)
    # Deconstruct lomr layer into a linear boundary
    lomr_geom = arcgis.geometry.Geometry(lomr_layer.geometry).as_arcpy
    boundary = lomr_geom.boundary()

    # try:
    session = arcpy.da.Editor(workspace)
    session.startEditing(False, True)
    session.startOperation()

    # Open an insert cursor for edits
    log.info("Creating Insert cursor.")
    insert = arcpy.da.InsertCursor(fc_path, fields)

    # Cut polygons in the feature class
    log.info("Cutting polys by LOMR boundary.")
    _cut_polys(fc=fc_path, fields=fields, where_clause=where_clause,
               boundary=boundary, cursor=insert)

    # Inactivate the current floodplain polygons
    log.info("Inactivating old polygons.")
    _inactivate_polys(fc=fc_path, fields=fields, where_clause=where_clause,
                      polygon=lomr_geom, date=lomr_date)

    # Add the transformed polygons
    log.info("Adding new polys.")
    _add_new_polys(sfha_sdf=sfha_sdf, fields=fields, cursor=insert)

    session.stopOperation()
    session.stopEditing(True)
    del session, insert
    # except Exception:
    #     log.error("The edit operation failed.")
