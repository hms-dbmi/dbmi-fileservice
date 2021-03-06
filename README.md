# FileService API

Fileserivce is an API that takes care of a variety of needs when it comes to managing files uploaded to AWS S3 buckets, including: permissions, authentication, upload/download signing, metadata handling, searching and archiving of files.

This is about the API. If you want information on the command line interface (CLI), go to fileservice/cli.

## API Documentation

### DownloadLogs

This endpoint returns data about file downloads, limited by just the ArchiveFiles that requesting user has view_archivefile permissions on.

URL: `/filemaster/api/logs`.

Accepted GET parameters:
1. `user_email` - the user who requested the download.
2. `uuid` - the uuid of the archivefile.
3. `filename` - the filename as specified in the ArchiveFile.Filename field.
4. `download_date_gte` - download dates greater than or equal to.
4. `download_date_lte` - download dates less than or equal to.

Return data:
1. `archivefile` - a json of some information about the downloaded ArchiveFile, include uuid, description, filename, and creation date.
2. `download_requested_on` - datetime the user requested a download URL.
3. `requesting_user` - a json of {'email': '{email}'} of who requested the download.

## Developer notes

### Accessing the Django shell in an EC2 docker container
1. First ssh into the EC2.
2. Then bash into the docker container running the django app.
3. Then run `ps -ef` to determine which PID is running the wsgi app as root user.
4. Then run `. <(xargs -0 bash -c 'printf "export %q\n" "$@"' -- < /proc/{PID}/environ)` with the PID from the above step to copy environment variables into your session.
5. Then run `python app/manage.py shell` to access the shell.

### Running unit tests
1. First make sure you are in a virtualenvironment with the pip requirements installed.
2. CD to the directory where manage.py is stored.
3. Run `python manage.py test --settings fileservice.test_settings`.

## Old notes below, may need updates

### Diagrams -- open in draw.io plugin  
[Login](https://drive.google.com/file/d/0B9lnki7dueLpV1pKbWJMVGNaRTQ/view?usp=sharing)  
[Upload](https://drive.google.com/file/d/0B9lnki7dueLpNFJfTHBfdEV5ZlU/view?usp=sharing)   
[Download](https://drive.google.com/file/d/0B9lnki7dueLpTkRDOHg0N2hVRTQ/view?usp=sharing)    

### Log in  
* HMS SAML via Auth0 -- alter first few lines of hms_saml_login.py and fill with your information. Then run it.  
```
$python hms_saml_login.py
```
It will spit out a JWT. Save it to a BASH variable.  
```
$CBMI1=`python hms_saml_login.py`
```

Or in a webbrowser go to:  
```
https://hms-dbmi.auth0.com/authorize?response_type=code&scope=openid%20profile&client_id=oI1eRm6NxzYD4fcikngYYKDnxjLLY7wb&redirect_uri=https://fileservice-ci.dbmi.hms.harvard.edu/callback/&connection=hms-it-test
```

* Another SAML -- will need a different &connection= string from HMS team (bernick)
* A plain old U/p -- Not desired, but can be used once added to fileservice database. Username will always be "email"
* An API token -- Not desired for humans, but can be used by services. Will need to be requested from HMS.  

### Create Permissions and Groups

A "group" represents a dataset. For instance a projectname might be a group, or some specific set of data like "breast cancer samples", "Pan-Cancer Study", or "Ebola samples". This is a logical group of data. Almost like a "folder" in a traditional file system. Permissions (read, write, etc) will be applied to those groups. Files can belong to multiple groups.  

Creates group called "udntest" with no users in it. The Power User executing this command needs to have "add_group" privileges.

After the group is created, a bunch of roles are created -- ADMINS, DOWNLOADERS, READERS, WRITERS, UPLOADERS. You add users to those roles depending on what powers they should have. The User who created this group automatically has rights in all of the roles.  

Users are always identified by "email address".  


```
$curl -k -v -X POST --cookie "Authorization=$CBMI1" \
-H "Content-Type: application/json; charset=UTF-8" \ 
-d '{"name":"udntest","users":[]}' \
"https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/groups/"

[
  {
    "users": [
      {
        "email": "cbmi_test1@medlab.harvard.edu"
      }
    ],
    "name": "udntest__ADMINS",
    "id": 1
  },
  {
    "users": [
      {
        "email": "cbmi_test1@medlab.harvard.edu"
      }
    ],
    "name": "udntest__DOWNLOADERS",
    "id": 2
  },
  {
    "users": [
      {
        "email": "cbmi_test1@medlab.harvard.edu"
      }
    ],
    "name": "udntest__READERS",
    "id": 3
  },
  {
    "users": [
      {
        "email": "cbmi_test1@medlab.harvard.edu"
      }
    ],
    "name": "udntest__WRITERS",
    "id": 4
  },
  {
    "users": [
      {
        "email": "cbmi_test1@medlab.harvard.edu"
      }
    ],
    "name": "udntest__UPLOADERS",
    "id": 5
  }
]

```

Alters group called "udntest__DOWNLOADERS" and puts users in it. The user's email must exist in the system.      

```
$curl -k -v -X PUT --cookie "Authorization=$CBMI1" \
 -H "Content-Type: application/json" \
 -d '{"users":[{"email":"cbmi_test2@medlab.harvard.edu"}]}' \
 "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/groups/2/"
```

If a group needs Upload access to a specific bucket. Ususally to the __UPLOADER group. You can do this through the /admin interface, too.  

Why do I need to do this if a user is a member of an "Upload" group? We want file uploaders to be able to specify different buckets for different needs, as FileService serves many buckets. For security reasons, Upload groups need access to specific buckets or else they could write to ALL buckets.  


```
$curl -k -v -X PUT --cookie "Authorization=$CBMI1" \
 -H "Content-Type: application/json" \
 -d '{"buckets":[{"name":"cbmi-fileservice-test"}]}' \
 "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/groups/5/"
```


### File management  

Now put a file in.  Make sure you fill out "filename" and "permissions".  There are other fields you can fill out, such as Location. Feel free to add tags and as much metadata (in JSON format) as you want.  
```
$curl -k -v -X POST --cookie "Authorization=$CBMI1" \
 -H "Content-Type: application/json" \
 -d '{"permissions":["udntest"],"metadata":{"coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2"]}' \
 "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/"

{
  "id": 7,
  "uuid": "0c19072c-9a6f-4a96-88ec-a9bb4033c4d6",
  "description": null,
  "permissions": ["udntest"],
  "metadata": {
    "coverage": "30",
    "patientid": "1234-123-123-123",
    "otherinfo": "info"
  },
  "tags": [
    "tag1",
    "tag2"
  ],
  "owner": {
    "email": "cbmi_test1@medlab.harvard.edu"
  },
  "filename": "test2.txt",
  "locations": []
}
```

### Edit a file with a PATCH.  The following will add a tag ("test4444") to the list of tags.  
```
curl -v -X PATCH  --cookie "Authorization=$CBMI1" \
-H "Content-Type: application/json" \
-d '{"tags":["test4444"]}' \ 
"https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/0c19072c-9a6f-4a96-88ec-a9bb4033c4d6/"
```

### Register a local file location associated with this file.  
```
$curl -k -v -X POST --cookie "Authorization=$CBMI1" \
 -H "Content-Type: application/json" \
 -d '{"location":"file:///isilon/location/test2.txt"}' \
 "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/0c19072c-9a6f-4a96-88ec-a9bb4033c4d6/register/"
```

### Upload a local file to S3. This command also registers the file location to the FileService.  
```
$curl -k -v -X GET --cookie "Authorization=$CBMI1" \
 -H "Content-Type: application/json" \
 "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/0c19072c-9a6f-4a96-88ec-a9bb4033c4d6/upload/"

{"url": "https://udnarchive-ci.s3.amazonaws.com/55a529e9-2677-4feb-bc71-171d49750798/test2.txt?Signature=al%2BeX%2BV04HeyIJTXPF6xQM6Ugy8%3D&Expires=1413916977&AWSAccessKeyId=AKIAJB22JW7JSGJXYYZA",  "location":"s3://udnarchive-ci/55a529e9-2677-4feb-bc71-171d49750798/test2.txt", "secretkey": "+AcXO0xxxxxxx", "sessiontoken": "AQoDYXdzEDUaxxxxxxxxx","accesskey": "ASIAJxxxxxxx", "foldername": "8519a097-79cf-469d-af65-346272905903","message": "PUT to this url"}

$curl -v -X PUT --upload-file "~/location/of/localfile.txt" \
"https://udnarchive-ci.s3.amazonaws.com/55a529e9-2677-4feb-bc71-171d49750798/test2.txt?Signature=al%2BeX%2BV04HeyIJTXPF6xQM6Ugy8%3D&Expires=1413916977&AWSAccessKeyId=AKIAJB22JW7JSGJXYYZA"
```
OR use the secretkey,sessiontoken and foldername (prefix) and use your own tools to upload, especially for multipart uploads (the CLI uses this).  

You can register a file location manually if you want.  
```
$curl -k -v -X POST --cookie "Authorization=$CBMI1" \
 -H "Content-Type: application/json" \
 -d '{"location":"s3://udnarchive-ci/55a529e9-2677-4feb-bc71-171d49750798/test2.txt"}' \
 "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/0c19072c-9a6f-4a96-88ec-a9bb4033c4d6/register/"
```


### Download a file from S3.  
```
$curl -k -v -X GET --cookie "Authorization=$CBMI1" \
 "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/0c19072c-9a6f-4a96-88ec-a9bb4033c4d6/download/"

{"url": "https://udnarchive-ci.s3.amazonaws.com/55a529e9-2677-4feb-bc71-171d49750798/test2.txt?Signature=V4kud19zXxtb%2FgTcOO8zx%2B6jNpo%3D&Expires=1413917245&AWSAccessKeyId=AKIAJB22JW7JSGJXYYZA"}

```
Use the returned URL to grab the file.  

### Search for a file.  
```
curl -X GET -H 'Accept: application/json;indent=4' -H 'Content-Type:application/json' \ 
--cookie "Authorization=$CBMI1" \ 
"http://localhost:8000/filemaster/api/search/?q=udntest&fields=md_permissions"

[
    {
        "description": "testttesttest", 
        "filename": "test2.txt", 
        "uuid": "b3b17c67-d45d-46a1-b57a-8d36b75a94bd", 
        "owner": "cbmi_test1@medlab.harvard.edu", 
        "tags": "tag1, tag2", 
        "metadata": "{\"permissions\": [\"udntest\"]}"
    }, 
    {
        "description": "testttesttest", 
        "filename": "test2.txt", 
        "uuid": "4aa366b8-2bed-4e99-ba8a-3a47c194c750", 
        "owner": "cbmi_test1@medlab.harvard.edu", 
        "tags": "tag1, tag2, tag3", 
        "metadata": "{\"coverage\": \"30x\", \"permissions\": [\"udntest\"]}"
    }
]

```
### Parameters  
* q = content -- the keywords you're looking for. 
* fields = field1,field2 -- to limit the search to certain fields. If you're looking for a field embedded in the regular metadata, try to start the field with md_ (md_permissions, md_coverage, etc).  
* facets = facet1,facet2 -- implemented in indexing, but nothing visible to users now (http://django-haystack.readthedocs.org/en/latest/faceting.html) .  

Tests
```
TEST_AWS_KEY=AKIAxxxxx TEST_AWS_SECRET=cXRrxxxxxxxxx coverage run --source='.' manage.py shell --settings fileservice.settings.local_dev
```
TODO:  

Extensive error checking  
Logging  
Auditing Logs  
MD Handling for new/edit files