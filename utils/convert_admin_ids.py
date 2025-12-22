from utils.logger import setup_logger

logger = setup_logger(__name__)

def convert_admin_ids(admin_list: str):
    """
        Utilitary function to convert each admin id to int when read from .env
        
        Parameters: 
            - admin_list: list of the admin ids (in generali ADMIN_IDS in config/costants.py)
    """
    if admin_list is None:
        logger.error("La lista degli admin non può essere vuota")
        return
    new_admin_list = []
    admin_list_formatted = admin_list.strip("[]").split(",")
    for id in admin_list_formatted:
        new_admin_list.append(id)
    return new_admin_list