#!/usr/bin/python
# Copyright (c) 2011 TurnKey Linux - all rights reserved

"""
Configuration environment variables:
    FAB_POOL_PATH           Path to the package pool
    FAB_PLAN_INCLUDE_PATH   Global include path for plan preprocessing
"""

from os.path import *
import pyproject

class CliWrapper(pyproject.CliWrapper):
    DESCRIPTION = __doc__
    
    INSTALL_PATH = dirname(__file__)

    COMMANDS_USAGE_ORDER = ['cpp', 'chroot', 
                            '',
                            'plan-annotate', 'plan-resolve',
                            '',
                            'install',
                            '',
                            'apply-removelist', 'apply-overlay']
    
if __name__ == '__main__':
    CliWrapper.main()
