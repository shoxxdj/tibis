import tarfile
import sqlite3
import pgpy
import tibis.lib.logger as log
import tibis.lib.static as static
import tibis.lib.config as config

from pathlib import Path
import os 

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

def uncompressArchive(source,dest):
 with tarfile.open(source,"r:gz") as tar:
  tar.extractall(dest)

def deleteArchive(source):
	remove_dir(source)

def createArchive(dirname,source,dest):
	with tarfile.open(dest+"/"+dirname+".gz","w:gz") as tar:
		for fn in os.listdir(source):
			p = os.path.join(source, fn)
			tar.add(p, arcname=fn)
		#tar.add(source,arcname=dirname)
	return dest+"/"+dirname+".gz"

def cryptArchive(keyPath,source,dest,dirname):
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