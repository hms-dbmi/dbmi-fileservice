# Examples

## Install
```
cd cli
python setup.py build
python setup.py develop
python setup.py install
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



TODO:  
Detail file  
Put files  
Get files  
Add Users  
Add Groups