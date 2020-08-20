import floodplains.config as config

log = config.logging.getLogger(__name__)


def _cut_polys():
    # Cuts the city flood polygons
    pass


def _inactivate_polys():
    # Make all existing polys inside the LOMR boundaries 'Inactive'
    pass


def _add_new_polys():
    # Add new transformed polygons from FEMA
    pass


def _dissolve_polys():
    # Dissolve polygons inside the new LOMR by DRAINAGE, FEMAZONE, FLOODPLAIN,
    # and LIFECYCLE
    pass


def perform_edits():
    # Make all edits to the city floodplains
    pass
