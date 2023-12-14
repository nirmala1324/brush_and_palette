import os

file_path = "./static/admin/artwork/AW_ajbn.jpg"

try:
    os.remove(file_path)
    print(f"File {file_path} successfully deleted.")
except OSError as e:
    print(f"Error: {file_path} - {e}")