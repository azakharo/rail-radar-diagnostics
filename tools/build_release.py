#! python2
# -*- coding: utf-8 -*-


from os.path import dirname, join, exists
from shutil import copy
import subprocess
import sys

# Add src dir to import paths
SRC_ROOT = join(dirname(__file__), "..", 'src')
sys.path.append(SRC_ROOT)
from mylogging import info, err

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
    info("Run Dropbox")
    subprocess.Popen([join(DROPBOX_EXE_DIR, 'Dropbox.exe')], cwd=DROPBOX_EXE_DIR)
    infoSep()

    info("Run build exe script")
    subprocess.call("build_exe.bat", shell=True)

    # Check the build has been completed
    exePath = join(DIST_DIR, EXE_FNAME)
    if not exists(exePath):
        err('{exe} was not built!'.format(exe=EXE_FNAME))
        return 1
    infoSep()

    info("Copy additional files to the dist dir")
    for f in FILES2COPY:
        copy(f, DIST_DIR)
    infoSep()

    info("Build setup.exe")
    subprocess.call(["C:/Program Files (x86)/NSIS/makensis.exe", "build_installer.nsi"], shell=True)
    infoSep()

    info("Copy the setup exe to Dropbox dir")
    setupExeSrcPath = join(DIST_DIR, SETUP_EXE_FNAME)
    copy(setupExeSrcPath, DROPBOX_DIR)
    infoSep()

    info("DONE")

def infoSep():
    info("===============================================================================")


if __name__ == '__main__':
    main()
