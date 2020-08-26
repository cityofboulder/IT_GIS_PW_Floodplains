import floodplains.config as config
import floodplains.utils.esriapi as api
import floodplains.utils.editdb as edit
import floodplains.utils.managedb as db

import arcgis


# Initiate a logger for etl
log = config.logging.getLogger(__name__)


def extract():
    """The main function used to extract new SFHAs from FEMA's REST
    Endpoint.

    The function uses data from FEMA's map services and Boulder's map
    service for city limits to query whether new LOMRs have been
    effected inside the city. If there are new LOMRs within the city,
    the function returns a spatial dataframe of all the SFHA
    delineations that were inside those new LOMRs. If no new LOMRs are
    found, than nothing is returned.
    """
    # Step 1: Identify relevant feature services
    city = arcgis.features.FeatureLayer(config.urls["city"])
    nfhl = arcgis.features.FeatureLayerCollection(config.urls["nfhl"])
    lomr = nfhl.layers[1]
    sfha = nfhl.layers[27]

    # Step 2: Create spatial filter object for city limits
    log.info("Creating spatial filter of city limits.")
    geom_filter = api.create_spatial_filter(city, config.sr)

    # Step 3: Extract LOMRs based on spatial filters and SQL query
    log.info("Querying the LOMR feature service.")
    date_str = '2018-08-16'  # <- will change based on SDE
    where = f"STATUS = 'Effective' AND EFF_DATE > '{date_str}'"
    boulder_lomrs = api.query_lomr(lomr, where, geom_filter, config.sr)

    # Step 4: If there are "more than zero" new LOMRs, continue ETL process
    if len(boulder_lomrs.features) > 0:
        log.info("Extracting SFHAs.")
        where = ("DFIRM_ID = '08013C'")
        fields = ['FLD_AR_ID', 'STUDY_TYP', 'FLD_ZONE',
                  'ZONE_SUBTY', 'SFHA_TF', 'STATIC_BFE', 'DEPTH']
        fema_flood, summary = api.extract_sfha(
            sfha, boulder_lomrs, where, fields, config.sr)
        return fema_flood, boulder_lomrs
    else:
        return None, None


def transform(sfha_sdf, lomr_fs):
    """Transforms SFHA delineations to meet City of Boulder standards.

    All transformations are done to the DataFrame in-place.

    Parameters
    ----------
    sfha_sdf : Pandas DataFrame
        Boulder's new special flood hazard areas
    lomr_fs : arcgis.features.FeatureSet
        Boulder's new LOMR areas
    """
    # Step 5: Query the city's floodplain feature service
    city_flood = arcgis.features.FeatureLayer(config.urls["city_flood"])
    compare = city_flood.query(out_fields=['DRAINAGE'], out_sr=config.sr)

    # Step 6: Calculate all fields
    log.info("Calculating DRAINAGE.")
    api.calc_drainages(sfha_sdf, compare, config.sr)

    log.info("Calculating ADOPTDATE.")
    sfha_sdf = api.calc_adoptdate(sfha_sdf, lomr_fs)

    log.info("Calculating INEFFDATE.")
    dups = list(sfha_sdf[sfha_sdf.duplicated(["FLD_AR_ID"])]["FLD_AR_ID"])
    dup_dates = {i: sorted(
        list(sfha_sdf[sfha_sdf["FLD_AR_ID"] == i]["ADOPTDATE"])) for i in dups}
    sfha_sdf["INEFFDATE"] = sfha_sdf.apply(
        api.calc_ineffdate, date_dict=dup_dates, axis=1)

    log.info("Calculating FLOODPLAIN.")
    sfha_sdf["FLOODPLAIN"] = sfha_sdf.apply(api.calc_floodplain, axis=1)

    log.info("Calculating FEMAZONE.")
    sfha_sdf["FEMAZONE"] = sfha_sdf.apply(api.calc_femazone, axis=1)

    log.info("Calculating LIFECYCLE.")
    sfha_sdf.loc[sfha_sdf["INEFFDATE"].notnull(), "LIFECYCLE"] = "Inactive"
    sfha_sdf.loc[sfha_sdf["INEFFDATE"].isnull(), "LIFECYCLE"] = "Active"

    log.info("Calculating SOURCE.")
    sfha_sdf["SOURCE"] = "FEMA"

    # Step 7: Drop all non-essential fields and rows
    sfha_sdf = sfha_sdf[sfha_sdf["ZONE_SUBTY"]
                        != "AREA OF MINIMAL FLOOD HAZARD"]
    sfha_sdf = sfha_sdf[config.fc_fields]
    return sfha_sdf


def load(sfha_sdf, lomr_fs):
    """Loads the transformed SFHAs into the city's dataset.

    Parameters
    ----------
    sfha_sdf : Pandas DataFrame
        Transformed special flood hazard areas
    lomr_fs : arcgis.features.FeatureSet
        Boulder's LOMR areas
    """
    # Step 8: Create a new versioned connection for city floodplains
    edit_connect = db.create_versioned_connection(
        config.version_params, config.db_params)

    # Step 9: For every lomr, perform edits to city floodplains
    where = ("LIFECYCLE = 'Active' AND FLOODPLAIN IN "
             "('500 Year', '100 Year', 'Conveyance Zone')")
    for lomr in lomr_fs.features:
        lomr_id = lomr.attributes["CASE_NO"]
        log.info(f"Making edits for {lomr_id}.")
        edit.perform_edits(workspace=edit_connect,
                           fc=config.fc_name,
                           fields=config.fc_fields,
                           where_clause=where,
                           lomr_layer=lomr,
                           sfha_sdf=sfha_sdf)

# Step 6b: Make edits to the version
# Step 6c: Cut existing floodplains with LOMR boundaries
# Step 6d: Make existing floodplains inside LOMR bounds "Inactive"
# Step 6e: Add the transformed sfhas into the version

# NOTIFY
# Step 7a: Notify steward of new version edits
# Step 7b: Notify SMEs that edits are pending and new LOMRs are available
