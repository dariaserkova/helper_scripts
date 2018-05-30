#!/usr/bin/env python
'''Documentation to be written'''
# '%(folder_url)sjob/%(short_name)s/nextbuildnumber/submit

import read_config
import sys
import requests
import json

#####################
# Checking the configuration
#####################
cfg = read_config.read()
if cfg:
    j_url = cfg['jenkins_url']
    user = cfg['user']
    token = cfg['token']
else:
    print('Missing some mandatory parameters')
    sys.exit(1)


def set_b_num(url, num):
    print(num)
    r = requests.post(url, auth=(user, token), data={'nextBuildNumber': num})
    print(json.loads(r.text)['nextBuildNumber'])


def learn_b_num(url):
    r = requests.get(url, auth=(user, token))
    return json.loads(r.text)['nextBuildNumber']


