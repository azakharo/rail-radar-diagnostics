#! python2
# -*- coding: utf-8 -*-

import logging
from os.path import dirname, join, exists
from shutil import copy
import subprocess

DIST_DIR = '../.build/dist'
EXE_FNAME = 'diagnost.exe'
SETUP_EXE_FNAME = 'DiagnostSetup.exe'
FILES2COPY = [
    '../src/favicon.ico',
    '../config/diagnost.cfg'
]

DROPBOX_EXE_DIR = 'C:/Users/zakhar/AppData/Roaming/Dropbox/bin'
DROPBOX_DIR = 'C:/Users/zakhar/Dropbox/Public'


def main():
    # Run Dropbox
    subprocess.Popen([join(DROPBOX_EXE_DIR, 'Dropbox.exe')], cwd=DROPBOX_EXE_DIR)

    # Run build exe script
    subprocess.call("build_exe.bat", shell=True)

    # Check the build has been completed
    exePath = join(DIST_DIR, EXE_FNAME)
    if not exists(exePath):
        err('{exe} was not built!'.format(exe=EXE_FNAME))
        return 1

    # Copy file to the dist dir
    for f in FILES2COPY:
        copy(f, DIST_DIR)

    # Build setup.exe
    subprocess.call(["C:/Program Files (x86)/NSIS/makensis.exe", "build_installer.nsi"], shell=True)

    # Copy the setup exe to Dropbox dir
    setupExeSrcPath = join(DIST_DIR, SETUP_EXE_FNAME)
    copy(setupExeSrcPath, DROPBOX_DIR)

    info("DONE")


##################################
# Logging

FORMAT = '%(message)s'
logging.basicConfig(format=FORMAT)
_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)

def log(msg):
    _logger.debug(msg)

def info(msg):
    _logger.info(msg)

def err(msg):
    _logger.error("ERROR: " + msg)

##################################


if __name__ == '__main__':
    main()
