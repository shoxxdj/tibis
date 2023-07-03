import yaml 
import tibis.lib.static as static
import sys

def storage_path():
    with open(static.tibis_full_config_location) as file:
        p = yaml.load(file,Loader=yaml.FullLoader)
        return p['storage_path']

def pgp_infos():
    with open(static.tibis_full_config_location) as file:
        p = yaml.load(file,Loader=yaml.FullLoader)
        return p['pgp_infos']

def check_integrity_status():
    with open(static.tibis_full_config_location) as file:
        p = yaml.load(file,Loader=yaml.FullLoader)
        if('check_integrity' in p ):
            return p['check_integrity']
        else:
            return True