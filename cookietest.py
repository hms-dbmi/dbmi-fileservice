import requests,base64
from urlparse import urlparse,parse_qs
from HTMLParser import HTMLParser

username = "cbmi_test1@medlab.harvard.edu"
password = "%$^xxxxx"
adfsurl = "http://adfs.medlab.harvard.edu/adfs/services/trust"
callback = "http://localhost:8000/callback/"
auth0initial = "https://hms-dbmi.auth0.com/authorize?response_type=code&scope=openid%20profile&client_id=oI1eRm6NxzYD4fcikngYYKDnxjLLY7wb&redirect_uri="+callback+"&connection=hms-it-test"
auth0callback = "https://hms-dbmi.auth0.com/login/callback?connection=hms-it-test"

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
            except Exception,e:
            	pass
    def get_fileids(self):
        return self.fileids

r = requests.get(auth0initial,allow_redirects=False,verify=False)

adfs =  r.headers['location']
auth0cookies = r.cookies

o=urlparse(adfs)
qs = parse_qs(o.query)

cookies = dict(MSISIPSelectionPersistent=base64.b64encode(adfsurl))
headers={
	"Connection":"keep-alive",
	"Content-Type":"application/x-www-form-urlencoded",
	"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0",
	"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}
headers2={
	"Connection":"keep-alive",
	"Content-Type":"application/x-www-form-urlencoded",
	"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0",
	"Accept":"application/xml"
}

r3 = requests.get(
	o.scheme+"://"+o.netloc+o.path,
	params={"SAMLRequest":qs['SAMLRequest'][0]},
	headers=headers,
	cookies=cookies
)

myparser = MyHTMLParser(r3.text)

payload = {
	"ctl00$ContentPlaceHolder1$SubmitButton":"Sign+In",
	"ctl00$ContentPlaceHolder1$UsernameTextBox":username,
	"ctl00$ContentPlaceHolder1$PasswordTextBox":password,
	"__VIEWSTATE":myparser.fields["__VIEWSTATE"],
	"__VIEWSTATEGENERATOR":myparser.fields["__VIEWSTATEGENERATOR"],
	"__EVENTVALIDATION":myparser.fields["__EVENTVALIDATION"],
	"__db":myparser.fields["__db"]
}

r4 = requests.post(
	o.scheme+"://"+o.netloc+o.path,
	params={"SAMLRequest":qs['SAMLRequest'][0]},
	headers=headers2,
	data=payload,
	cookies=cookies
)

myparser = MyHTMLParser(r4.text)

r5 = requests.post(
	auth0callback,
	headers=headers2,
	cookies=auth0cookies,
	data={"SAMLResponse":myparser.fields['SAMLResponse']},
    verify=False
)

print r5.cookies["Authorization"]
#print r5.json()
