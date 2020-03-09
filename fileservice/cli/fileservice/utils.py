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


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', print_end="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        print_end    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r  %s |%s| %s%% %s' % (prefix, bar, percent, suffix), end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()
