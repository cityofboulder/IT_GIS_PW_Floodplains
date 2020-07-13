import floodplains.config as config
import floodplains.utils.esriapi as api

import arcgis


# Initiate a logger for etl
log = config.logging.getLogger(__name__)


def main():
    # Step 1: Identify relevant feature services
    sr = config.sde["spatialref"]
    city = arcgis.features.FeatureLayer(config.urls["city"])
    nfhl = arcgis.features.FeatureLayerCollection(config.urls["nfhl"])
    lomr = nfhl.layers[1]
    sfha = nfhl.layers[27]

    # Step 2: Create spatial filter object for city limits
    geom_filter = api.create_spatial_filter(city, sr)

    # Step 3: Extract LOMRs based on spatial filters and SQL query
    date_str = '2018-08-16'  # <- will change based on SDE
    where = f"STATUS = 'Effective' AND EFF_DATE > '{date_str}'"
    boulder_lomrs = api.query_lomr(lomr, where, geom_filter, sr)

    # Step 4: Check if updates are necessary
    if len(boulder_lomrs.features) == 0:
        # send email
        pass

    # TRANSFORM
    # Step 5: Create a new versioned connection for city floodplains
    # Step 6a: Transform sfha delineations natively (dicts or pandas)
    # Step 6b: Dissolve new delins based on COB standards

    # LOAD
    # Step 7a: Make edits to the version
    # Step 7b: Cut existing floodplains with LOMR boundaries
    # Step 7c: Make existing floodplains inside LOMR bounds "Inactive"
    # Step 7d: Add the transformed sfhas into the version

    # NOTIFY
    # Step 8a: Notify steward of new version edits
    # Step 8b: Notify SMEs that edits are pending and new LOMRs are available
