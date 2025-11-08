"""
Utilities per operazioni su file
"""
import os
from typing import List


def save_bytes_to_file(bts: bytes, path: str) -> None:
    """
    Salva bytes su file.
    
    Args:
        bts: Contenuto binario da salvare
        path: Percorso del file di destinazione
    """
    with open(path, "wb") as f:
        f.write(bts)


def clean_directory(directory: str, extensions: List[str] | None = None) -> int:
    """
    Pulisce una directory rimuovendo tutti i file (opzionalmente filtrati per estensione).
    
    Args:
        directory: Percorso della directory da pulire
        extensions: Lista di estensioni da rimuovere (es: ['.jpg', '.png']). 
                   Se None, rimuove tutti i file.
    
    Returns:
        Numero di file rimossi
    """
    if not os.path.exists(directory):
        return 0
    
    count = 0
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if not os.path.isfile(file_path):
            continue
        
        # Filtra per estensione se specificato
        if extensions and not any(filename.endswith(ext) for ext in extensions):
            continue
        
        try:
            os.remove(file_path)
            count += 1
        except Exception as e:
            print(f"⚠️ Impossibile rimuovere {file_path}: {e}")
    
    return count