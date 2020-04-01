import logging
import json
import jsonschema
import requests
import sys
import math
import os
import multiprocessing
import threading
import io as StringIO
from boto.s3.connection import S3Connection
from cliff.command import Command
from filechunkio import FileChunkIO
from furl import furl
from magic import Magic
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from .utils import print_progress_bar

threadLimiter = threading.BoundedSemaphore(multiprocessing.cpu_count())
chunk_size = 52428800


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
        r = requests.get("%s/%s/%s/" % (self.app.configoptions["fileserviceurl"],"filemaster/api/file",fileID),
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
                                             "filemaster/api/file"),
                                             headers=headers,
                                             data=json.dumps(j)
                                             )
            if r.status_code>=200 and r.status_code<300:
                self.app.stdout.write("%s\n" % json.dumps(r.json()["uuid"]))
            else:
                self.app.stdout.write("ERROR WRITING: %s" % r.status_code)
            continue
            
    def validatejson(self, jsondata):
        for j in jsondata:
            schema = None
            try:
                schema = json.load(open("data/schemas/files.json"))
            except Exception as e:
                self.log.error("Cannot decode schema file -- %s" % e)
                return False
            
            try:
                jsonschema.validate(j, schema)
                return True
            except jsonschema.ValidationError:
                self.log.error("Metadata is not valid for type FILE")
                raise
                return False

def callback(num_bytes_read):
    #print num_bytes_read, 'bytes read'
    pass

class processMultipart(threading.Thread):
    def __init__(self, i,chunk_count,filepath,mp,app):
        threading.Thread.__init__(self)
        self.i = i
        self.chunk_count = chunk_count
        self.filepath = filepath
        self.mp = mp
        self.app = app

    def run(self):
        threadLimiter.acquire()
        try:
            offset = chunk_size * self.i
            source_size = os.stat(self.filepath).st_size
    
            bytes = min(chunk_size, source_size - offset)
            with FileChunkIO(self.filepath, 'r', offset=offset,bytes=bytes) as fp:
                self.mp.upload_part_from_file(fp, part_num=self.i + 1, cb=self.percent_cb, num_cb=10)
                self.app.stdout.write(("Completed %s of %s chunks\n") % (self.i+1,str(self.chunk_count)))
        finally:
            threadLimiter.release()
            
    def percent_cb(self,complete, total):
        sys.stdout.write('.')
        sys.stdout.flush()
            

class UploadFile(Command):
    "Upload a file"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(UploadFile, self).get_parser(prog_name)

        parser.add_argument('--fileID',
                            help="File UUID",
                            required=True)

        parser.add_argument('--localFile',
                            help="The local location of the file -- eg /home/user/test.bam",
                            required=True)

        parser.add_argument('--bucket',
                            help="The bucket where the file should go",
                            required=False)


        return parser

    
    def take_action(self, parsed_args):
        self.log.debug(parsed_args)
        self.log.debug("Logged in -- "+self.app.user.ssotoken)
        headers={"Authorization":self.app.user.ssotoken,"Content-Type": "application/json"}
        bucket=None
        
        try:
            bucket = parsed_args.bucket
        except:
            bucket = self.app.configoptions["bucket"]
        
        r = requests.get("%s/%s" % (self.app.configoptions["fileserviceurl"],
                                            "filemaster/api/file/%s/upload/" % (parsed_args.fileID)),
                                            headers=headers,
                                            params={"bucket":bucket}
                                            )
        if r.status_code>=200 and r.status_code<300:
            uploadurl = r.json()["url"]
            #upload = requests.put(uploadurl,data=open(parsed_args.localFile))
            conn = S3Connection(aws_access_key_id=r.json()["accesskey"], 
                                aws_secret_access_key=r.json()["secretkey"],
                                security_token=r.json()['sessiontoken'],
                                is_secure=True, host=S3Connection.DefaultHost)
            
            b = conn.get_bucket(r.json()['bucket'],validate=False)
            
            from boto.s3.key import Key
            k = Key(b)
            k.key = "/"+r.json()['foldername']+"/"+r.json()['filename']
            
            source_size = os.stat(parsed_args.localFile).st_size
            if source_size < 1000000000:
                k.set_contents_from_filename(parsed_args.localFile, cb=self.percent_cb, num_cb=10)
            else:
                mp = b.initiate_multipart_upload(k.key)
                self.multipartUpload(parsed_args.localFile,mp)

            uploadcomplete = requests.get("%s/%s" % (self.app.configoptions["fileserviceurl"],
                                                            "filemaster/api/file/%s/uploadcomplete/" % (parsed_args.fileID)),
                                                            headers=headers,
                                                            params={"location":r.json()["locationid"]}
                                                            )                
            self.app.stdout.write("\n%s,%s,%s\n" % (parsed_args.fileID,uploadurl,uploadcomplete.json()["filename"]))
        else:
            self.app.stdout.write("%s" % r)
        
    def multipartUpload(self,filepath,mp):
        source_size = os.stat(filepath).st_size
        chunk_count = int(math.ceil(source_size / float(chunk_size)))

        self.app.stdout.write(("Uploading in %s Chunks\n") % str(chunk_count))
        threads = []

        for i in range(chunk_count):
            self.app.stdout.write(("Starting thread for Chunk %s\n") % str(i))
            thread = processMultipart(i,chunk_count,filepath,mp,self.app)
            #thread = threading.Thread(target=processMultipart, args=(i,chunk_count,filepath,mp,self.app))
            thread.start()
            threads.append(thread)            
                
        for thread in threads:
            thread.join()                                
        mp.complete_upload()
        self.app.stdout.write("Upload Complete\n")        
        
    def percent_cb(self,complete, total):
        sys.stdout.write('.')
        sys.stdout.flush()


class ReadCallbackStream(object):
    """Wraps a string in a read-only file-like object, but also calls
    callback(num_bytes_read) whenever read() is called on the stream. Used for
    tracking upload progress. Idea taken from this StackOverflow answer:
    http://stackoverflow.com/a/5928451/68707
    """
    def __init__(self, data, callback,filename):
        self._len = len(data)
        self._io = StringIO.StringIO(data)
        self._callback = callback
        self.totalsize = os.path.getsize(filename)
        self.readsofar = 0
        sys.stderr.write("Uploading %s" % filename)

    def __len__(self):
        return self._len

    def read(self, *args):
        chunk = self._io.read(*args)
        if len(chunk) > 0:
            self._callback(len(chunk))
        self.readsofar += len(chunk)
        percent = self.readsofar * 1e2 / self.totalsize
        sys.stderr.write("\r{percent:3.0f}%".format(percent=percent))            
        return chunk


class DownloadFile(Command):
    "Download a file"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(DownloadFile, self).get_parser(prog_name)

        parser.add_argument('--fileID',
                            help="File UUID",
                            required=True)

        return parser

    def take_action(self, parsed_args):
        self.log.debug(parsed_args)
        self.log.debug("Logged in -- "+self.app.user.ssotoken)
        headers={"Authorization":self.app.user.ssotoken,"Content-Type": "application/json"}

        r = requests.get("%s/%s" % (self.app.configoptions["fileserviceurl"],
                                            "filemaster/api/file/%s/download/" % (parsed_args.fileID)),
                                            headers=headers
                                            )
        self.app.stdout.write("%s" % json.dumps(r.json()))


def upload_callback(monitor):
    # Print a progress bar
    if not monitor.completed:
        print_progress_bar(iteration=monitor.bytes_read, total=monitor.len,
                           prefix='Uploading %s: ' % (monitor.filename),
                           suffix='of %d bytes' % monitor.len, length=70)

    # Mark as completed to prevent double print
    if monitor.bytes_read == monitor.len:
        monitor.completed = True


class PostFile(Command):
    "POST a file"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(PostFile, self).get_parser(prog_name)

        parser.add_argument('--fileID',
                            help="File UUID",
                            required=True)

        parser.add_argument('--localFile',
                            help="The local location of the file -- eg /home/user/test.bam",
                            required=True)

        parser.add_argument('--bucket',
                            help="The bucket where the file should go",
                            required=False)

        return parser

    def take_action(self, parsed_args):
        self.log.debug(parsed_args)
        self.log.debug("Logged in -- " + self.app.user.ssotoken)
        headers = {"Authorization": self.app.user.ssotoken, "Content-Type": "application/json"}
        bucket = None

        try:
            bucket = parsed_args.bucket
        except:
            bucket = self.app.configoptions["bucket"]

        try:
            # Build URL to get pre-signed POST
            post_url = furl(self.app.configoptions["fileserviceurl"])
            post_url.path.segments.extend(['filemaster', 'api', 'file', parsed_args.fileID, 'post', ''])

            # Make request
            post_r = requests.get(post_url.url, headers=headers, params={"bucket": bucket})
            if post_r.ok:
                # Parse elements of pre-signed POST from Fileservice
                location_id = post_r.json()["locationid"]
                post = post_r.json()["post"]
                upload_url = post["url"]
                fields = post["fields"]

                # Get MIME type
                magic = Magic(mime=True)
                mime_type = magic.from_file(parsed_args.localFile)

                # Add file
                fields['file'] = (os.path.basename(parsed_args.localFile), open(parsed_args.localFile, 'rb'), mime_type)

                encoder = MultipartEncoder(fields=fields)
                monitor = MultipartEncoderMonitor(encoder, upload_callback)

                # Add filename
                setattr(monitor, 'filename', os.path.basename(parsed_args.localFile))
                setattr(monitor, 'completed', False)

                # Make the request
                upload_r = requests.post(upload_url, data=monitor, headers={'Content-Type': monitor.content_type})
                if upload_r.ok:

                    # Build URL to get complete file
                    complete_url = furl(self.app.configoptions["fileserviceurl"])
                    complete_url.path.segments.extend(['filemaster', 'api', 'file', parsed_args.fileID,
                                                       'uploadcomplete', ''])

                    # Make the request
                    complete_r = requests.get(complete_url.url, headers=headers, params={"location": location_id})
                    if not complete_r.ok:
                        sys.stderr.write("Completion error: %s" % complete_r.content)

                    # Print upload details
                    self.app.stdout.write("\n%s,%s,%s\n" % (
                        parsed_args.fileID, upload_url, complete_r.json()["filename"]
                    ))

                else:
                    sys.stderr.write("Upload POST error: %s" % upload_r.content)
            else:
                sys.stderr.write("Upload error: %s" % post_r.content)
        except Exception as e:
            sys.stderr.write("Pre-signed POST error: %s" % e)
