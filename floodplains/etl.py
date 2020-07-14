import floodplains.config as config
import floodplains.utils.esriapi as api
import arcgis


# Initiate a logger for etl
log = config.logging.getLogger(__name__)


def extract():
    # Step 1: Identify relevant feature services
    sr = config.sde["spatialref"]
    city = arcgis.features.FeatureLayer(config.urls["city"])
    nfhl = arcgis.features.FeatureLayerCollection(config.urls["nfhl"])
    lomr = nfhl.layers[1]
    sfha = nfhl.layers[27]

    # Step 2: Create spatial filter object for city limits
    log.info("Creating spatial filter of city limits.")
    geom_filter = api.create_spatial_filter(city, sr)

    # Step 3: Extract LOMRs based on spatial filters and SQL query
    log.info("Querying the LOMR feature service.")
    date_str = '2018-08-16'  # <- will change based on SDE
    where = f"STATUS = 'Effective' AND EFF_DATE > '{date_str}'"
    boulder_lomrs = api.query_lomr(lomr, where, geom_filter, sr)

    # Step 4: If there are "more than zero" new LOMRs, continue ETL process
    if len(boulder_lomrs.features) > 0:
        log.info("Extracting SFHAs.")
        where = "DFIRM_ID = '08013C'"
        fields = ['FLD_AR_ID', 'STUDY_TYP', 'FLD_ZONE',
                  'ZONE_SUBTY', 'SFHA_TF', 'STATIC_BFE', 'DEPTH']
        fema_flood, summary = api.extract_sfha(
            sfha, boulder_lomrs, where, fields, sr)
        return fema_flood
    else:
        return None


# TRANSFORM
# Step 5a: Transform sfha delineations natively (dicts or pandas)
# Step 5b: Dissolve new delins based on COB standards

# LOAD
# Step 6a: Create a new versioned connection for city floodplains
# Step 6b: Make edits to the version
# Step 6c: Cut existing floodplains with LOMR boundaries
# Step 6d: Make existing floodplains inside LOMR bounds "Inactive"
# Step 6e: Add the transformed sfhas into the version

# NOTIFY
# Step 7a: Notify steward of new version edits
# Step 7b: Notify SMEs that edits are pending and new LOMRs are available
