import arcgis
import floodplains.config as config
import numpy as np
import pandas as pd

from datetime import datetime

# Initialize log for esriapicalls
log = config.logging.getLogger(__name__)


def last_checked_date(in_layer):
    """Checks the last time the GISSCR user created floodplain delineations in
    the city's floodplains in order to approximate the last time the script
    was run.

    Parameters
    ----------
    in_layer : FeatureLayer
        An arcgis feature layer

    Returns
    -------
    str
        The last date the layer was edited by the GISSCR user (e.g. 2019-04-01)
    """
    where = ("CREATED_USER = 'GISSCR' AND (FLOODZONE LIKE 'A%' OR FLOODZONE "
             "IN ('X', 'B'))")
    query = in_layer.query(out_fields=["CREATED_USER", "CREATED_DATE"],
                           where=where,
                           return_geometry=False)
    ts = max([f.attributes["CREATED_DATE"] for f in query.features])/1000
    formatted = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    return formatted


def create_spatial_filter(in_layer: arcgis.features.layer.FeatureLayer,
                          sr: int) -> dict:
    """Creates a spatial filter of dissolved geometries for use in
    querying ESRI's REST API.

    The returned dict is an ESRI spec'd schema that can be ingesetd by
    their query API call.

    Parameters
    ----------
    in_layer : arcgis.features.layer.FeatureLayer
        A feature layer derived from a feature or map service endpoint
    sr : int
        The output spatial reference

    Returns
    -------
    dict
        A dict that is understood by ESRI's REST API query
    """
    # ESRI requires that an anonymous instance of a Portal is started
    # in order to use the geometry union function
    temp_gis = arcgis.gis.GIS()

    # Get the set of features within the FeatureLayer
    feature_set = in_layer.query(out_sr=sr)

    # Union all output features
    geoms = [poly.geometry for poly in feature_set.features]
    unioned = arcgis.geometry.union(
        spatial_ref=sr, geometries=geoms, gis=temp_gis)

    # Create a filter for use in ESRI's API query
    geom_filter = arcgis.geometry.filters.intersects(unioned, sr=sr)

    del temp_gis

    return geom_filter


def query_lomr(in_layer: arcgis.features.layer.FeatureLayer,
               clause: str, g_filter: dict, sr: int):
    """Returns all the LOMR boundaries that appear inside the spatial
    filter based on the clause used.

    Parameters
    ----------
    in_layer : arcgis.features.layer.FeatureLayer
        A feature layer derived from a feature or map service endpoint
    clause : str
        Conditions used to restrict output, written in SQL syntax (e.g.
        "STATUS = 'Effective'")
    g_filter : dict
        The boundaries that make up where the user is checking for new
        LOMR boundaries
    sr : int
        The output spatial reference

    Returns
    -------
    arcgis.features.layer.FeatureLayer
        An ESRI FeatureLayer
    """
    # Query the feature service
    lomrs = in_layer.query(where=clause,
                           geometry_filter=g_filter,
                           out_sr=sr,
                           datum_transformation=1478)
    # Drop duplicate Case Numbers and Geometries if features are returned
    if lomrs.features:
        temp = lomrs.sdf
        temp['GEOM_STR'] = str(temp['SHAPE'])
        temp.drop_duplicates(subset=['CASE_NO', 'GEOM_STR'], inplace=True)
        temp.sort_values(by='EFF_DATE', inplace=True, ascending=False)
        lomrs = arcgis.features.FeatureSet.from_dataframe(temp)

    return lomrs


def extract_sfha(in_layer: arcgis.features.layer.FeatureLayer,
                 boundaries: arcgis.features.layer.FeatureSet,
                 clause: str, out_fields: list, sr: int):
    """Extracts all the SFHA floodplains that are within some boundaries
    into a pandas dataframe.

    This package either requires shapely or arcpy, depending on the OS.
    The output pandas dataframe is spatially enabled, and contains no
    duplicate geometries based on FEMA's ID scheme. Duplicattes can
    occur periodically because LOMRs can overlap.

    Parameters
    ----------
    in_layer : arcgis.features.layer.FeatureLayer
        A feature layer derived from a feature or map service endpoint
    boundaries : arcgis.features.layer.FeatureSet
        The boundaries in which to evaluate "insidedness"
    clause : str
        Conditions used to restrict output, written in SQL syntax (e.g.
        "DFIRM_ID = '08013C'")
    out_fields : list
        The fields to output as columns in the spatial dataframe
    sr : int
        The output spatial reference

    Returns
    -------
    pandas.DataFrame
        With duplicate geometries removed
    dict
        A dictionary summarizing number of SFHAs in a given polygon
        based on ID
    """
    # Query the feature service
    all_sfha = in_layer.query(where=clause,
                              out_fields=out_fields,
                              out_sr=sr,
                              datum_transformation=1478)

    # Create an empty dataframe with the same schema as the output
    all_sfha_sdf = all_sfha.sdf
    subset = all_sfha_sdf.copy()
    subset.drop(list(range(len(subset))), inplace=True)

    # Loop through the LOMR boundaries and ID all SFHAs that are inside
    catalog = {}
    for lomr in boundaries.features:
        case = lomr.attributes['CASE_NO']
        g = arcgis.geometry.Geometry(lomr.geometry)

        # buffer LOMR geom by one foot to avoid topological errors where polys
        # share an edge
        buf = g.buffer(1)
        count = 0

        for row in all_sfha.features:
            area_id = row.attributes['FLD_AR_ID']
            f = arcgis.geometry.Geometry(row.geometry)
            if buf.contains(f):
                subset = subset.append(
                    all_sfha_sdf[all_sfha_sdf['FLD_AR_ID'] == area_id],
                    ignore_index=True)
                count += 1

        # log counts by LOMR Case Number
        catalog[case] = count

    # drop any rows that represent duplicate flood areas
    subset.drop_duplicates(subset=['FLD_AR_ID'], inplace=True)

    return subset, catalog


def calc_effdate(sfha, lomr):
    """Calculates the date a given SFHA was adopted based on the LOMR
    boundary in which it resides.

    Parameters
    ----------
    sfha : ESRI Spatial Dataframe
        The Special Flood Hazard Area information extracted from an ESRI
        API call
    lomr : ESRI Feature Set
        The Letter of Map Revision areas extracted from an API call to
        FEMA's Rest Endpoint

    Returns
    -------
    ESRI Spatial Dataframe
        A copy of the incoming SFHA dataframe, but with a new
        "EFFDATE" field appended.
    """
    # Spatial join of LOMRs and SFHAs
    if not isinstance(sfha, pd.DataFrame):
        sfha = sfha.sdf
    if not isinstance(lomr, pd.DataFrame):
        lomr = lomr.sdf
    new_sdf = sfha.spatial.join(lomr)

    new_sdf.rename(columns={"EFF_DATE": "EFFDATE"}, inplace=True)
    # Return new spatial dataframe
    return new_sdf


def calc_ineffdate(row, date_dict: dict):
    """Calculates the date a given SFHA was deemed ineffective based on
    whether the SFHA resides inside 2+ different LOMRs.

    Parameters
    ----------
    row : Pandas Series
        A row of a pandas DataFrame

    date_dict : dict
        A dictionary of FLD_AR_IDs and all the LOMR EFF_DATEs associated
        with each. The EFF_DATEs should be ordered chronologically.

    Returns
    -------
    pandas.Timestamp
        The timestamp a polygon went ineffective, or None
    """
    fema_id = row["FLD_AR_ID"]
    adopt_date = row["ADOPTDATE"]
    ineff_date = None
    try:
        idx = date_dict[fema_id].index(adopt_date)
        try:
            ineff_date = date_dict[fema_id][idx+1]
        except IndexError:
            # The polygon has the most recent ADOPTDATE of all the LOMRs that
            # touch the polygon, and therefore doesn't have an INEFFDATE
            pass
    except KeyError:
        # The polygon was not duplicated
        pass
    return ineff_date


def calc_floodplain(row):
    """Extracts the floodplain designation of an SFHA based on each
    row's attributes.

    This function acts on individual rows of a pandas DataFrame using
    the apply built-in.

    Parameters
    ----------
    row : Pandas Series
        A row of a pandas DataFrame

    Returns
    -------
    str
        The SFHA floodplain designation
    """
    if row["SFHA_TF"] == "T":
        if row["ZONE_SUBTY"] == 'FLOODWAY':
            floodplain = 'Conveyance Zone'
        else:
            floodplain = '100 Year'
    else:
        if row["ZONE_SUBTY"] in ('0.2 PCT ANNUAL CHANCE FLOOD HAZARD',
                                 'AREA WITH REDUCED FLOOD RISK DUE TO LEVEE'):
            floodplain = '500 Year'
        else:
            floodplain = None
    return floodplain


def calc_floodzone(row):
    """Extracts the FEMAZONE of an SFHA based on each row's attributes.

    This function acts on individual rows of a pandas DataFrame using
    the apply built-in.

    Parameters
    ----------
    row : Pandas Series
        A row of a pandas DataFrame

    Returns
    -------
    str
        The flood zone designation for an SFHA
    """
    if row["FLD_ZONE"] == 'AO':
        zone = 'AO' + str(round(row['DEPTH']))
    elif row["FLD_ZONE"] == 'AH':
        zone = 'AH' + str(round(row["STATIC_BFE"]))
    else:
        zone = row["FLD_ZONE"]
    return zone


def calc_drainages(to_calc, comparison, spatial_ref: int):
    """Checks if geometries in the "to_calc" DataFrame are inside the
    geometries of the "comparison" FeatureSet, and assigns the DRAINAGE
    variable accordingly.

    Modifies the input DataFrame called "to_calc" with a new DRAINAGE
    column.

    Parameters
    ----------
    to_calc : pandas.DataFrame
        The features that require geometry comparisons.
    comparison : arcgis.features.FeatureSet
        The features to compare geometries against.
    spatial_ref : int
        Output spatial reference

    Returns
    -------
    None
        No output, this function modifies the "to_calc" input in-place.
    """
    # ESRI requires that an anonymous instance of a Portal is started
    # in order to use the geometry union function
    temp_gis = arcgis.gis.GIS()

    # Union the city drainages
    def union_drainages(row):
        """Unions a given DataFrame row into a new ESRI Geometry object.

        At time of writing this script, geometries coming out of the
        union function come out with an empty spatial reference. This
        is a workaround solution to this problem.

        This function acts on individual rows of a pandas DataFrame
        using the apply built-in.

        Parameters
        ----------
        row : pandas.Series
            A row of a pandas DataFrame

        Returns
        -------
        arcgis.geometry.Geometry
            An arcgis Geometry object
        """
        no_sr = arcgis.geometry.union(
            geometries=row["SHAPE"], spatial_ref=spatial_ref, gis=temp_gis)
        geom = arcgis.geometry.Geometry(
            {"rings": no_sr.rings, "spatialReference": {"wkid": spatial_ref}})
        return geom

    def rand_point_in_poly(row):
        """Get a random, representative point inside a polygon.

        This function requires the shapely library, and acts on
        individual rows of a pandas DataFrame using the apply built-in.

        Parameters
        ----------
        row : pandas.Series
            A row of a pandas DataFrame

        Returns
        -------
        arcgis.geometry.Geometry
            A point geometry projected to the parent function's
            spatial_ref
        """
        rand = row["SHAPE"].as_shapely.representative_point()
        point = arcgis.geometry.Geometry(
            {"x": rand.x, "y": rand.y,
                "spatialReference": {"wkid": spatial_ref}})
        return point

    def check_within(row):
        """Checks whether the representative point inside the supplied
        DataFrame row is within the unioned drainages of the city.

        This function acts on individual rows of a pandas DataFrame
        using the apply built-in.

        Parameters
        ----------
        row : pandas.Series
            A row of a pandas DataFrame

        Returns
        -------
        str
            The name of the drainage within which the point lies
        """
        for item in drain_fs.features:
            arcgis_point = rand_point_in_poly(row)
            g = arcgis.geometry.Geometry(item.geometry)
            if g.contains(arcgis_point):
                drain = item.attributes["DRAINAGE"]
                return drain

    # Create a new pandas DataFrame, where each row is grouped by drainage,
    # and the geometries for each drainage are put into a list
    drainages = pd.DataFrame(comparison.sdf.groupby("DRAINAGE")[
                             "SHAPE"].apply(list)).reset_index()
    # Convert the list of geometries for each DataFrame row into
    # an ESRI Geometry object.
    drainages["SHAPE"] = drainages.apply(union_drainages, axis=1)

    # Convert the DataFrame into a FeatureSet
    drain_fs = arcgis.features.FeatureSet.from_dataframe(drainages)

    # Calculate all drainages
    to_calc["DRAINAGE"] = to_calc.apply(check_within, axis=1)


def dissolve_sdf(df, by=None):
    """Dissolves geometries in a spatial dataframe based on the supplied
    fields.

    Parameters
    ----------
    df : pd.DataFrame
        A spatially enabled esri dataframe (contains a SHAPE field that
        consists of arcgis.geometry.Geometry objects)
    by : list, optional
        The list of fields to group by in the dissolve, default None
    """
    def dissolve_shapes(row, sr):
        """Helper function that dissolves a list of arcgis Geometry
        objects in an DataFrame apply function.

        Parameters
        ----------
        row : pd.Series
            A pandas Series representing a row of a dataframe

        Returns
        -------
        arcgis.geometry.Geometry
            An arcgis geometry object
        """
        # Set up a temporary GIS object
        tmp = arcgis.gis.GIS()
        # Dissolve the geoms
        geom = arcgis.geometry.functions.union(
            geometries=row.SHAPE, spatial_ref=sr, gis=tmp)
        return geom

    if by:
        # Temporarily fill n/a values so that grouping can happen even when
        # a field has an undetermined value. Exclude SHAPE field.
        na = df.fillna({field: "NONE" for field in by})

        # Group by the supplied fields
        grouped = na.groupby(by)

        # For rows that get grouped, create a list of their geometries
        listed_geoms = grouped.SHAPE.apply(list)
        listed_geoms = listed_geoms.reset_index()

        # Re-enable n/a values in the df
        dissolved = listed_geoms.replace("NONE", np.NaN)
    else:
        # Condense all geometries to a list
        geoms = [df.SHAPE.to_list()]
        # Create a new df of those listed shapes
        dissolved = pd.DataFrame([geoms], columns=["SHAPE"])

    # Dissolve the shapes based on field groupings
    dissolved.SHAPE = dissolved.apply(dissolve_shapes, sr=2876, axis=1)

    return dissolved
