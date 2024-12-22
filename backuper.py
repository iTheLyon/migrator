from dotenv import load_dotenv
import os
import paramiko
import subprocess
import mysql.connector
from scp import SCPClient
load_dotenv()
# Credenciales del servidor remoto
SSH_HOST =os.getenv("SSH_SOURCE_HOST")
SSH_USER =os.getenv("SSH_SOURCE_USER")
SSH_PASS =os.getenv("SSH_SOURCE_PASS")
# Credenciales para las bases de datos MySQL remoto servidor
DB_USER = os.getenv("DATABASE_SOURCE_USER")
DB_PASS = os.getenv("DATABASE_SOURCE_PASS")
DB_PORT = os.getenv("DATABASE_SOURCE_PORT")

# Ruta de los archivos SQL
SQL_3 = "script_ajustar_tildes.sql"
        
def create_ssh_client(host, user, password):
    """Crea una sesión SSH"""
    print(f"Conectándose a {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password)
    print("Conexión SSH establecida.")
    return client

def execute_remote_command(client, command):
    """Ejecuta un comando en el servidor remoto"""
    print(f"Ejecutando comando remoto: {command}")
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.read().decode(), stderr.read().decode()

def dump_database(ssh_client, db_name, dump_file):
    """Genera el dump de una base de datos en el servidor remoto"""
    print(f"Generando dump de la base de datos {db_name} en el servidor remoto...")
    command = f"mysqldump -u {DB_USER} -p{DB_PASS} {db_name} > {dump_file}"
    stdout, stderr = execute_remote_command(ssh_client, command)
    if stderr:
        print(f"Error ejecutando mysqldump: {stderr}")
    else:
        print(f"Dump de {db_name} completado.")
    return stdout

def download_file(ssh_client, remote_path, local_path):
    """Descarga un archivo por SCP desde el servidor remoto"""
    print(f"Descargando {remote_path} a {local_path}...")
    with SCPClient(ssh_client.get_transport()) as scp:
        scp.get(remote_path, local_path)
    print(f"Archivo {local_path} descargado.")

def restore_sql_file_with_source(db_name, sql_file ,dropcreatedb = True,db_user="root",db_pass="root",db_port="3306",db_host="localhost"):
    """Restaura un archivo SQL en una base de datos MySQL usando el comando mysql con source."""
    if(dropcreatedb):        
        sqldropcreate = f"DROP DATABASE IF EXISTS `{db_name}`; CREATE DATABASE IF NOT EXISTS `{db_name}`;"
    else:
        sqldropcreate=""
    # Construir el comando que incluye la opción 'source'
   
    command = [
        'mysql',
        '-u', db_user,
        f'--password={db_pass}',
        '-h', db_host,
        '-P', str(db_port),
        '-e', sqldropcreate +
        f"USE `{db_name}`;"+
        f"SOURCE {sql_file};"  # Ejecutar el archivo SQL con el comando 'source'
    ]
    
    
     
    try:
        # Ejecutar el comando mysql
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            print(f"Archivo {sql_file} restaurado exitosamente en la base de datos {db_name}.")
        else:
            print(f"Error al restaurar el archivo {sql_file}: {result.stderr}")
    
    except Exception as e:        
        print(f"Ocurrió un error: {e}")
        
print("PROGRAMA PARA COPIAR BASE DE DATOS REMOTAMENTE Y RESTAURAR LOCALMENTE")
databasename=input("INGRESE EL NOMBRE DE BASE DE DATOS:")

database_is_file=False
# Crear cliente SSH y conectarse al servidor
if not database_is_file:
    ssh_client = create_ssh_client(SSH_HOST, SSH_USER, SSH_PASS)

path_remote_folder_scripts=os.getenv("PATH_REMOTE_FOLDER_SCRIPTS")


if not database_is_file:
    sqlfile=databasename+".sql"
    # Dump de la base de datos A
    dump_database(ssh_client, databasename,path_remote_folder_scripts+sqlfile)
    dump_database(ssh_client, databasename,path_remote_folder_scripts+"original_"+sqlfile)   
    download_file(ssh_client,path_remote_folder_scripts+sqlfile, sqlfile)

# Eliminar y crear las bases de datos localmente
print("Eliminando y recreando la base de datos A localmente...")
restore_sql_file_with_source(databasename, sqlfile)

# Eliminar y crear las bases de datos localmente
if database_is_file:
    print("Ajustes de tildes...")
    restore_sql_file_with_source(databasename, SQL_3,False)

if not database_is_file:
    # Cerrar conexión SSH
    ssh_client.close()

print("Proceso copia remota y restauracion local de base de datos completado.")
