import inspect 

def get_all_args(include_implicit_args: bool = False) -> dict:
    """
    Get all arguments of the caller function, excluding 'self' if include_self is False.
    :param include_implicit_args: If True, include 'self' or 'cls' in the returned dictionary.
    :return: Dictionary of argument names and their values.
    """
    frame = inspect.currentframe()
    outer_frame = frame.f_back  # Get the caller's frame
    args, _, _, values = inspect.getargvalues(outer_frame)
    res = {arg: values[arg] for arg in args}

    if not include_implicit_args:
        # Remove 'self' or 'cls' if present
        res.pop('self', None)
        res.pop('cls', None)
    
    return res