import getpass
import logging
import logging.config
import logging.handlers
import os

import yaml
from cryptography.fernet import Fernet


def decrypt(key: str, token: str):
    """Decrypts encrypted text back into plain text.

    Parameters:
    -----------
    key : str
        Encryption key
    token : str
        Encrypted text

    Returns:
    --------
    str
        Decrypted plain text
    """

    f = Fernet(key)
    decrypted = f.decrypt(bytes(token, 'utf-8'))

    return decrypted.decode("utf-8")


username = getpass.getuser()
user_email = f"{username}@bouldercolorado.gov"

with open(f".{os.sep}floodplains{os.sep}credentials.yaml") as cred_file:
    creds = yaml.safe_load(cred_file.read())

with open(f".{os.sep}floodplains{os.sep}config.yaml") as config_file:
    config = yaml.safe_load(config_file.read())
    config['LOGGING']['handlers']['email']['toaddrs'] = user_email
    config['LOGGING']['handlers']['email']['credentials'] = [
        creds['EMAIL']['address'],
        creds['EMAIL']['password']]
    logging.config.dictConfig(config['LOGGING'])

# ESRI properties
esri = config["ESRI"]
esri_folder = os.path.abspath(esri["root"])
# Pro project location
aprx_location = os.path.join(esri_folder, esri["aprx_name"])

# Data properties
last_date = config["DATA"]["last_checked_date"]
urls = config["DATA"]["urls"]
sde = config["DATA"]["sde"]
sr = sde["spatialref"]
fc_name = sde["feature"]["name"]
fc_fields = sde["feature"]["fields"]

# Database properties
database = config["DATABASE"]
# Connections
read_conn = database["connections"]["read"]
edit_conn = database["connections"]["edit"]

# Version properties
version_params = config["VERSIONING"]
version_name = version_params["version_name"]
version_params["in_workspace"] = edit_conn
# Versioned SDE Connection
db_params = database["info"]
db_creds = creds["DATABASE"]
edit_user = db_params["username"].upper()
db_params["version"] = f"{edit_user}.{version_name}"
db_params["password"] = decrypt(db_creds["key"], db_creds["token"])
db_params["out_folder_path"] = esri_folder
db_params["out_name"] = db_params["version"] + ".sde"

# Email credentials
sender = creds["EMAIL"]["address"]
password = creds["EMAIL"]["password"]
# Email recipient config dict
recipients = config["EMAIL"]
# Different lists
notification = recipients["lomr-notification"]
steward = recipients["data-steward"]
