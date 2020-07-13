import floodplains.config as config

import arcgis


# Initiate a logger for etl
log = config.logging.getLogger(__name__)


def main():
    # Step 1: Identify relevant feature services
    urls = {"city": ("https://maps.bouldercolorado.gov/arcgis/rest/services/"
                     "plan/CityLimits/MapServer/0"),
            "nfhl": ("https://hazards.fema.gov/gis/nfhl/rest/services/"
                     "public/NFHL/MapServer")}

    city = arcgis.features.FeatureLayer(urls["city"])
    nfhl = arcgis.features.FeatureLayerCollection(urls["nfhl"])
    lomr = nfhl.layers[1]
    sfha = nfhl.layers[27]

    # Step 2: Create spatial filter object for city limits
    # This will be used to test whether a LOMR has been added inside the city
    sr = 2876  # NAD83(HARN) / Colorado North (ftUS)
    anon_gis = arcgis.gis.GIS()
    city_lims = city.query(out_sr=sr)
    city_geoms = [poly.geometry for poly in city_lims.features]
    city_union = arcgis.geometry.union(
        spatial_ref=sr, geometries=city_geoms, gis=anon_gis)
    geom_filter = arcgis.geometry.filters.intersects(city_union, sr=sr)

    # EXTRACT
    # Step 3a: Extract LOMRs based on the desired criteria
    # Step 3b: Find the most recent update to our internal floodplains through
    # a connection to sde (using ADOPTDATE)
    # Step 3c: Identify LOMRs that are more recent than the most recent
    # floodplain update, and remove potential duplicates
    # Step 4: If no new lomrs exist, send an email to the steward
    # otherwise, extract new sfha delineations using the lomr boundaries

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
