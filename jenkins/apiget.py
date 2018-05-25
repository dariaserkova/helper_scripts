#!/usr/bin/env python
'''Documentation to be written'''


import getpass
import yaml
import sys
import re
import requests
import json

#####################
## Reading the configuration
#####################
try:
    with open("config.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
except IOError:
    print('Can not find config.yml.yml in the current directory')
    sys.exit(1)

# jenkins url must be in config
try:
    j_url = cfg['jenkins_url']
    view = cfg['view']
except KeyError, exc:
    print("No such option in config.yml.yml - {}".format(str(exc)))
    sys.exit(1)

try:
    user = cfg['user']
    token = cfg['token']
except KeyError: #if not in config, could be provided via stdin
    print('Missing username and\or password in config. Please provide it via stdin.')
    user = raw_input('User: ')
    token = getpass.getpass()

# go through views
main_url = j_url + '/view/' + view
main_view = requests.get(main_url + '/api/json', auth=(user, token))
views = json.loads(main_view.text)['views']
print('|Job name \t |Job url \t |Properties file path|')
for item in views:
    nested = requests.get(item['url'] + '/api/json', auth=(user, token))
    jobs = json.loads(nested.text)['jobs']
    for job in jobs:
        if re.search('-SRC-build', job['name']):
            config = requests.get(job['url'] + '/config.xml', auth=(user, token))
            props = re.search(r'(?<=propertiesFilePath\>)[\w\d\.]+', config.text)
            if props:
                print('|' + job['name'] + '\t' + '|' + job['url'] + '\t' + '|' + props.group(0) + '|')
            else:
                print('|' + job['name'] + '\t' + '|' + job['url'] + '|')



