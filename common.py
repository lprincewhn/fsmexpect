#!/usr/bin/python
#coding=utf8

import config

def debug(str):
    if config.logger:
        config.logger.debug(str)
    elif config.debug:
        print '[DEBUG] ' + str

class AuthenticationFailed(Exception):
    pass

class ConnectionError(Exception):
    pass

class Timeout(Exception):
    pass

class SCPFailed(Exception):
    pass
