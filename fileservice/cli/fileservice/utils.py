import configparser, os,logging,json
import requests


def parseConfig(configfile):
    log = logging.getLogger(__name__)
    
    configfields =["authtype","fileserviceurl"]
    tokenfields=["token"]

    auth0hmsfields=["username",
                    "password",
                    "adfsurl",
                    "appcallback",
                    "auth0initial",
                    "auth0callback"]
    udnfields=["udntoken","udnurl"]
    configoptions = {}
    
    config = configparser.RawConfigParser()
    try:
        config.read([configfile])
    except Exception as e:
        log.info("Error reading conf file: %s" % e)
        return None
    
    try:
        for f in configfields:
            configoptions[f] = config.get("fileservice", f)
    except Exception as e:
        log.info("Error in conf file: %s" % e)
        return None

    if configoptions["authtype"]=="token":
        try:
            for f in tokenfields:
                configoptions[f] = config.get("fileservice", f)
        except Exception as e:
            log.info("Error in conf file token auth: %s" % e)
            return None
    elif configoptions["authtype"]=="hmssaml":
        try:
            for f in auth0hmsfields:
                configoptions[f] = config.get("fileservice", f)
        except Exception as e:
            log.info("Error in conf file hmssaml auth: %s" % e)
            return None
    
    try:
        for f in udnfields:
            configoptions[f] = config.get("udn", f) 
    except:
        pass

    
    return configoptions
