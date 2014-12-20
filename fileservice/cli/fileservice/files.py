import logging,json, os,jsonschema,importlib,uuid,requests,sys

from cliff.command import Command

class SearchFiles(Command):
    "Search by keywords, tags and fields: fileservice search --fields 'description' --keyword testfile"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(SearchFiles, self).get_parser(prog_name)

        parser.add_argument('--fields',
                            help="Key value pairs for filtering. comma separated: description,md_test",
                            required=False)

        parser.add_argument('--keyword',
                            help="Keyword to search by",
                            required=True)


        return parser

    def take_action(self, parsed_args):
        self.log.debug(parsed_args)
        self.log.debug("Logged in -- "+self.app.user.ssotoken)
        headers={"Authorization":self.app.user.ssotoken}
        
        fieldlist=[]
        fields=parsed_args.fields
        if fields:
            fieldlist = fields.split(',') 
        data = {}

        data["q"]=parsed_args.keyword
        data["fields"]=fields
        r = requests.get("%s/%s" % (self.app.configoptions["fileserviceurl"],"filemaster/api/search/"),
                         params=data,
                         headers=headers)
        self.log.debug("Search URL -- "+r.url)
        if r.status_code==200:
            self.app.stdout.write("%s" % json.dumps(r.json(),indent=4))
        else:
            self.app.stdout.write("%s" % r.status_code)
            

class ListFiles(Command):
    "List and filter by structured data: fileservice list --fields '{\"field\":\"value\"}'"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(ListFiles, self).get_parser(prog_name)

        parser.add_argument('--fields',
                            help="Key value pairs for filtering. json format. '{\"field\":\"value\"}'",
                            required=False)

        return parser

    def take_action(self, parsed_args):
        self.log.debug(parsed_args)
        self.log.debug("Logged in -- "+self.app.user.ssotoken)
        headers={"Authorization":self.app.user.ssotoken}
        
        fields=parsed_args.fields
        data={}
        if fields:
            data=json.loads(fields)
        r = requests.get("%s/%s" % (self.app.configoptions["fileserviceurl"],"filemaster/api/file/"),
                         params=data,
                         headers=headers)
        if r.status_code==200:
            self.app.stdout.write("%s" % json.dumps(r.json(),indent=4))
        else:
            self.app.stdout.write("%s" % r.status_code)

class ReadFile(Command):
    "Details about a file"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(ReadFile, self).get_parser(prog_name)

        parser.add_argument('--fileID',
                            help="File UUID",
                            required=True)

        return parser

    def take_action(self, parsed_args):
        self.log.debug(parsed_args)
        self.log.debug("Logged in -- "+self.app.user.ssotoken)
        headers={"Authorization":self.app.user.ssotoken}
        
        fileID=parsed_args.fileID
        r = requests.get("%s/%s/%s/" % (self.app.configoptions["fileserviceurl"],"filemaster/api/file/",fileID),
                         headers=headers)
        if r.status_code==200:
            self.app.stdout.write("%s" % json.dumps(r.json(),indent=4))
        else:
            self.app.stdout.write("%s" % r.status_code)

class WriteFile(Command):
    "Write a file"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(WriteFile, self).get_parser(prog_name)

        parser.add_argument('--jsonFile',
                            help="a file location containing a JSON List [] full of JSON describing files to create.",
                            required=True)

        return parser

    def take_action(self, parsed_args):
        self.log.debug(parsed_args)
        self.log.debug("Logged in -- "+self.app.user.ssotoken)
        headers={"Authorization":self.app.user.ssotoken,"Content-Type": "application/json"}
        
        #parse
        #jsonfile = json.dumps(json.load(open(parsed_args.jsonFile)))
        jsonfile = json.load(open(parsed_args.jsonFile))
        jsondump = json.dumps(json.load(open(parsed_args.jsonFile)))
        #validate
        if not self.validatejson(jsonfile):
            self.app.stdout.write("json parsing error")
            sys.exit(0)
        #for each entry, addand spit out line
        for j in jsonfile:
            r = requests.post("%s/%s/" % (self.app.configoptions["fileserviceurl"],
                                             "filemaster/api/file/"),
                                             headers=headers,
                                             data=json.dumps(j)
                                             )
            if r.status_code>=200 and r.status_code<300:
                self.app.stdout.write("%s" % json.dumps(r.json()["uuid"]))
            else:
                self.app.stdout.write("ERROR WRITING: %s" % r.status_code)
            continue
            
    def validatejson(self, jsondata):
        for j in jsondata:
            schema = None
            try:
                schema = json.load(open("data/schemas/files.json"))
            except Exception,e:
                self.log.error("Cannot decode schema file -- %s" % e)
                return False
            
            try:
                jsonschema.validate(j, schema)
                return True
            except jsonschema.ValidationError:
                self.log.error("Metadata is not valid for type FILE")
                raise
                return False
