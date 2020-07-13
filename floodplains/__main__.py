import floodplains.etl as etl
import floodplains.config as config
from floodplains.utils.managedisk import list_files

# Initiate a logger for __main__
log = config.logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        etl.main()
    except Exception:
        log.exception("Something prevented the script from running")
    finally:
        list_files(['.sde'], delete=True)
