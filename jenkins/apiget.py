#!/usr/bin/env python
'''
Documentation to be written
'''


import getpass
import yaml
import sys
import re
import requests
import json
import print_table


#####################
# Reading the configuration
#####################
try:
    with open("config.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
except IOError:
    print('Can not find config.yml in the current directory')
    sys.exit(1)

# jenkins url must be in config
try:
    j_url = cfg['jenkins_url']
    view = cfg['view']
    job_name_template = cfg['job_name_template']
    job_conf_template = cfg['job_conf_template']
    depth = cfg['search_depth']
except KeyError, exc:
    print("No such option in config.yml - {}\nIf it is a template and you dont need it - set it as empty line".format(str(exc)))
    sys.exit(1)

try:
    user = cfg['user']
    token = cfg['token']
except KeyError: #if not in config, could be provided via stdin
    print('Missing username and\or password in config. Please provide it via stdin.')
    user = raw_input('User: ')
    token = getpass.getpass()


def rec_checker(api_ans):
    '''
    gets json as a parametr
    returns list of jobs
    '''
    global depth
    if not isinstance(api_ans, dict):
        print(type(api_ans))
        return None
    if depth <= 0:
        return jobs
    depth -= 1
    if 'jobs' in api_ans:
        for job in api_ans['jobs']:
            if 'FreeStyleProject' in job['_class'] or 'MavenModuleSet' in job['_class']:
                jobs.append(job)
            if 'Folder' in job['_class']:
                nested = requests.get(job['url'] + '/api/json', auth=(user, token))
                contents = json.loads(nested.text)
                if contents['primaryView'] in contents['views']:  # we have url on view itself in view field in folder
                    contents['views'].remove(contents['primaryView'])  # json output so we need to remove it
                    del contents['primaryView']
                rec_checker(contents)
    if 'views' in api_ans:
        for view in api_ans['views']:
            nested = requests.get(view['url'] + '/api/json', auth=(user, token))
            rec_checker(json.loads(nested.text))
    return jobs


# go through views
main_url = j_url + '/view/' + view
main_view = requests.get(main_url + '/api/json', auth=(user, token))
views = json.loads(main_view.text)
jobs = []
jobs = rec_checker(views)
t_headers = ['Job name', 'Job url', "Matched with {}".format(job_conf_template)]
t_items = []
if job_name_template != '' and job_conf_template != '':
    for job in jobs:
        if re.search(job_name_template, job['name']):
            config = requests.get(job['url'] + '/config.xml', auth=(user, token))
            props = re.search(job_conf_template, config.text)
            if props:
                t_items.append([job['name'], job['url'], props.group(0)])
            else:
                t_items.append([job['name'], job['url'], 'Nope'])
elif job_conf_template == '' and job_name_template == '':
    for job in jobs:
        t_items.append([job['name'], job['url'], 'Was not performed'])
elif job_conf_template == '' and job_name_template != '':
    for job in jobs:
        if re.search(job_name_template, job['name']):
            t_items.append([job['name'], job['url'], 'Was not performed'])
else:
    for job in jobs:
        config = requests.get(job['url'] + '/config.xml', auth=(user, token))
        props = re.search(job_conf_template, config.text)
        if props:
            t_items.append([job['name'], job['url'], props.group(0)])
print_table.print_table(t_items, header=t_headers, wrap=False, max_col_width=55, wrap_style='wrap', row_line=True, fix_col_width=False)



