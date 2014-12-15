import ConfigParser, os,logging,json
import requests

def parseConfig(configfile):
    log = logging.getLogger(__name__)
    
    configfields =["username","password","environment"]
    configoptions = {}
    
    config = ConfigParser.RawConfigParser()
    try:
        config.read([configfile])
    except Exception,e:
        log.info("Error reading conf file: %s" % e)
        return None
    
    try:
        for f in configfields:
            configoptions[f] = config.get("fileservice", f)
    except Exception,e:
        log.info("Error in conf file: %s" % e)
        return None
    
    return configoptions
