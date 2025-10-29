from pathlib import Path
from halo import Halo
from os import rmdir
import tibis.lib.logger as log
import tibis.lib.common as common
import tibis.lib.config as config
import tibis.lib.static as static

def lock(dirname):
    """Version optimisée du verrouillage"""
    if config.isEncrypting():
        log.error("Wait for previous operation to end")
    else:
        if not common.existsInDB(dirname):
            log.error("Directory not in database")
            return False
        if not common.isUnlocked(dirname):
            log.error("Directory is already locked")
            return False
        else:
            publicKeyLocation = common.getPublicKey(dirname)
            mountPoint = common.getMountPoint(dirname)
            
            if not mountPoint:
                log.error("MountPoint not found")
                return False
                
            if not Path(static.tibis_tmp_dir).exists():
                path = Path(static.tibis_tmp_dir)
                path.mkdir(parents=True, exist_ok=True)
                
            if publicKeyLocation:
                config.defineEncryptingStatus(True)
                
                # Nettoyer le répertoire temporaire
                [f.unlink() for f in Path(static.tibis_tmp_dir).glob("*") if f.is_file()]
                
                # Créer l'archive avec spinner
                spinner = Halo(text='Creating archive (parallel compression)', spinner='moon')
                spinner.start()
                archivePath = common.createArchive(dirname, mountPoint, static.tibis_tmp_dir)
                spinner.succeed('Archive created with optimized compression')
                
                # Vérification d'intégrité en parallèle si activée
                if config.check_integrity_status():
                    spinner = Halo(text='Checking integrity (parallel)', spinner='moon')
                    spinner.start()
                    
                    if config.use_parallel_hash():
                        with ThreadPoolExecutor(max_workers=2) as executor:
                            future_dir = executor.submit(
                                common.calculate_directory_hash_parallel, mountPoint
                            )
                            future_archive = executor.submit(
                                common.checkArchiveIntegrity, str(archivePath)
                            )
                            
                            directoryIntegrity = future_dir.result()
                            archiveIntegrity = future_archive.result()
                    else:
                        directoryIntegrity = common.calculate_directory_hash(mountPoint)
                        archiveIntegrity = common.checkArchiveIntegrity(str(archivePath))
                    
                    spinner.succeed('Integrity check completed (parallel)')
                    common.checkIntegrityIsOK(archiveIntegrity, directoryIntegrity, mountPoint)
                
                # Chiffrement
                spinner = Halo(text='Encrypting and moving', spinner='moon')
                spinner.start()
                isCrypted = common.cryptArchive(
                    publicKeyLocation, archivePath, 
                    config.storage_path(), dirname
                )
                spinner.succeed('Archive encrypted')
                
                if isCrypted:
                    spinner = Halo(text='Removing files', spinner='moon')
                    spinner.start()
                    [f.unlink() for f in Path(static.tibis_tmp_dir).glob("*") if f.is_file()]
                    common.remove_dir(mountPoint)
                    common.updateStatus(dirname, 'locked')
                    common.updateMountPoint(dirname, '')
                    spinner.succeed('Files removed')
                    log.success(f"{dirname} is locked")
                    config.defineEncryptingStatus(False)
                else:
                    log.error("Something went wrong...")
                    config.defineEncryptingStatus(False)



if __name__ == '__main__':
    lock(dirname)
