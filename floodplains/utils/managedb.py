import cryptography


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


def create_version():
    pass


def create_versioned_connection():
    pass


def remove_version():
    pass
