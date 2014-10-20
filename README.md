====
Log in
====
alter cookietest.py and fill with your information. Then run it.  
```
$python cookietest.py
```
It will spit out a JWT. Save it to a BASH variable.  
```
$CBMI1=`python cookietest.py`
```

Or in a webbrowser go to:  
```
https://hms-dbmi.auth0.com/authorize?response_type=code&scope=openid%20profile&client_id=oI1eRm6NxzYD4fcikngYYKDnxjLLY7wb&redirect_uri=https://fileservice-ci.dbmi.hms.harvard.edu/callback/&connection=hms-it-test
```

====
Create Group
====
Creates group called "udntest" with no users in it. User executing this command needs to hand "add_group" privileges.  


```
$curl -k -v -X POST --cookie "Authorization=$CBMI1" -H "Content-Type: application/json; charset=UTF-8"  -d '{"name":"udntest","users":[]}' "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/groups/"

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

Alters group called "udntest" and puts users in it. The user's email must exist in the system.      

```
$curl -k -v -X PUT --cookie "Authorization=$CBMI1" -H "Content-Type: application/json"   -d '{"users":[{"email":"cbmi_test2@medlab.harvard.edu"}]}' "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/groups/2/"
```

Now put a file in.  Make sure you fill out "metadata:permissions" and "filename".  There are other fields you can fill out, such as Location. Feel free to add tags and as much metadata (in JSON format) as you want.  
```
$curl -k -v -X POST --cookie "Authorization=$CBMI1" -H "Content-Type: application/json" -d '{"metadata":{"permissions":["udntest"]},"filename":"test2.txt","tags":["tag1","tag2"]}' "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/"

{
  "id": 7,
  "uuid": "0c19072c-9a6f-4a96-88ec-a9bb4033c4d6",
  "description": null,
  "metadata": {
    "permissions": [
      "udntest"
    ]
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

Edit a file with a PATCH.  
```
curl -v -X PATCH  --cookie "Authorization=$CBMI1" -H "Content-Type: application/json"   -d '{"tags":["test4444"]}' "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/0c19072c-9a6f-4a96-88ec-a9bb4033c4d6/"
```

Register a local file location associated with this file.  
```
$curl -k -v -X POST --cookie "Authorization=$CBMI1" -H "Content-Type: application/json" -d '{"location":"file:///isilon/location/test2.txt"}' "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/0c19072c-9a6f-4a96-88ec-a9bb4033c4d6/register/"
```

Upload a local file to S3.  
```
$curl -k -v -X GET --cookie "Authorization=$CBMI1" -H "Content-Type: application/json" "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/0c19072c-9a6f-4a96-88ec-a9bb4033c4d6/upload/"

{"url": "https://udnarchive-ci.s3.amazonaws.com/55a529e9-2677-4feb-bc71-171d49750798/test2.txt?Signature=al%2BeX%2BV04HeyIJTXPF6xQM6Ugy8%3D&Expires=1413916977&AWSAccessKeyId=AKIAJB22JW7JSGJXYYZA", "message": "PUT to this url"}

$curl -v -X PUT --upload-file "~/location/of/localfile.txt" "https://udnarchive-ci.s3.amazonaws.com/55a529e9-2677-4feb-bc71-171d49750798/test2.txt?Signature=al%2BeX%2BV04HeyIJTXPF6xQM6Ugy8%3D&Expires=1413916977&AWSAccessKeyId=AKIAJB22JW7JSGJXYYZA"

```

Download a file from S3.  
```
$curl -k -v -X GET --cookie "Authorization=$CBMI1" "https://fileservice-ci.dbmi.hms.harvard.edu/filemaster/api/file/0c19072c-9a6f-4a96-88ec-a9bb4033c4d6/download/"

{"url": "https://udnarchive-ci.s3.amazonaws.com/55a529e9-2677-4feb-bc71-171d49750798/test2.txt?Signature=V4kud19zXxtb%2FgTcOO8zx%2B6jNpo%3D&Expires=1413917245&AWSAccessKeyId=AKIAJB22JW7JSGJXYYZA"}

```
Use the returned URL to grab the file.

TODO:  

Tests  
Error Checking  
Logging  
Auditing Logs  
Docs  
Search/Browse 
MD Handling for new/edit files
