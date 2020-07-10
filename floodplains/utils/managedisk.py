import os


def list_files(include: list = [], exclude: list = [], delete: bool = False):
    """Lists files from the package's root directory based on the
    filters provided in the positional args.

    Parameters
    ----------
    include : list
        If any string keyword in this parameter appears in the file
        name, it will be added to the list. If no list is provided,
        everything in the cwd will be listed.
    exclude : list
        If any keyword in this parameter appears in the file name, it
        will not be added to the list
    delete : bool
        A trigger to delete the files listed

    Returns:
    --------
    list
        A list of system paths to the files that match the spec'd
        criteria. If the delete flag is raised, the list represents the
        files on disk that were deleted.
    """
    listed = list()
    for root, _, files in os.walk(os.getcwd()):
        for f in files:
            listed.append(os.path.join(root, f).lower())

    if include:
        if not isinstance(include, list):
            include = [include]
        listed = [f for f in listed if any(
            arg.lower() in f for arg in include)]
    if exclude:
        if not isinstance(exclude, list):
            exclude = [exclude]
        listed = [f for f in listed if not any(
            arg.lower() in f for arg in exclude)]

    if delete:
        for d in listed:
            os.remove(d)

    return listed
