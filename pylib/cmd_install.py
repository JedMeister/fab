#!/usr/bin/python
# Copyright (c) TurnKey GNU/Linux - http://www.turnkeylinux.org
#
# This file is part of Fab
#
# Fab is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.

"""
Install packages into chroot

Arguments:
  <packages> := ( - | path/to/plan | path/to/spec | package[=version] ) ...
                If a version isn't specified, the newest version is implied.

Options:

  Pool related options:
  -p --pool=PATH                Set pool path (default: $FAB_POOL_PATH)
  -a --arch=ARCH                Set architecture (default: $FAB_ARCH)
  -n --no-deps                  Do not resolve/install package dependencies

  APT proxy:
  -x --apt-proxy=URL            Set apt proxy (default: $FAB_APT_PROXY)

  General:
  -i --ignore-errors=PKG[: ...] Ignore errors generated by list of packages
  -e --env=VARNAME[: ...]       List of environment variable names to pass through
                                default: $FAB_INSTALL_ENV

  (Also accepts fab-cpp options to effect plan preprocessing)

Environment:

   FAB_SHARE_PATH               Path to directory containing initctl.dummy
                                default: /usr/share/fab
"""

import os

import sys
import getopt

import help
import cpp
from plan import Plan
from installer import PoolInstaller, LiveInstaller
from common import fatal, gnu_getopt

from cmd_chroot import get_environ
from executil import getoutput

@help.usage(__doc__)
def usage():
    print >> sys.stderr, "Syntax: %s [-options] <chroot> <packages>" % sys.argv[0]

def main():
    cpp_opts, args = cpp.getopt(sys.argv[1:])
    try:
        opts, args = gnu_getopt(args, 'np:a:i:e:x:',
             ['pool=', 'arch=', 'apt-proxy=', 'ignore-errors=', 'env=', 'no-deps'])
    except getopt.GetoptError, e:
        usage(e)

    if not args:
        usage()

    if not len(args) > 1:
        usage("bad number of arguments")

    pool_path = os.environ.get('FAB_POOL_PATH', None)
    arch = os.environ.get('FAB_ARCH', None)
    apt_proxy = os.environ.get('FAB_APT_PROXY', None)
    resolve_deps = True
    ignore_errors = []

    env_conf = os.environ.get('FAB_INSTALL_ENV')
    environ = get_environ(env_conf)

    for opt, val in opts:
        if opt in ('-p', '--pool'):
            pool_path = val

        elif opt in ('-a', '--arch'):
            arch = val

        elif opt in ('-n', '--no-deps'):
            resolve_deps = False

        elif opt in ('-x', '--apt-proxy'):
            apt_proxy = val

        elif opt in ('-i', '--ignore-errors'):
            ignore_errors = val.split(":")

        elif opt in ('-e', '--env'):
            env_conf = val

    chroot_path = args[0]
    if not os.path.isdir(chroot_path):
        fatal("chroot does not exist: " + chroot_path)

    if not pool_path and not resolve_deps:
        fatal("--no-deps cannot be specified if pool is not defined")

    if not arch:
        arch = getoutput("dpkg --print-architecture")

    plan = Plan(pool_path=pool_path)
    for arg in args[1:]:
        if arg == "-" or os.path.exists(arg):
            plan |= Plan.init_from_file(arg, cpp_opts, pool_path)
        else:
            plan.add(arg)

    if pool_path:
        if resolve_deps:
            packages = list(plan.resolve())
        else:
            packages = list(plan)

        installer = PoolInstaller(chroot_path, pool_path, arch, environ)
    else:
        packages = list(plan)
        installer = LiveInstaller(chroot_path, apt_proxy, environ)

    installer.install(packages, ignore_errors)


if __name__=="__main__":
    main()

