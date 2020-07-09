import getpass
import logging
import logging.config
import logging.handlers

import yaml

username = getpass.getuser()
user_email = f"{username}@bouldercolorado.gov"

with open(r'.\floodplains\credentials.yaml') as cred_file:
    creds = yaml.safe_load(cred_file.read())

with open(r'.\floodplains\config.yaml') as config_file:
    config = yaml.safe_load(config_file.read())
    config['LOGGING']['handlers']['email']['toaddrs'] = user_email
    config['LOGGING']['handlers']['email']['credentials'] = [
        creds['EMAIL']['address'],
        creds['EMAIL']['password']]
    logging.config.dictConfig(config['LOGGING'])

# Pro project location
aprx = config["aprx"]

# Database config dict
database = config["DATABASE"]
# Connections
read_conn = database["connections"]["read"]
edit_conn = database["connections"]["edit"]
# Properties
db_params = database["info"]
db_creds = database["credentials"]

# Email config dict
email = config["EMAIL"]
# Different lists
notification = email["lomr-notification"]
steward = email["data-steward"]

# Version config dict
version = config["VERSIONING"]
# Creation properties
parent = version["parent"]
version_name = version["name"]
