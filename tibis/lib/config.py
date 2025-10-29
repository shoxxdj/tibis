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
def compression_method():
    with open(static.tibis_full_config_location) as file:
        p = yaml.load(file,Loader=yaml.FullLoader)
        if('compression_method' in p):
            return p['compression_method']
        else:
            return 'gz'

def isEncrypting():
    with open(static.tibis_full_config_location) as file:
        p = yaml.load(file,Loader=yaml.FullLoader)
        if('encrypting' in p):
            return p['encrypting']
        else:
            return False

def defineEncryptingStatus(status):
    with open(static.tibis_full_config_location,'r+') as file:
        p = yaml.load(file,Loader=yaml.FullLoader)
        file.truncate(0)
        file.seek(0)
        p['encrypting']=status
        yaml.dump(p,file)

def get_compression_level():
    """Obtenir le niveau de compression configuré"""  
    try:
        with open(static.tibis_full_config_location) as file:
            p = yaml.load(file, Loader=yaml.FullLoader)
            if 'compression_level' in p:
                return p['compression_level']
    except:
        pass
    return 6  # Niveau par défaut

def get_compression_threads():
    """Obtenir le nombre de threads pour la compression"""   
    try:
        with open(static.tibis_full_config_location) as file:
            p = yaml.load(file, Loader=yaml.FullLoader)
            if 'compression_threads' in p:
                return p['compression_threads']
    except:
        pass
    return max(1, multiprocessing.cpu_count() - 1)

def use_parallel_hash():
    """Vérifier si on utilise le hash parallèle"""    
    try:
        with open(static.tibis_full_config_location) as file:
            p = yaml.load(file, Loader=yaml.FullLoader)
            if 'parallel_hash' in p:
                return p['parallel_hash']
    except:
        pass
    return True  # Activé par défaut