import yaml 
import tibis.lib.static as static

def storage_path():
    with open(static.tibis_full_config_location) as file:
        p = yaml.load(file,Loader=yaml.FullLoader)
        return p['storage_path']
