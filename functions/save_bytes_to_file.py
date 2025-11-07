def save_bytes_to_file(bts: bytes, path: str) -> None:
    "This function store image on folder stories"
    with open(path, "wb") as f:
        f.write(bts)