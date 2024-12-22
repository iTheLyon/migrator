from dotenv import load_dotenv
import os
import paramiko

load_dotenv()
def execute_ssh_command(ssh_client, command):
    """
    Ejecuta un comando en un servidor remoto mediante SSH.
    """
    stdin, stdout, stderr = ssh_client.exec_command(command)
    stdout_text = stdout.read().decode("utf-8")
    stderr_text = stderr.read().decode("utf-8")
    if stderr_text:
        raise Exception(f"Error al ejecutar el comando: {stderr_text}")
    return stdout_text


def zip_folder_remote(ssh_client, remote_folder, zip_file_path):
    """
    Comprime una carpeta en el servidor remoto.
    """
    command = f"zip -r {zip_file_path} {remote_folder}"
    execute_ssh_command(ssh_client, command)
    print(f"Carpeta comprimida en: {zip_file_path}")


def download_file(ssh_client, remote_file, local_file):
    """
    Descarga un archivo desde el servidor remoto.
    """
    sftp = ssh_client.open_sftp()
    sftp.get(remote_file, local_file)
    sftp.close()
    print(f"Archivo descargado: {local_file}")


def upload_file(ssh_client, local_file, remote_file):
    """
    Sube un archivo a un servidor remoto.
    """
    sftp = ssh_client.open_sftp()
    sftp.put(local_file, remote_file)
    sftp.close()
    print(f"Archivo subido: {remote_file}")


def unzip_folder_remote(ssh_client, zip_file_path, destination_folder):
    """
    Descomprime un archivo en el servidor remoto.
    """
    command = f"unzip {zip_file_path} -d {destination_folder}"
    execute_ssh_command(ssh_client, command)
    print(f"Archivo descomprimido en: {destination_folder}")


def apply_permissions_remote(ssh_client, folder_path, user_group, permissions):
    """
    Aplica permisos y cambia propietario/grupo en un servidor remoto.
    """
    commands = [
        f"chown -R {user_group} {folder_path}",
        f"chmod -R {permissions} {folder_path}",
    ]
    for command in commands:
        execute_ssh_command(ssh_client, command)
    print(f"Permisos aplicados en {folder_path}: chown {user_group}, chmod {permissions}")


def connect_to_server(hostname, username, password, port=22):
    """
    Conecta a un servidor remoto mediante SSH.
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, password=password, port=port)
    return ssh


# Configuración de servidores y carpetas
remote1 = {
    "hostname": os.getenv("SSH_SOURCE_HOST"),
    "username": os.getenv("SSH_SOURCE_USER"),
    "password": os.getenv("SSH_SOURCE_PASS"),
    "remote_folder": os.getenv("REMOTE_FOLDER_1"),
    "zip_file": os.getenv("ZIP_FILE1")
}
remote2 = {
    "hostname":os.getenv("REMOTE_FOLDER_2"),
    "username": os.getenv("USER_2"),
    "password": os.getenv("PASSWORD_2"),
    "destination_folder": os.getenv("DESTINATION_FOLDER_2"),
    "destination_folder_ruc": os.getenv("DESTINATION_FOLDER_RUC_2")
}
local_zip_file = os.getenv("LOCAL_ZIP_FILE")
user_group = os.getenv("USER_GROUP")
permissions = os.getenv("PERMISSIONS")

# # Conectar al servidor 1
# ssh1 = connect_to_server(remote1["hostname"], remote1["username"], remote1["password"])

# # Comprimir la carpeta en el servidor 1
# zip_folder_remote(ssh1, remote1["remote_folder"], remote1["zip_file"])

# # Descargar el archivo ZIP desde el servidor 1
# download_file(ssh1, remote1["zip_file"], local_zip_file)
# ssh1.close()

# Conectar al servidor 2
ssh2 = connect_to_server(remote2["hostname"], remote2["username"], remote2["password"])

# Subir el archivo ZIP al servidor 2
upload_file(ssh2, local_zip_file, remote1["zip_file"])

# Descomprimir el archivo en el servidor 2
unzip_folder_remote(ssh2, remote1["zip_file"], remote2["destination_folder"])

# Aplicar permisos en el servidor 2
apply_permissions_remote(ssh2, remote2["destination_folder_ruc"], user_group, permissions)

# Cerrar conexión al servidor 2
ssh2.close()

print("Proceso completado.")
