from pathlib import Path
from os import rmdir
import tibis.lib.logger as log
import tibis.lib.common as common
import tibis.lib.static as static

def lock(dirname):
 if(not common.existsInDB(dirname)):
 	log.error("Directory not in database")
 	return False
 if(not common.isUnlocked(dirname)):
 	log.error("Directory is already locked")
 	return False
 else:
  	#Get Keys
 	publicKeyLocation=common.getPublicKey(dirname)
 	mountPoint=common.getMountPoint(dirname)
 	if(publicKeyLocation):
 		#Create archive
 		[f.unlink() for f in Path(static.tibis_tmp_dir).glob("*") if f.is_file()]
 		archivePath=common.createArchive(dirname,mountPoint,static.tibis_tmp_dir)
 		common.cryptArchive(publicKeyLocation,archivePath,static.tibis_storage_path,dirname)
 		[f.unlink() for f in Path(static.tibis_tmp_dir).glob("*") if f.is_file()]
 		common.remove_dir(mountPoint)
 		common.updateStatus(dirname,'locked')
 		common.updateMountPoint(dirname,'')
 		log.success(dirname+" is locked")

if __name__ == '__main__':
    lock(dirname)
