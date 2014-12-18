import logging,json, os,jsonschema,importlib,uuid,requests

from cliff.command import Command

class SearchFiles(Command):
    "Search by keywords, tags and fields -- fileservice -v list --fields 'description' --keyword testfile"
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
        json.dumps(r.json(), indent=1)
        self.app.stdout.write("%s" % json.dumps(r.json(),indent=4))

class ListFiles(Command):
    "List and filter by structured data"
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
        print data
        r = requests.get("%s/%s" % (self.app.configoptions["fileserviceurl"],"filemaster/api/file/"),
                         params=data,
                         headers=headers)
        self.app.stdout.write("%s" % json.dumps(r.json(),indent=4))
        