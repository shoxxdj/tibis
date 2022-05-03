import pgpy
import getpass
import tibis.lib.common as common
import tibis.lib.static as static
import tibis.lib.logger as log
from pathlib import Path
from tibis.lib.common import getPrivateKey

def unlock(dirname,destination):
 #Verifier que c'est pas déja unlock
 if(not common.existsInDB(dirname)):
  log.error("Directory not in database")
  return False
 if(common.isUnlocked(dirname)):
  log.error("Already unlocked")
  return False
 else:
  #GetKey
  enc_privatekey, _ = pgpy.PGPKey.from_file(static.tibis_keys_location+"/"+dirname+"/private")
  #Unlock key
  log.ask("Enter passphrase :")
  p = getpass.getpass("")
  with enc_privatekey.unlock(p) as privatekey:
   #Uncrypt datas
   encrypted_content=pgpy.PGPMessage.from_file(static.tibis_storage_path+"/"+dirname)
   plaintext=privatekey.decrypt(encrypted_content).message
   #TODO Verify if its ok
   #Empty tmp dir
   [f.unlink() for f in Path(static.tibis_tmp_dir).glob("*") if f.is_file()]
   with open(static.tibis_tmp_dir+"/"+dirname,'wb') as archive:
   	archive.write(plaintext)

   #Prepare output
   path=Path(destination)
   path.mkdir(exist_ok=True,parents=True)
   common.uncompressArchive(static.tibis_tmp_dir+"/"+dirname,destination)
   if(common.updateStatus(dirname,"unlocked") and common.updateMountPoint(dirname,destination)):
   	log.success("Open at "+destination)
   [f.unlink() for f in Path(static.tibis_tmp_dir).glob("*") if f.is_file()]

if __name__ == '__main__':
    unlock(dirname,destination)
