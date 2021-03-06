#!/usr/bin/env python

'''
Gets the list of jenkins jobs due to some criteria, which's defined in config file
config sample:
jenkins_url: 'http(s)://your_jenkins.server'
user: 'username'
token: 'jenkins api token'
view: 'view_name' # if you want view in view just write external_view/view/internal_view here
job_name_template: 'job name mask' # if you want a list of jobs which contain some template in name, specify the template here, you can use regular expressions
job_conf_template: '(?<=you can use ahead search\>)[\w\d\.]+' # if you want a list of jobs which contain some template
# in config.xml, specify the template here. you can use regular expressions
search_depth: 3 # how far do you want to go through folders and views
'''

import read_config
import sys
import re
import requests
import json
import print_table


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

try:
    view = cfg['view']
    job_name_template = cfg['job_name_template']
    job_conf_template = cfg['job_conf_template']
    depth = cfg['search_depth']
except KeyError, exc:
    print("No such option in config.yml - {}\nIf it is a template and you dont need it - set it as empty line"
          .format(str(exc)))
    sys.exit(1)


def rec_checker(api_ans, depth):
    '''
    gets json as a parametr
    returns list of jobs
    '''
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
                rec_checker(contents, depth)
    if 'views' in api_ans:
        for view in api_ans['views']:
            nested = requests.get(view['url'] + '/api/json', auth=(user, token))
            rec_checker(json.loads(nested.text), depth)
    return jobs


# go through views
main_url = j_url + '/view/' + view
main_view = requests.get(main_url + '/api/json', auth=(user, token))
views = json.loads(main_view.text)
jobs = []
jobs = rec_checker(views, depth)
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



