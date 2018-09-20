import configparser, os,logging,json, base64, requests, sys
from urllib.parse import urlparse,parse_qs
from html.parser import HTMLParser


class User:
    id = None
    authtype = "token"
    configoptions = None
    ssotoken = None
    
    def __init__(self,configoptions):
        self.configoptions = configoptions

    def auth(self):
        log = logging.getLogger(__name__)
        requests_log = logging.getLogger("requests")
        requests_log.setLevel(logging.WARNING)
        
        if self.configoptions['authtype']=="token":
            self.ssotoken="Token %s" % self.configoptions['token']
            return True
        
        #try other methods
        #general oauth
        #get JWT from auth0
        try:
            if self.configoptions['authtype']=="hmssaml":
                self.ssotoken=self.hms_saml()
                return True                
        except Exception as e:
            log.info("error authenticating %s" % e)        
        return False
    
    def hms_saml(self):
        log = logging.getLogger(__name__)
        requests_log = logging.getLogger("requests")
        requests_log.setLevel(logging.WARNING)
        username = self.configoptions['username']
        password = self.configoptions['password']
        adfsurl = self.configoptions['adfsurl'] #"http://adfs.medlab.harvard.edu/adfs/services/trust"
        callback = self.configoptions['appcallback'] #"https://fileservice-ci.dbmi.hms.harvard.edu/callback/"
        auth0initial = self.configoptions['auth0initial'] #"https://hms-dbmi.auth0.com/authorize?response_type=code&scope=openid%20profile&client_id=oI1eRm6NxzYD4fcikngYYKDnxjLLY7wb&redirect_uri="+callback+"&connection=hms-it-test"
        auth0callback = self.configoptions['auth0callback'] #"https://hms-dbmi.auth0.com/login/callback?connection=hms-it-test"
        
        #call auth0 and get forwarding address and data
        r = requests.get(auth0initial,allow_redirects=False, verify=False)
        adfs =  r.headers['location']
        auth0cookies = r.cookies        
        o=urlparse(adfs)
        qs = parse_qs(o.query)
        cookies = dict(MSISIPSelectionPersistent=base64.b64encode(adfsurl))

        headers_html={
            "Connection":"keep-alive",
            "Content-Type":"application/x-www-form-urlencoded",
            "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0",
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        headers_xml={
            "Connection":"keep-alive",
            "Content-Type":"application/x-www-form-urlencoded",
            "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0",
            "Accept":"application/xml"
        }

        adfs_req = requests.get(
            o.scheme+"://"+o.netloc+o.path,
            params={"SAMLRequest":qs['SAMLRequest'][0]},
            headers=headers_html,
            cookies=cookies
        )

        myparser = MyHTMLParser(adfs_req.text)

        payload = {
            "ctl00$ContentPlaceHolder1$SubmitButton":"Sign+In",
            "ctl00$ContentPlaceHolder1$UsernameTextBox":username,
            "ctl00$ContentPlaceHolder1$PasswordTextBox":password,
            "__VIEWSTATE":myparser.fields["__VIEWSTATE"],
            "__VIEWSTATEGENERATOR":myparser.fields["__VIEWSTATEGENERATOR"],
            "__EVENTVALIDATION":myparser.fields["__EVENTVALIDATION"],
            "__db":myparser.fields["__db"]
        }

        adfs_post = requests.post(
            o.scheme+"://"+o.netloc+o.path,
            params={"SAMLRequest":qs['SAMLRequest'][0]},
            headers=headers_xml,
            data=payload,
            cookies=cookies
        )
                
        myparser = MyHTMLParser(adfs_post.text)

        auth0_callback = requests.post(
            auth0callback,
            headers=headers_xml,
            cookies=auth0cookies,
            data={"SAMLResponse":myparser.fields['SAMLResponse']},
                allow_redirects=False
            )
        
        auth0_jwt = requests.get(
                auth0_callback.headers['location'],
                headers=headers_xml,
                cookies=auth0_callback.cookies,
                allow_redirects=False
                )
        
        return "JWT %s" % auth0_jwt.cookies['Authorization'].rstrip()

        
class MyHTMLParser(HTMLParser):
    def __init__(self, fh):
        """
        {fh} must be an input stream returned by open() or urllib2.urlopen()
        """
        HTMLParser.__init__(self)
        self.fileids = []
        self.fields={}
        self.feed(fh)
    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            attrD = dict(attrs)
            self.fileids.append(attrD)
            value=None
            try:
                value = attrD['value']
            except:
                pass
            try:
                self.fields[attrD['name']]=value
            except Exception as e:
                pass
    def get_fileids(self):
        return self.fileids
        
