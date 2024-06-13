import os
from dotenv import load_dotenv, set_key, find_dotenv

# Nombre del archivo .env
dotenv_path = find_dotenv()

# Cargar el archivo .env existente o crear uno nuevo si no existe
if not dotenv_path:
    with open('.env', 'w'):
        pass
    dotenv_path = find_dotenv()

# Cargar variables del archivo .env
load_dotenv(dotenv_path=dotenv_path)

# Especificar la clave y el valor que deseas actualizar o agregar
API_KEY_NAME = "OPENAI_API_KEY"
NEW_API_KEY_VALUE = ""  # Reemplaza con tu nueva clave API

# Actualizar o agregar la clave en el archivo .env
set_key(dotenv_path, API_KEY_NAME, NEW_API_KEY_VALUE)

print(f"{API_KEY_NAME} ha sido establecida a {NEW_API_KEY_VALUE}")

