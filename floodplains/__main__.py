import floodplains.etl as etl
import floodplains.config as config
import floodplains.utils.email as email
from floodplains.utils.managedisk import list_files

# Initiate a logger for __main__
log = config.logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        log.info("Initiating extraction.")
        output = etl.extract()
        if output:
            # log.info("Initiating transformation.")
            # etl.transform(output)
            # log.info("Initiating load.")
            # etl.load()
            pass
        else:
            log.info("Notifying steward that no changes were made in Boulder.")
            body = email.email_body("No new LOMRs have been added in Boulder.")
            email.send_email(sender=config.sender, password=config.password,
                             recipients=config.steward, body=body)
    except Exception:
        log.exception("Something prevented the script from running.")
    finally:
        list_files(['.sde'], delete=True)
