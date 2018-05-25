#!/usr/bin/env python
'''
Docs to be written
'''

import yaml
import gitlab
import sys

#####################
## Reading the configuration
#####################
try:
    with open("config.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
except IOError:
    print('Can not find config.yml in the current directory')
    sys.exit(1)
try:
    GITLAB_TOKEN = cfg['GITLAB_TOKEN']
    GITLAB_ENDPOINT = cfg['GITLAB_ENDPOINT']
except KeyError, exc:
    print("No such option in config.yml - {}".format(str(exc)))
    sys.exit(1)

#####################
## Connection
#####################
def connection():
    global gitlab_conn
    gitlab_conn = gitlab.Gitlab(GITLAB_ENDPOINT,GITLAB_TOKEN)
    gitlab_conn.auth()

#########################
## Check if group exists
#########################
def check_group(group_name):
    try:
        group = gitlab_conn.groups.get(group_name)
    except (gitlab.GitlabHttpError, gitlab.GitlabGetError, gitlab.GitlabError):
        group = None
    return group

def main():
    global gitlab_group_name
    gitlab_group_name = sys.argv[1]
    connection()
    gitlab_group = check_group(gitlab_group_name)
    for group_project in gitlab_group.projects.list(all=True):
        try:
            project = gitlab_conn.projects.get(group_project.get_id())
            print(project.attributes.get('path_with_namespace') + '\n')
            project.archive()
        except gitlab.exceptions.GitlabCreateError, exc:
            print("Get an error for {}:\n{}".format(project, str(exc)))
            continue

if __name__ == "__main__":
    main()

