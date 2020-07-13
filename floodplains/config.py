import os
import cryptography
import getpass
import logging
import logging.config
import logging.handlers

import yaml


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

    f = cryptography.fernet.Fernet(key)
    decrypted = f.decrypt(bytes(token, 'utf-8'))

    return decrypted.decode("utf-8")


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

# ESRI properties
esri = config["ESRI"]
esri_folder = os.path.abspath(esri["root"])
# Pro project location
aprx_location = os.path.join(esri_folder, esri["aprx"])

# Data properties
urls = config["DATA"]["urls"]
sde = config["DATA"]["sde"]

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
edit_user = db_params["username"].upper()
db_params["version"] = f"{edit_user}.{version_name}"
db_params["password"] = decrypt(creds["key"], creds["token"])
db_params["out_folder_path"] = esri_folder
db_params["out_name"] = db_params["version"] + ".sde"

# Email config dict
email = config["EMAIL"]
# Different lists
notification = email["lomr-notification"]
steward = email["data-steward"]
