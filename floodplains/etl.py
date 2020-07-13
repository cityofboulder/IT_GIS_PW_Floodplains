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
