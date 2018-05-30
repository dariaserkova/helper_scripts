#!/usr/bin/env python
'''Reads config.yml file for other scripts
Returns dictionary with parameters'''

import yaml
import getpass


def main():
    try:
        with open("config.yml", 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
    except IOError:
        print('Can not find config.yml in the current directory')
        return None
    if 'jenkins_url' not in cfg:
        print('There is no mandatory parameter jenkins url in config')
        return None
    if 'user' not in cfg:
        print('Missing username in config. Please provide it via stdin.')
        cfg['user'] = raw_input('User: ')
    if 'token' not in cfg:
        print('Missing token in config. Please provide it via stdin.')
        cfg['token'] = getpass.getpass()
    return cfg


if __name__ == "__main__":
    main()



