import tarfile
import sqlite3
import hashlib
import pgpy
import tibis.lib.logger as log
import tibis.lib.static as static
import tibis.lib.config as config

import subprocess
from pathlib import Path
import os 
import sys
import threading
import time
import shutil
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from halo import Halo

def get_available_compressors():
    """Détecte les compresseurs disponibles sur le système"""
    compressors = {
        'pigz': shutil.which('pigz'),      # gzip parallèle
        'pbzip2': shutil.which('pbzip2'),  # bzip2 parallèle
        'xz': shutil.which('xz'),          # xz
        'pxz': shutil.which('pxz'),        # xz parallèle
        'lz4': shutil.which('lz4'),        # lz4 ultra-rapide
        'zstd': shutil.which('zstd'),      # zstandard (bon compromis)
    }
    return {k: v for k, v in compressors.items() if v is not None}

def get_compression_command(method, level, threads):
    """Retourne la commande de compression optimale selon la méthode"""
    available = get_available_compressors()
    
    if method in ['gz', 'gzip']:
        if 'pigz' in available:
            # pigz est 3-4x plus rapide que gzip
            return ['pigz', f'-{level}', f'-p{threads}']
        else:
            return ['gzip', f'-{level}']
    
    elif method in ['bz2', 'bzip2']:
        if 'pbzip2' in available:
            # pbzip2 utilise tous les cœurs
            return ['pbzip2', f'-{level}', f'-p{threads}']
        else:
            return ['bzip2', f'-{level}']
    
    elif method == 'xz':
        if 'pxz' in available:
            # pxz pour xz parallèle
            return ['pxz', f'-{level}', f'-T{threads}']
        elif 'xz' in available:
            # xz standard avec multi-threading
            return ['xz', f'-{level}', f'-T{threads}']
        else:
            return None
    
    elif method == 'lz4':
        if 'lz4' in available:
            # lz4 est le plus rapide (mais moins de compression)
            return ['lz4', f'-{level}']
        else:
            return None
    
    elif method == 'zstd':
        if 'zstd' in available:
            # zstd offre un excellent compromis vitesse/ratio
            return ['zstd', f'-{level}', f'-T{threads}']
        else:
            return None
    
    return None

def existsInDB(name):
	rows=True
	try:
		db=static.tibis_db_location
		conn=sqlite3.connect(db)
		cursor_obj = conn.cursor()
		cursor_obj.execute("SELECT name FROM tibis WHERE name=?", [name])

		rows = cursor_obj.fetchall()
	except Exception as e:
		raise e
	finally:
		conn.close()
		if(rows):
			return True
		else:
			return False

def getPrivateKey(name):
	rows=True
	try:
		db=static.tibis_db_location
		conn=sqlite3.connect(db)
		cursor_obj = conn.cursor()
		cursor_obj.execute("SELECT private_key_path as private FROM tibis WHERE name=?", [name])
		rows = cursor_obj.fetchone()	
	except Exception as e:
		raise e
	finally:
		conn.close()
		private_key_path=rows[0]
		if(Path(private_key_path).is_file()):
			return private_key_path
		else:
			return False

def getPublicKey(name):
	rows=True
	try:
		db=static.tibis_db_location
		conn=sqlite3.connect(db)
		cursor_obj = conn.cursor()
		cursor_obj.execute("SELECT public_key_path as public FROM tibis WHERE name=?", [name])
		rows = cursor_obj.fetchone()	
	except Exception as e:
		raise e
	finally:
		conn.close()
		public_key_path=rows[0]
		if(Path(public_key_path).is_file()):
			return public_key_path
		else:
			return False

def getMountPoint(name):
	rows=True
	try:
		db=static.tibis_db_location
		conn=sqlite3.connect(db)
		cursor_obj = conn.cursor()
		cursor_obj.execute("SELECT mount_point as mp FROM tibis WHERE name=?", [name])
		rows = cursor_obj.fetchone()	
	except Exception as e:
		raise e
	finally:
		conn.close()
		mp=rows[0]
		if(Path(mp).is_dir()):
			return mp
		else:
			return False

def updateMountPoint(name,mountPoint):
	allGood=False
	if(existsInDB(name)):
		try:
			db=static.tibis_db_location
			conn=sqlite3.connect(db)
			cursor_obj=conn.cursor()
			cursor_obj.execute("UPDATE tibis SET mount_point=? WHERE name=?",[mountPoint,name])
			conn.commit()
			allGood=True
		except Exception as e:
			raise e 
		finally:
			conn.close()
			return allGood

def isUnlocked(name):
	rows=True
	try:
		db=static.tibis_db_location
		conn=sqlite3.connect(db)
		cursor_obj = conn.cursor()
		cursor_obj.execute("SELECT status as status FROM tibis WHERE name=?", [name])
		rows = cursor_obj.fetchone()	
	except Exception as e:
		raise e
	finally:
		conn.close()
		status=rows[0]
		if(status=='unlocked'):
			return True
		else:
			return False

def updateStatus(name,status):
	allGood=False
	if(existsInDB(name)):
		try:
			db=static.tibis_db_location
			conn=sqlite3.connect(db)
			cursor_obj=conn.cursor()
			cursor_obj.execute("UPDATE tibis SET status=? WHERE name=?",[status,name])
			conn.commit()
			allGood=True
		except Exception as e:
			raise e 
		finally:
			conn.close()
			return allGood

def uncompressArchive(source, dest):
    """Version optimisée de la décompression avec outils parallèles"""
    compression = config.compression_method()
    threads = config.get_compression_threads()
    
    # Détecter l'extension
    if source.endswith('.tar.gz') or source.endswith('.tgz'):
        method = 'gz'
    elif source.endswith('.tar.bz2') or source.endswith('.tbz2'):
        method = 'bz2'
    elif source.endswith('.tar.xz') or source.endswith('.txz'):
        method = 'xz'
    elif source.endswith('.tar.lz4'):
        method = 'lz4'
    elif source.endswith('.tar.zst'):
        method = 'zstd'
    else:
        method = compression
    
    available = get_available_compressors()
    tar_path = source.replace('.gz', '').replace('.bz2', '').replace('.xz', '').replace('.lz4', '').replace('.zst', '')
    
    # Décompression parallèle si disponible
    decompress_cmd = None
    
    if method in ['gz', 'gzip'] and 'pigz' in available:
        decompress_cmd = ['pigz', '-d', '-c', f'-p{threads}']
    elif method in ['bz2', 'bzip2'] and 'pbzip2' in available:
        decompress_cmd = ['pbzip2', '-d', '-c', f'-p{threads}']
    elif method == 'xz' and 'pxz' in available:
        decompress_cmd = ['pxz', '-d', '-c', f'-T{threads}']
    elif method == 'xz' and 'xz' in available:
        decompress_cmd = ['xz', '-d', '-c', f'-T{threads}']
    elif method == 'lz4' and 'lz4' in available:
        decompress_cmd = ['lz4', '-d', '-c']
    elif method == 'zstd' and 'zstd' in available:
        decompress_cmd = ['zstd', '-d', '-c', f'-T{threads}']
    
    if decompress_cmd:
        # Décompression avec outil externe
        try:
            with open(source, 'rb') as compressed:
                process = subprocess.Popen(
                    decompress_cmd,
                    stdin=compressed,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Extraire le tar à la volée
                with tarfile.open(fileobj=process.stdout, mode='r|') as tar:
                    def is_within_directory(directory, target):
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        return prefix == abs_directory
                    
                    for member in tar:
                        member_path = os.path.join(dest, member.name)
                        if not is_within_directory(dest, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                        tar.extract(member, dest)
                
                process.wait()
                if process.returncode != 0:
                    stderr = process.stderr.read().decode()
                    raise Exception(f"Decompression failed: {stderr}")
        except Exception as e:
            log.warning(f"External decompression failed: {e}, falling back to standard method")
            # Fallback
            _uncompressArchive_standard(source, dest)
    else:
        # Fallback: décompression standard
        _uncompressArchive_standard(source, dest)


def _uncompressArchive_standard(source, dest):
    """Méthode de décompression standard (fallback)"""
    compression = config.compression_method()
    mode = f"r:{compression}" if compression else "r"
    
    with tarfile.open(source, mode, bufsize=10*1024*1024) as tar:
        def is_within_directory(directory, target):
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            prefix = os.path.commonprefix([abs_directory, abs_target])
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
            tar.extractall(path, members, numeric_owner=numeric_owner)
        
        safe_extract(tar, dest)

def deleteArchive(source):
	remove_dir(source)

def createArchive(dirname, source, dest):
    """Version optimisée avec compression parallèle externe"""
    try:
        compression = config.compression_method()
        level = config.get_compression_level()
        threads = config.get_compression_threads()
        
        # Mapper les extensions
        ext_map = {
            'gz': 'tar.gz', 'gzip': 'tar.gz',
            'bz2': 'tar.bz2', 'bzip2': 'tar.bz2',
            'xz': 'tar.xz',
            'lz4': 'tar.lz4',
            'zstd': 'tar.zst'
        }
        extension = ext_map.get(compression, f'tar.{compression}')
        
        tar_path = f"{dest}/{dirname}.tar"
        output_path = f"{dest}/{dirname}.{extension}"
        
        # Étape 1: Créer l'archive tar non compressée
        with tarfile.open(tar_path, 'w', bufsize=10*1024*1024) as tar:
            def reset_tarinfo(tarinfo):
                tarinfo.mtime = 0
                tarinfo.uid = tarinfo.gid = 0
                tarinfo.uname = tarinfo.gname = ""
                return tarinfo
            
            for fn in os.listdir(source):
                p = os.path.join(source, fn)
                tar.add(p, arcname=fn, filter=reset_tarinfo)
        
        # Étape 2: Compression parallèle avec outil externe
        compress_cmd = get_compression_command(compression, level, threads)
        
        if compress_cmd:
            # Utiliser compresseur externe optimisé
            with open(tar_path, 'rb') as input_file:
                with open(output_path, 'wb') as output_file:
                    process = subprocess.Popen(
                        compress_cmd,
                        stdin=input_file,
                        stdout=output_file,
                        stderr=subprocess.PIPE
                    )
                    _, stderr = process.communicate()
                    
                    if process.returncode != 0:
                        raise Exception(f"Compression failed: {stderr.decode()}")
            
            # Supprimer le tar non compressé
            os.remove(tar_path)
        else:
            # Fallback: compression intégrée Python
            log.warning(f"No parallel compressor found for {compression}, using standard compression")
            os.remove(tar_path)
            
            with tarfile.open(output_path, f"w:{compression}", 
                             bufsize=10*1024*1024) as tar:
                def reset_tarinfo(tarinfo):
                    tarinfo.mtime = 0
                    tarinfo.uid = tarinfo.gid = 0
                    tarinfo.uname = tarinfo.gname = ""
                    return tarinfo
                
                for fn in os.listdir(source):
                    p = os.path.join(source, fn)
                    tar.add(p, arcname=fn, filter=reset_tarinfo)
        
        return output_path
        
    except NotADirectoryError:
        log.error(f"Source directory {source} not found")
        config.defineEncryptingStatus(False)
        raise
    except Exception as e:
        log.error(f"Unexpected Error: {type(e).__name__} - {e}")
        raise

	


def cryptArchive(keyPath,source,dest,dirname):
	try:
		pubkey,_ = pgpy.PGPKey.from_file(keyPath)
		# file = open(source, "rb")
		# data = file.read()
		# file.close()
		# message = pgpy.PGPMessage.new(data)
		file_message=pgpy.PGPMessage.new(source,file=True)
		encrypted_message = pubkey.encrypt(file_message)

		#Important remove the clear content
		deleteArchive(source)
		#Save data into storage
		outputfile=dest+"/"+dirname

		#bytes_data=bytes(encrypted_message)

		with open(outputfile,'wb') as destFile:
			destFile.write(bytes(encrypted_message))
		return True
	except Exception as e:
		print(e)
		return False

def remove_dir(directory):
    path=Path(directory)
    if path.is_file() or path.is_symlink():
        path.unlink()
        return
    for p in path.iterdir():
        remove_dir(p)
    path.rmdir()

def deleteSQLEntry(name):
	allGood=False
	if(existsInDB(name)):
		try:
			db=static.tibis_db_location
			conn=sqlite3.connect(db)
			cursor_obj=conn.cursor()
			cursor_obj.execute("DELETE FROM tibis WHERE name=?",[name])
			conn.commit()
			allGood=True
		except Exception as e:
			raise e 
		finally:
			conn.close()
			return allGood

def calculate_directory_hash_parallel(directory, algorithm="sha256"):
    """Calcul parallèle des hash pour améliorer les performances"""
    import hashlib
    
    def hash_file(file_path):
        """Fonction pour hasher un fichier individuellement"""
        try:
            hasher = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                while chunk := f.read(65536):  # 64KB chunks
                    hasher.update(chunk)
            return (file_path, hasher.hexdigest())
        except Exception as e:
            log.error(f"Error hashing {file_path}: {e}")
            return (file_path, None)
    
    # Collecter tous les fichiers
    files_to_hash = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            files_to_hash.append(os.path.join(root, file))
    
    # Hasher en parallèle
    file_hashes = {}
    cpu_count = max(1, multiprocessing.cpu_count() - 1)
    
    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        results = executor.map(hash_file, files_to_hash)
        for file_path, hash_value in results:
            if hash_value:
                file_hashes[file_path] = hash_value
    
    return file_hashes


def calculate_tar_hash_parallel(archive_path, algorithm="sha256"):
    """Calcul parallèle des hash d'archive"""
    import hashlib
    
    compression = config.compression_method()
    mode = f"r:{compression}" if compression else "r"
    
    tar = tarfile.open(archive_path, mode)
    
    def hash_member(member_info):
        """Hash un membre du tar"""
        tar_local = tarfile.open(archive_path, mode)
        member, idx = member_info
        try:
            if member.isfile():
                file_content = tar_local.extractfile(member).read()
                hasher = hashlib.new(algorithm)
                hasher.update(file_content)
                return (member.name, hasher.hexdigest())
        except Exception as e:
            log.error(f"Error hashing {member.name}: {e}")
        finally:
            tar_local.close()
        return (member.name, None)
    
    members = [(m, i) for i, m in enumerate(tar.getmembers()) if m.isfile()]
    tar.close()
    
    file_hashes = {}
    cpu_count = max(1, multiprocessing.cpu_count() - 1)
    
    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        results = executor.map(hash_member, members)
        for name, hash_value in results:
            if hash_value:
                file_hashes[name] = hash_value
    
    return file_hashes


def calculate_hash(file_content, algorithm="sha256"):
    hasher = hashlib.new(algorithm)
    hasher.update(file_content)
    return hasher.hexdigest()

def calculate_tar_hash(archive_path, algorithm="sha256"):
    tar = tarfile.open(archive_path, "r")
    file_hashes = {}

    for member in tar.getmembers():
        if member.isfile():
            file_content = tar.extractfile(member).read()
            file_hash = calculate_hash(file_content, algorithm)
            file_hashes[member.name] = file_hash

    tar.close()
    return file_hashes

def calculate_directory_hash(directory, algorithm="sha256"):
    """Version standard (fallback)"""
    file_hashes = {}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                content = f.read()
                file_hash = calculate_hash(content, algorithm)
                file_hashes[file_path] = file_hash
    return file_hashes

def checkArchiveIntegrity(archive_path):
    """Version optimisée avec calcul parallèle"""
    return calculate_tar_hash_parallel(archive_path)

def checkIntegrityIsOK(archiveIntegrity,directoryIntegrity,mountPoint):
	if(len(archiveIntegrity) != len(directoryIntegrity)):
		log.error("Not the same files")
		log.error("Archive Content : "+str(archiveIntegrity))
		log.error("Directory Content : "+str(directoryIntegrity))
		sys.exit("ERROR")

	_directoryIntegrity=[]
	_archiveIntegrity=[]

	if(mountPoint[::-1][0]!='/'):
		mountPoint+="/"
	#CleanDirectoryIntegrity to remove mountPointValue
	for obj in directoryIntegrity:
		_directoryIntegrity.append({obj.replace(mountPoint,""):directoryIntegrity[obj]})
	for obj in archiveIntegrity:
		_archiveIntegrity.append({obj:archiveIntegrity[obj]})
	
	# Convert data1 and data2 to sets of frozensets
	set1 = {frozenset(item.items()) for item in _archiveIntegrity}
	set2 = {frozenset(item.items()) for item in _directoryIntegrity}

	if(set1!=set2 or set2!=set1):
		log.error("Integrity error")
		log.error("Archive Content : "+archiveIntegrity)
		log.error("Directory Content : "+directoryIntegrity)
		sys.exit(1)
	else:
		log.success("Same integrity between archive and content")