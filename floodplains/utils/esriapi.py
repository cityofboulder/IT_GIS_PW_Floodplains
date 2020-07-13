import floodplains.config as config

import arcgis

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
    lomrs = in_layer.query(where=clause,
                           geometry_filter=g_filter,
                           out_sr=sr)
    # Drop duplicate Case Numbers and Geometries.
    temp = lomrs.sdf
    temp['GEOM_STR'] = str(temp['SHAPE'])
    temp.drop_duplicates(subset=['CASE_NO', 'GEOM_STR'], inplace=True)
    temp.sort_values(by='EFF_DATE', inplace=True, ascending=False)
    lomrs = arcgis.features.FeatureSet.from_dataframe(temp)

    return lomrs
