from utils.logger import setup_logger
import os

logger = setup_logger(__name__)

def clean_download_directory(download_dir) -> None:
    """
    Clean the download directory before fetching new stories.
    Removes all files but keeps the directory structure.
    """
    if not os.path.exists(download_dir):
        logger.info(f"📁 Creating download directory: {download_dir}")
        os.makedirs(download_dir, exist_ok=True)
        return
    
    try:
        file_count = 0
        for filename in os.listdir(download_dir):
            file_path = os.path.join(download_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    file_count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    file_count += 1
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete {file_path}: {e}")
        
        if file_count > 0:
            logger.info(f"🧹 Cleaned {file_count} old files from {download_dir}")
        else:
            logger.info(f"✨ Download directory already clean")
            
    except Exception as e:
        logger.error(f"❌ Error cleaning download directory: {e}")

