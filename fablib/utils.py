import apt


class FabDependsError(Exception):
    pass


def packages_installed(
        packages: list[str], raise_error: bool = True
) -> dict[str, bool | None]:
    """Checks if deb packages are installed using python-apt.

    If raise_error == True, then will raise an Error including about missing
    packages.

    Otherwise returns a list of dictionaries where the key is the package name
    and the value denotes the package installation status:

        True    package is installed
        False   package is not installed
        None    Package not found/not installable
    """
    package_status: dict[str, bool | None] = {}

    # messages for exception
    packages_missing = False
    missing = ""
    not_found = ""

    cache = apt.Cache()
    cache.open()


    for package in packages:
        package_status[package] = False
        try:
            pkg = cache[package]
            if pkg.is_installed:
                package_status[package] = True
            else:
                packages_missing = True
        except KeyError:
            # package not found
            packages_missing = True
            package_status[package] = None

        if raise_error and package_status[package] is False:
            if not missing:
                missing = f"missing package/s: {package}"
            else:
                missing = f"{missing}, {package}"
        elif raise_error and package_status[package] is None:
            if not not_found:
                not_found = f"uninstallable package/s: {package}"
            else:
                not_found = f"{not_found}, {package}"

    if not raise_error or not packages_missing:
        return package_status
    error_msg = "Packages not found:"
    if missing:
        error_msg = f"{error_msg}\n{missing}"
    if not_found:
        error_msg = f"\n{error_msg}\n{not_found}"
    raise FabDependsError(error_msg)

