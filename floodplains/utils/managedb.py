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

    decrypted = ""
    try:
        f = cryptography.fernet.Fernet(key)
        decrypted = f.decrypt(bytes(token, 'utf-8'))
    except Exception:
        pass

    return decrypted.decode("utf-8")
