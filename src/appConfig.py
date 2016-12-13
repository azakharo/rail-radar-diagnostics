#! python2
# -*- coding: utf-8 -*-

from ConfigParser import ConfigParser
from os.path import exists
from mylogging import exception, info, warn


class AppConfig(object):

    DEF_HOST = '127.0.0.1'
    DEF_PORT = 22
    DEF_USER = 'user'
    DEF_PASS = '123456'
    DEF_STATE_PATH = '~/vbu.state.txt'

    def __init__(self, host=DEF_HOST, port=DEF_PORT, user=DEF_USER, passwd=DEF_PASS, statePath=DEF_STATE_PATH):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.statePath = statePath

    @staticmethod
    def safeGet(config, section, option, defVal):
        retval = defVal
        if config and config.has_section(section) and config.has_option(section, option):
            retval = config.get(section, option)
        return retval

    @staticmethod
    def safeGetInt(config, section, option, defVal):
        retval = defVal
        if config and config.has_section(section) and config.has_option(section, option):
            try:
                retval = config.getint(section, option)
            except:
                exception(u"invalid value for config file option '{0}'".format(option))
        return retval

    @staticmethod
    def safeGetBool(config, section, option, defVal):
        retval = defVal
        if config and config.has_section(section) and config.has_option(section, option):
            strVal = config.get(section, option)
            if strVal:
                # Convert to bool
                if strVal == 'Yes':
                    retval = True
                elif strVal == 'No':
                    retval = False
                else:
                    info(u"invalid value for config file option '{0}'".format(option))
        return retval

    # Return None if there is no config file
    @classmethod
    def readConfig(cls, cfgFilePath):
        appConf = None
        if exists(cfgFilePath):
            #info("Found config file: {0}".format(cfgFilePath))
            config = ConfigParser()
            config.read(cfgFilePath)
            sectionName = 'main'
            if config.has_section(sectionName):
                host = cls.safeGet(config, sectionName,     'host',     '')
                port = cls.safeGetInt(config, sectionName,  'port',     22)
                user = cls.safeGet(config, sectionName,     'user',     '')
                passwd = cls.safeGet(config, sectionName,   'passwd',   '')
                statePath = cls.safeGet(config, sectionName,'statePath','')

                # Create config
                appConf = AppConfig(host, port, user, passwd, statePath)
            else:
                warn("The configuration file doesn't have required section '{}'".format(sectionName))
        else:
            info("Config file '{0}' not found".format(cfgFilePath))
        return appConf
