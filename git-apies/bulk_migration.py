#!/usr/bin/env python
"""
This is a draft of gitlab -> bitbucket migration script for gitlab project one by one
Usage:  python migration.py <SAMI-GROUP> <BB-PROJECT> <FEATURES>
Where
FEATURES: Issues,MergeRequests,Pipelines,Snippets,Webhooks,Wiki

Examples:
Group with projects only with Pull-Requests, no more extra features
python bulk_migration.py ls-infrastructure infra MergeRequests

Group with projects with Issues and Snippets
python bulk_migration.py ls-infrastructure infra Issues,Snippets

Group with projects with everything
python bulk_migration.py ls-infrastructure infra Issues,MergeRequests,Pipelines,Snippets,Webhooks,Wiki

You can also specify <SAMI-GROUP>/<SAMI-PROJECT> if you want to migrate just one of them
Run pip install -r pip-list to install all dependences
"""
import os
import gitlab
import git
import sys
import requests
import subprocess
import json
import time
import yaml

#####################
# Reading the configuration
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
    BITBUCKET_ENDPOINT = cfg['BITBUCKET_ENDPOINT']
    BITBUCKET_REPOURL = cfg['BITBUCKET_REPOURL']
    BITBUCKET_REST_URL = cfg['BITBUCKET_REST_URL']
    BITBUCKET_TOKEN = cfg['BITBUCKET_TOKEN']
    BITBUCKET_USER = cfg['BITBUCKET_USER']
    TEMPORAL_PATH = cfg['TEMPORAL_PATH']
    METADATA_DIR = cfg['METADATA_DIR']
except KeyError, exc:
    print("No such option in config.yml - {}".format(str(exc)))
    sys.exit(1)

#####################
# Connection
#####################
def connection():
    global gitlab_conn
    gitlab_conn = gitlab.Gitlab(GITLAB_ENDPOINT,GITLAB_TOKEN)
    gitlab_conn.auth()


#########################
# Check if group exists
#########################
def check_group(group_name):
    try:
        group = gitlab_conn.groups.get(group_name)
    except (gitlab.GitlabHttpError, gitlab.GitlabGetError, gitlab.GitlabError):
        group = None
    return group


#########################
# Clone git repo locally
#########################
def clone_repo(project):
    destination = os.path.join(TEMPORAL_PATH,project.attributes.get('path_with_namespace'))
    if os.path.isdir(destination):
        print(">>>>> Fetching repo content from {}".format(project.attributes.get('path_with_namespace')))
        repo = git.Repo(destination)
        repo.remotes.origin.fetch()
    else:
        print(">>>>> Cloning repo from {} to {}".format(project.attributes.get('path_with_namespace'),destination))
        repo = git.Repo.clone_from(project.attributes.get('ssh_url_to_repo'), destination, mirror=True)
    return repo


#########################
# Create remote repo in bitbucket
#########################
def create_repo(project_name, repo_name):
    project_url = BITBUCKET_REST_URL+'/projects/'+project_name
    project_exists = requests.get(project_url,auth=(BITBUCKET_USER,BITBUCKET_TOKEN))
    if project_exists.status_code != 200:
        print(">>>>> Project {} does NOT exist on git..io :-(\nPlease create it before migrating repos".format(project_name))
        sys.exit(1)

    repo_url = BITBUCKET_REST_URL+'/projects/'+project_name+'/repos/'+repo_name
    repo_exists = requests.get(repo_url,auth=(BITBUCKET_USER,BITBUCKET_TOKEN))
    if repo_exists == 200:
        print(">>>>> Repo {} already exists, most likely...".format(repo_name))
        return

    url = project_url+'/repos'
    authentication = "Authorization: Bearer {}".format(BITBUCKET_TOKEN)
    headers = "Content-Type: application/{}".format('json')
    data = r'{"scm": "git", "is_private": "true", "fork_policy": "no_public_forks", "name": "'+repo_name+'\"}'
    command = "curl -X POST -H \"{}\" -H \"{}\" {} -d \'{}\' > /dev/null 2>&1".format(authentication,headers,url,data)
    print(">>>>> Creating {} repo under {} project".format(repo_name, project_name))
    subprocess.check_output(command,shell=True)



#########################
# Add remote origin
#########################
def add_remote_repo(repo, project_name, repo_name):
    remote_name = "bb_{}_{}".format(os.getpid(),repo_name)
    print(">>>>> Adding remote {} to origin on {} repo".format(remote_name, repo_name))
    connection_string = "{}/{}/{}".format(BITBUCKET_REPOURL, project_name,repo_name)
    repo.remotes.origin.add(repo,remote_name,connection_string)
    return remote_name


#########################
# Push repo to remote
#########################
def push_repo(repo,remote_name):
    try:
        print(">>>>> Pushing {} to {} repo".format(repo.working_dir.split('/')[-1], remote_name))
        remote_origin = repo.remotes[remote_name]
        remote_origin.push(mirror=True)
    except git.exc.GitCommandError:
        print('>>>>> Some error on cloning, maybe, empty repo?')


#########################
## Remove local repo
#########################
def remove_repo(project):
    destination = os.path.join(TEMPORAL_PATH,project.attributes.get('path_with_namespace'))
    if os.path.isdir(destination):
        print(">>>>> Removing local repo {}".format(project.attributes.get('path_with_namespace').split('/')[-1]))
        subprocess.check_output('rm -fr '+destination,shell=True)
 

#########################
# METADATA
#########################
def metadata_dir(project_name, repo_name):
    print(">>>>> Creating metadata gitlab dir {}".format(METADATA_DIR))
    destination = os.path.join(TEMPORAL_PATH,project_name,repo_name)
    repo_url = "{}/{}/{}".format(BITBUCKET_REPOURL,project_name,repo_name)
    repo = git.Repo.clone_from(repo_url, destination)
    samidir = os.path.join(repo.working_dir,METADATA_DIR)
    os.mkdir(samidir)
    return repo,samidir


def metadata_push(repo):
    print(">>>>> Pushing metadata gitlab dir {}".format(METADATA_DIR))
    repo.index.add([METADATA_DIR])
    message = "Add gitlab metadata (issues,mergerequests,pipelines...)"
    repo.index.commit(message)
    repo.remotes.origin.push()


def metadata_remove(repo):
    destination = repo.working_dir
    subprocess.check_output('rm -fr '+destination, shell=True)

def bb_push(group_project):
    project = gitlab_conn.projects.get(group_project.get_id())
    bb_repo_name = project.attributes.get('path_with_namespace').split('/')[-1]
    print(">>>>> Processing {} repository".format(bb_repo_name))
    if len(project.commits.list()) == 0:
        print(">>>>> Project {} is empty".format(bb_repo_name))
        # print(">>>>> Archiving {} project".format(bb_repo_name))
        # project.archive()

    cloned_repo = clone_repo(project)
    create_repo(bb_project_name, bb_repo_name)
    bb_remote_name = add_remote_repo(cloned_repo, bb_project_name, bb_repo_name)
    push_repo(cloned_repo,bb_remote_name)
    remove_repo(project)

    #METADATA
    handle_metadata(features, bb_project_name, bb_repo_name, project)

def handle_metadata(features, project_name, repo_name, project):
    if len(features) != 0:
        ISSUES = True if features.find('Issues') != -1 else False
        MERGEREQUESTS = True if features.find('MergeRequests') != -1 else False
        PIPELINES = True if features.find('Pipelines') != -1 else False
        SNIPPETS = True if features.find('Snippets') != -1 else False
        WEBHOOKS = True if features.find('Webhooks') != -1 else False
        WIKI = True if features.find('Wiki') != -1 else False

    if ISSUES or MERGEREQUESTS or PIPELINES or SNIPPETS or WEBHOOKS or WIKI:
        metadata_repo,samidir = metadata_dir(project_name, repo_name)

    if ISSUES:
        if project.attributes.get('issues_enabled'):
            issues_dir = os.path.join(samidir,'issues')
            os.mkdir(issues_dir)
            for item in project.issues.list(all=True):
                item_name = "{}/{}.json".format(issues_dir,item.get_id())
                item_content = json.dumps(item.attributes,indent=4)+"\n"
                file(item_name,'w').write(item_content)

    if MERGEREQUESTS:
        if project.attributes.get('merge_requests_enabled'):
            mr_dir = os.path.join(samidir,'merge-requests')
            os.mkdir(mr_dir)
            for item in project.mergerequests.list(all=True):
                item_name = "{}/{}.json".format(mr_dir,item.get_id())
                item_content = json.dumps(item.attributes,indent=4)+"\n"
                file(item_name,'w').write(item_content)

    if PIPELINES:
        if project.attributes.get('jobs_enabled'):
            pipelines_dir = os.path.join(samidir,'pipelines')
            os.mkdir(pipelines_dir)
            for item in project.pipelines.list(all=True):
                item_name = "{}/{}.json".format(pipelines_dir,item.get_id())
                item_content = json.dumps(item.attributes,indent=4)+"\n"
                file(item_name,'w').write(item_content)

    if SNIPPETS:
        if project.attributes.get('snippets_enabled'):
            snippets_dir = os.path.join(samidir,'snippets')
            os.mkdir(snippets_dir)
            for item in project.snippets.list(all=True):
                item_name = "{}/{}.json".format(snippets_dir,item.get_id())
                item_content = json.dumps(item.attributes,indent=4)+"\n"
                file(item_name,'w').write(item_content)
                file(item_name,'a').write(item.content()+"\n")

    if WEBHOOKS:
        if len(project.hooks.list()):
            webhooks_dir = os.path.join(samidir,'webhooks')
            os.mkdir(webhooks_dir)
            for item in project.hooks.list(all=True):
                item_name = "{}/{}.json".format(webhooks_dir,item.get_id())
                item_content = json.dumps(item.attributes,indent=4)+"\n"
                file(item_name,'w').write(item_content)

    if WIKI:
        try:
            if project.attributes.get('wiki_enabled'):
                wiki_dir = os.path.join(samidir,'wikis')
                os.mkdir(wiki_dir)
                for item in project.wikis.list(all=True):
                    item_name = "{}/{}.json".format(wiki_dir,item.get_id())
                    file(item_name,'w').write(project.wikis.get(item.get_id()).content)
        except gitlab.GitlabListError:
            wiki_dir = os.path.join(samidir,'wikis')
            if not os.path.exists(wiki_dir):
                os.mkdir(wiki_dir)
            wiki_name = "{}/empty.json".format(wiki_dir)
            file(wiki_name,'w').write('NO WIKI FOUND!!!')

    if ISSUES or MERGEREQUESTS or PIPELINES or SNIPPETS or WEBHOOKS or WIKI:
        metadata_push(metadata_repo)
        metadata_remove(metadata_repo)

#########################
# main function
#########################
def main():
    usage = 'Usage: python migration.py <SAMI-GROUP> <BB-PROJECT> <FEATURES>\nYou can also specify <SAMI-GROUP>/<SAMI-PROJECT> if you want to migrate just one of them'
    if len(sys.argv) is not 4:
        print(usage)
        sys.exit(1)
    global gitlab_group_name, bb_project_name, features
    gitlab_group_name = sys.argv[1]
    if '/' in gitlab_group_name: #to migrate only one project from group
        gitlab_project = gitlab_group_name.split('/')[-1]
        gitlab_group_name = gitlab_group_name.split('/')[0]
    bb_project_name = sys.argv[2]
    features = sys.argv[3]

    if gitlab_group_name == '':
        print ">>>>> The Gitlab referenced group must contain a valid name (ls-infrastructure, ls-devops, etc...)"
        print(usage)
        sys.exit(1)

    if bb_project_name == '':
        print ">>>>> The Bitbucket referenced project must contain a valid name (INFRA, DEVOPS, etc...)"
        print(usage)
        sys.exit(1)
    
    connection()
    gitlab_group = check_group(gitlab_group_name)

    if gitlab_group != None:
        print(">>>>> Group to be cloned: {}".format(gitlab_group.attributes.get('name')))
    else:
        print(">>>>> The group <<{}>> does not exist,\n>>>>> please be sure the name passed is real".format(gitlab_group_name))
        sys.exit(1)

    if not os.path.exists(TEMPORAL_PATH):
        os.mkdir(TEMPORAL_PATH)
    try:
        project = gitlab_conn.projects.get(gitlab_group_name + '/' + gitlab_project) #if we have this project in gitlab and specified in arguments we'll migrate only it
        bb_push(project)
       #project.archive()
    except gitlab.exceptions.GitlabGetError:
        print(">>>>> There is no such a project {}\n".format(gitlab_project))
        sys.exit(1)
    except NameError: # if we have no argument we will migrate the whole group
        print(">>>>> Project is undefined, begin for all projects")
        for project in gitlab_group.projects.list(all=True):
            bb_push(project)
            #project.archive()
            time.sleep(1)


#####################
# MAIN
#####################
if __name__ == "__main__":
    main()
