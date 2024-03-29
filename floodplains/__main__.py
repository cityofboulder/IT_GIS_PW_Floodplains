import requests

import floodplains.config as config
import floodplains.etl as etl
import floodplains.utils.email as email
from floodplains.utils.managedb import remove_version
from floodplains.utils.managedisk import list_files

# Initiate a logger for __main__
log = config.logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        log.info("Testing REST Endpoints.")
        offline = list(filter(lambda u: requests.get(
            u, {"f": "pjson"}).status_code != 200, list(config.urls.values())))
        if not offline:
            log.info("Removing old edit version.")
            remove_version(config.edit_conn, config.version_name)
            log.info("Initiating extraction.")
            new_sfhas, new_lomrs = etl.extract()
            if new_sfhas is not None:
                log.info("Initiating transformation.")
                transformed = etl.transform(new_sfhas, new_lomrs)
                log.info("Initiating load.")
                email_table = etl.load(transformed, new_lomrs)
                log.info("Notifying folks of changes.")
                etl.notify(email_table)
            else:
                log.info("No changes were made in Boulder.")
                body = email.email_body(
                    ("No changes have been made to floodplains in Boulder "
                     "since the GISSCR user last edited floodplains in "
                     "GISPROD3."))
                email.send_email(sender=config.sender,
                                 password=config.password,
                                 recipients=config.steward,
                                 body=body)
        else:
            log.error("Offline URLs: " + ", ".join(u for u in offline))
            body = email.email_body("The following URLs are offline:<br><br>" +
                                    ", ".join(u for u in offline) +
                                    "<br><br>Try again later.")
            email.send_email(sender=config.sender, password=config.password,
                             recipients=config.steward, body=body)
    except Exception:
        log.exception("Something prevented the script from running.")
    finally:
        list_files(['.sde'], delete=True)
        log.info("Process finished!")
