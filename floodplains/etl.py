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
