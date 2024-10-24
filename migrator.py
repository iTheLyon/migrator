import os
import paramiko
import subprocess
import mysql.connector
from scp import SCPClient
import xml.etree.ElementTree as ET

# Credenciales del servidor remoto
SSH_HOST = "sfact.org.pe"
SSH_USER = "root"
SSH_PASS = "4320Abril6060"

# Credenciales para las bases de datos MySQL
DB_USER = "nenriquez"
DB_PASS = "20601956366@sfact"
DB_PORT ="3307"
DB_NAME_A = "10000000000"
DB_NAME_B = "20610816887"

DB_USER_LOCAL = "root"
DB_PASS_LOCAL = "root"
DB_PORT_LOCAL = "3306"
DB_HOST_LOCAL ="localhost"
# Ruta de los archivos SQL
SQL_A = DB_NAME_A+".sql"
SQL_B = DB_NAME_B+".sql"
SQL_1 = "script_estructura.sql"
SQL_2 = "script_datos.sql"

MC_EXECUTABLE=r"C:\Program Files (x86)\Red Gate\MySQL Compare 1\MC.exe"
arg_project_file = "2_migracion_estructura.mcp"
arg_script_file = SQL_1

MDC_EXECUTABLE=r"C:\Program Files (x86)\Red Gate\MySQL Data Compare 1\MDC.exe"
arg_project_file_2 = "4_migracion_datos.mdc"
arg_script_file_2 = SQL_2

def crear_archivo_si_no_existe(ruta_archivo):
    # Verificar si el archivo existe
    if not os.path.exists(ruta_archivo):
        # Crear el archivo
        with open(ruta_archivo, 'w') as archivo:
            archivo.write('')  # Crea el archivo vacío
        print(f"Archivo creado: {ruta_archivo}")
    else:
        print(f"El archivo ya existe: {ruta_archivo}")
        
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

def restore_database(ssh_client,db_name,restore_file):
    """Genera la restauracion de una base de datos en el servidor remoto"""
    check_db_exists = f"mysql -u {DB_USER} -p{DB_PASS} -P {DB_PORT} -e \"SHOW DATABASES LIKE '{db_name}';\""
    drop_db = f"mysql -u {DB_USER} -p{DB_PASS} -P {DB_PORT} -e 'DROP DATABASE `{db_name}`;'"
    create_db = f"mysql -u {DB_USER} -p{DB_PASS} -P {DB_PORT} -e 'CREATE DATABASE `{db_name}`;'"
    execute_sql = f"mysql -u {DB_USER} -p{DB_PASS} -P {DB_PORT} {db_name} < {restore_file};"

    # Verificar si la base de datos existe
    print(f"Verificando si la base de datos {db_name} existe...")
    stdout, stderr = execute_remote_command(ssh_client, check_db_exists)
    db_exists = stdout != ""
    if db_exists:
        print(f"La base de datos {db_name} existe, eliminando...")
        stdout, stderr =execute_remote_command(ssh_client,drop_db)
        stderr_output = stderr != ""
        if stderr_output:
            print(f"Error eliminando la base de datos: {stderr_output}")

    # Crear la base de datos
    print(f"Creando la base de datos {db_name}...")    
    stdout, stderr = execute_remote_command(ssh_client,create_db)
    stderr_output = stderr != ""
    if stderr_output:
        print(f"Error creando la base de datos: {stderr_output}")
    
    # Ejecutar el script SQL
    print(f"Ejecutando script SQL en {db_name}...")
    stdout, stderr = execute_remote_command(ssh_client,execute_sql)
    stderr_output = stderr != ""
    if stderr_output:
        print(f"Error ejecutando el script SQL: {stderr_output}")
    else:
        print("Script ejecutado correctamente.")


def download_file(ssh_client, remote_path, local_path):
    """Descarga un archivo por SCP desde el servidor remoto"""
    print(f"Descargando {remote_path} a {local_path}...")
    with SCPClient(ssh_client.get_transport()) as scp:
        scp.get(remote_path, local_path)
    print(f"Archivo {local_path} descargado.")

def upload_file(ssh_client, local_path, remote_path):
    """Sube un archivo por SCP al servidor remoto"""
    print(f"Subiendo {local_path} al servidor remoto en {remote_path}...")
    with SCPClient(ssh_client.get_transport()) as scp:
        scp.put(local_path, remote_path)
    print(f"Archivo {local_path} subido al servidor.")

def execute_local_sql(db_name, sql_script):
    """Ejecuta un script SQL en la base de datos local"""
    print(f"Ejecutando el archivo {sql_script} en la base de datos {db_name}...*")
    connection = mysql.connector.connect(user=DB_USER_LOCAL, password=DB_PASS_LOCAL, database=db_name,port=DB_PORT_LOCAL)
    cursor = connection.cursor()    
    cursor.execute(sql_script, multi=True)        
    connection.commit()
    cursor.close()
    connection.close()
    print(f"Ejecución de {sql_script} en la base de datos {db_name} completada.")

def execute_local_sql_from_file(db_name, sql_file):
    """Ejecuta un script SQL en la base de datos local"""
    print(f"Ejecutando el archivo {sql_file} en la base de datos {db_name}...!")
    connection = mysql.connector.connect(user=DB_USER_LOCAL, password=DB_PASS_LOCAL, database=db_name,port=DB_PORT_LOCAL)
    cursor = connection.cursor()
    with open(sql_file, 'r',encoding='utf-8') as f:
        sql_script = f.read()
    for result in cursor.execute(sql_script, multi=True):
        pass
    connection.commit()
    cursor.close()
    connection.close()
    print(f"Ejecución de {sql_file} en la base de datos {db_name} completada.")

def restore_sql_file_with_source(db_name, sql_file ,dropcreatedb = True):
    """Restaura un archivo SQL en una base de datos MySQL usando el comando mysql con source."""
    if(dropcreatedb):        
        sqldropcreate = f"DROP DATABASE IF EXISTS `{db_name}`; CREATE DATABASE IF NOT EXISTS `{db_name}`;"
    else:
        sqldropcreate=""
    # Construir el comando que incluye la opción 'source'
    command = [
        'mysql',
        '-u', DB_USER_LOCAL,
        f'--password={DB_PASS_LOCAL}',
        '-h', DB_HOST_LOCAL,
        '-P', str(DB_PORT_LOCAL),
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
        
def replace_in_file(file_path, old_text, new_text):
    """Reemplaza texto dentro de un archivo"""
    print(f"Reemplazando '{old_text}' por '{new_text}' en el archivo {file_path}...")
    with open(file_path, 'r') as file:
        data = file.read()
    data = data.replace(old_text, new_text)
    with open(file_path, 'w') as file:
        file.write(data)
    print(f"Reemplazo completado en {file_path}.")

def update_xml_value(file_path, tag_path, new_value):
    # Cargar y parsear el archivo XML
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Separar la ruta en los diferentes niveles de etiquetas (ejemplo: 'left/database')
    tags = tag_path.split('/')

    # Comenzar desde el root y seguir la ruta de los tags
    current_element = root
    for tag in tags:
        current_element = current_element.find(tag)
        if current_element is None:
            print(f"Etiqueta '{tag}' no encontrada.")
            return

    # Cambiar el valor dentro del último tag
    print(f"Valor anterior: {current_element.text}")
    current_element.text = new_value

    # Guardar los cambios en el archivo
    tree.write(file_path)
    print(f"Valor de '{tag_path}' actualizado a: {new_value}")

def comentar_linea(file_path, texto):
    # Leer el archivo línea por línea
    with open(file_path, 'r',encoding="latin-1") as file:
        lineas = file.readlines()

    # Abrir el archivo en modo escritura para guardar los cambios
    with open(file_path, 'w',encoding="latin-1") as file:
        for linea in lineas:
            if texto in linea:
                # Comentar la línea si contiene el texto
                linea = f"-- {linea}"
            file.write(linea)

    print(f"Líneas con el texto '{texto}' comentadas.")

# Crear cliente SSH y conectarse al servidor
ssh_client = create_ssh_client(SSH_HOST, SSH_USER, SSH_PASS)

path_remote_folder_scripts="/var/www/html/scripts/"
# Dump de la base de datos A
dump_database(ssh_client, DB_NAME_A,path_remote_folder_scripts+SQL_A)
dump_database(ssh_client, DB_NAME_A,path_remote_folder_scripts+"original_"+SQL_A)
download_file(ssh_client, SQL_A, SQL_A)

# Dump de la base de datos B
dump_database(ssh_client, DB_NAME_B,path_remote_folder_scripts+SQL_B)
dump_database(ssh_client, DB_NAME_B,path_remote_folder_scripts+"original_"+SQL_B)
download_file(ssh_client, SQL_B, SQL_B)

# Eliminar y crear las bases de datos localmente
print("Eliminando y recreando la base de datos A...")
restore_sql_file_with_source(DB_NAME_A, SQL_A)

print("Eliminando y recreando la base de datos B...")
restore_sql_file_with_source(DB_NAME_B, SQL_B)

# Ejecutar el programa mc para generar el archivo 1.sql y reemplazar textos
print("Ejecutando programa mc para generar 1.sql...")
crear_archivo_si_no_existe(SQL_1)

update_xml_value(arg_project_file, "left/databaseName",f"{DB_NAME_A}")
update_xml_value(arg_project_file, "left/userName",f"{DB_USER_LOCAL}")
update_xml_value(arg_project_file, "left/server",f"{DB_HOST_LOCAL}")
update_xml_value(arg_project_file, "left/port",f"{DB_PORT_LOCAL}")

update_xml_value(arg_project_file, "right/databaseName",f"{DB_NAME_B}")
update_xml_value(arg_project_file, "right/userName",f"{DB_USER_LOCAL}")
update_xml_value(arg_project_file, "right/server",f"{DB_HOST_LOCAL}")
update_xml_value(arg_project_file, "right/port",f"{DB_PORT_LOCAL}")

subprocess.run([MC_EXECUTABLE, f"/project:{arg_project_file}", f"/scriptfile:{arg_script_file}"])
replace_in_file(SQL_1, "''", "'")
replace_in_file(SQL_1, "DEFAULT 'NULL'", "")

# Restaurar 1.sql en la base de datos B
restore_sql_file_with_source(DB_NAME_B, SQL_1,False)

# # Ejecutar el programa mdc para generar el archivo 2.sql y restaurarlo en la base de datos B
print("Ejecutando programa mdc para generar 2.sql...")
crear_archivo_si_no_existe(SQL_2)

update_xml_value(arg_project_file_2, "schemaMapping/source/string",f"{DB_NAME_A}")
update_xml_value(arg_project_file_2, "schemaMapping/destination/string",f"{DB_NAME_B}")

update_xml_value(arg_project_file_2, "left/databaseName",f"{DB_NAME_A}")
update_xml_value(arg_project_file_2, "left/userName",f"{DB_USER_LOCAL}")
update_xml_value(arg_project_file_2, "left/server",f"{DB_HOST_LOCAL}")
update_xml_value(arg_project_file_2, "left/port",f"{DB_PORT_LOCAL}")

update_xml_value(arg_project_file_2, "right/databaseName",f"{DB_NAME_B}")
update_xml_value(arg_project_file_2, "right/userName",f"{DB_USER_LOCAL}")
update_xml_value(arg_project_file_2, "right/server",f"{DB_HOST_LOCAL}")
update_xml_value(arg_project_file_2, "right/port",f"{DB_PORT_LOCAL}")

update_xml_value(arg_project_file_2, "tableMappings/tableMappings/tableMapping/lTableView/owner",f"{DB_NAME_A}")
update_xml_value(arg_project_file_2, "tableMappings/tableMappings/tableMapping/rTableView/owner",f"{DB_NAME_B}")

subprocess.run([MDC_EXECUTABLE, f"/project:{arg_project_file_2}", f"/scriptfile:{arg_script_file_2}"])

comentar_linea(arg_script_file_2,f"UPDATE `{DB_NAME_B}`.`sede` SET `CodigoSede`='0000'")
comentar_linea(arg_script_file_2,f"UPDATE `{DB_NAME_B}`.`correlativodocumento`")
comentar_linea(arg_script_file_2,f"UPDATE `{DB_NAME_B}`.`parametrosistema` SET `NombreParametroSistema`='980148718'")
comentar_linea(arg_script_file_2,f"UPDATE `{DB_NAME_B}`.`parametrosistema` SET `NombreParametroSistema`='v0.81.240326.0948'")
comentar_linea(arg_script_file_2,f"DELETE FROM")

restore_sql_file_with_source(DB_NAME_B, SQL_2,False)

# # Hacer dump de la base de datos B y subirlo por SCP
print("Generando dump de la base de datos local B...")
subprocess.run(["mysqldump","-u",DB_USER_LOCAL,"-p" + DB_PASS_LOCAL,"-P",DB_PORT_LOCAL,DB_NAME_B,"-r",SQL_B])
upload_file(ssh_client, SQL_B, f"/var/www/html/scripts/{SQL_B}")

# Ejecutar la restauración de la base de datos B en el servidor remoto
print("Restaurando la base de datos B en el servidor remoto...")
restore_database(ssh_client,DB_NAME_B,path_remote_folder_scripts+SQL_B)

# Cerrar conexión SSH
ssh_client.close()

print("Proceso completado.")
