# Examples

## Install
```
cd cli
mkvirtualenv -p python3 dbmi-fileservice
pip install .
```
Copy the fileservice.cfg.example file to ~/.fileservice.cfg and alter it for your own settings.  
I recommend getting a token from the sysadmin rather than using the SAML process, but that works too. 


## Search and List files
```
fileservice list --fields '{"filename":"autotest.txt"}'
```
"fields" is a simple json structure of "key" and "value". It lists files you have access to with that filter.  

```
fileservice search --keyword 'auto'
[
    {
        "uuid": "800821a5-6d1e-4eda-b321-0819b592a338", 
        "tags": "", 
        "description": "test auto stuff", 
        "filename": "autotest.txt", 
        "owner": "cbmi_test1@medlab.harvard.edu", 
        "metadata": "{\"permissions\": [\"udntest\"]}"
    }
]
```
```
fileservice search --keyword 'tag1' --fields 'tags'
[
    {
        "uuid": "7527081d-fcac-475c-a805-c4c81e3eaf06", 
        "tags": "tag1, tag2", 
        "description": "testfile", 
        "filename": "test2.txt", 
        "owner": "cbmi_test1@medlab.harvard.edu", 
        "metadata": "{\"permissions\": [\"udntest\"]}"
    }, 
    {
        "uuid": "0c19072c-9a6f-4a96-88ec-a9bb4033c4d6", 
        "tags": "tag1, tag2, test444", 
        "description": "testfile", 
        "filename": "test2.txt", 
        "owner": "cbmi_test1@medlab.harvard.edu", 
        "metadata": "{\"permissions\": [\"udntest\"]}"
    }
]
```
"fields" is a comma separated list of fields to restrict search to. "keyword" is the text string to used to search.  

## Write a file (metadta)
Prepare a file with your metadata.  

```
[
  {
    "metadata": {"coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},
    "filename": "test.txt",
    "description": "test",
    "permissions":["udntest"]
  }
]
```
And run to write that data.  
```
fileservice -v write --jsonFile test.json
```
Output is a list of UUIDs. Please use these UUIDs to address the file in the future. Or put them in a database. But keep them!  

## Read a file (metadata)
```
fileservice -v view --fileID=f149cf5d-722e-4a3f-9767-89b856458ddb
{
    "creationdate": "2014-12-20T17:17:49Z", 
    "modifydate": "2014-12-20T17:17:49Z", 
    "description": "test", 
    "tags": [], 
    "locations": [], 
    "uuid": "f149cf5d-722e-4a3f-9767-89b856458ddb", 
    "filename": "test.txt", 
    "owner": {
        "email": "David_Bernick@hms.harvard.edu"
    }, 
    "permissions": [
        "udntest"
    ], 
    "id": 11, 
    "metadata": {
        "patientid": "1234-123-123-123", 
        "coverage": "30", 
        "otherinfo": "info"
    }
}
```

### Upload data to a "file" in the cloud
Uploads a local file to the fileID submitted. Optional "bucket" option to specify a specific bucket in the cloud.
```
fileservice -v upload --fileID f149cf5d-722e-4a3f-9767-89b856458ddb \
	--localFile /Users/db165/etl.retry \
	--bucket "udnarchive-ci"
```

### Download data from the cloud
Downloads a file to local filesystems.
```
curl `fileservice download --fileID f149cf5d-722e-4a3f-9767-89b856458ddb | jq -r .url` > ~/test.txt
```

### Register a file into UDN Gateway
Adds a file to UDN
```
fileservice udn --fileID <FILE UUID when you write file> --patientID <UDN PATIENT UUID>
```

TODO:  
Add Users  
Add Groups
