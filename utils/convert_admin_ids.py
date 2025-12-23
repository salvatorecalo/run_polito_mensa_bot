from utils.logger import setup_logger

logger = setup_logger(__name__)

def convert_admin_ids(admin_list_str: str):
    if not admin_list_str or admin_list_str.strip() == "":
        logger.warning("La lista degli admin è vuota")
        return []
    
    clean_str = admin_list_str.replace("[", "").replace("]", "").replace('"', '').replace("'", "")
    
    new_admin_list = []
    for admin_id in clean_str.split(","):
        admin_id = admin_id.strip()
        if admin_id.isdigit():
            new_admin_list.append(int(admin_id))
            
    return new_admin_list