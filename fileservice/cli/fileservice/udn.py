import logging,json, os,jsonschema,importlib,uuid,requests,sys

from cliff.command import Command


class RegisterFile(Command):
    "Register a file to UDN Gateway"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(RegisterFile, self).get_parser(prog_name)

        parser.add_argument('--fileID',
                            help="File UUID",
                            required=True)

        parser.add_argument('--patientID',
                            help="UDN Patient ID",
                            required=True)

        parser.add_argument('--filename',
                            help="filename",
                            required=False)


        return parser
    
    def take_action(self, parsed_args):
        self.log.debug(parsed_args)
        filename=None
        if parsed_args.filename:
            filename = parsed_args.filename
        else:
            headers={"Authorization":self.app.user.ssotoken,"Content-Type": "application/json"}
            r = requests.get("%s/%s/%s/" % (self.app.configoptions["fileserviceurl"],"filemaster/api/file",parsed_args.fileID),
                             headers=headers)
            if r.status_code==200:
                filename = json.dumps(r.json()["filename"])
            else:
                self.log.debug("%s" % r.status_code)
        
        #if self.app.configoptions["udntoken"]=="x":
        #    headers={"Authorization":self.app.user.ssotoken,"Content-Type": "application/json"}
        #else:
        headers={"Authorization":"Token "+self.app.configoptions["udntoken"],"Content-Type": "application/json"}
        r = requests.post("%s/patient/registerapi/%s/%s/" % (self.app.configoptions["udnurl"],parsed_args.patientID,parsed_args.fileID),
                          data=json.dumps({"filename":filename}),
                          headers=headers
                          )
        
        if r.status_code>=200 and r.status_code<300:
            self.app.stdout.write("%s" % json.dumps(r.json()))
        else:
            self.log.debug("%s" % r.status_code)

        