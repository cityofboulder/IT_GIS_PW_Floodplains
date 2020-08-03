import floodplains.config as config

import arcgis
import pandas as pd

# Initialize log for esriapicalls
log = config.logging.getLogger(__name__)


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
                           out_sr=sr)
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
    all_sfha = in_layer.query(where=clause, out_fields=out_fields, out_sr=sr)

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


def calc_adoptdate(sfha, lomr):
    """Calculates the date a given SFHA was adopted based on the LOMR
    boundary in which it resides.

    If an SFHA resides in two LOMR boundaries at once, it will be
    assigned the ADOPTDATE of which LOMR area is most recent.

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
        "ADOPTDATE" field appended.
    """
    # Spatial join of LOMRs and SFHAs
    if not isinstance(sfha, pd.DataFrame()):
        sfha = sfha.sdf
    new_sdf = sfha.spatial.join(lomr.sdf)
    # Sort by effective date, most recent first
    new_sdf.sort_values(by=['EFF_DATE'], inplace=True, ascending=False)
    # Remove duplicate FLD_AR_IDs, keep the first dup record encountered.
    new_sdf.drop_duplicates(subset=['FLD_AR_ID'], inplace=True, keep='first')
    new_sdf.rename(columns={"EFF_DATE": "ADOPTDATE"}, inplace=True)
    # Return new spatial dataframe
    return new_sdf


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
    [type]
        [description]
    """
    if row["SFHA_TF"] == "T":
        if row["ZONE_SUBTY"] == 'FLOODWAY':
            floodplain = 'Conveyance Zone'
        else:
            floodplain = '100-Year'
    else:
        if row["ZONE_SUBTY"] in ('0.2 PCT ANNUAL CHANCE FLOOD HAZARD',
                                 'AREA WITH REDUCED FLOOD RISK DUE TO LEVEE'):
            floodplain = '500-Year'
        else:
            floodplain = None
    return floodplain
