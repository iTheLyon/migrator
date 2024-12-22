from dotenv import load_dotenv
import os
import paramiko
import subprocess
import mysql.connector
from scp import SCPClient
import xml.etree.ElementTree as ET

load_dotenv()
# Credenciales del servidor remoto
SERVER_SOURCE_TYPE=os.getenv("SERVER_SOURCE_TYPE")
SSH_SOURCE_HOST=os.getenv("SSH_SOURCE_HOST")
SSH_SOURCE_USER=os.getenv("SSH_SOURCE_USER")
SSH_SOURCE_PASS=os.getenv("SSH_SOURCE_PASS")

# Credenciales para acceder a la base origen
DATABASE_SOURCE_HOST = os.getenv("DATABASE_SOURCE_HOST")
DATABASE_SOURCE_USER = os.getenv("DATABASE_SOURCE_USER")
DATABASE_SOURCE_PASS = os.getenv("DATABASE_SOURCE_PASS")
DATABASE_SOURCE_PORT = os.getenv("DATABASE_SOURCE_PORT")
DATABASE_SOURCE_NAME = os.getenv("DATABASE_SOURCE_NAME")
DATABASE_SOURCE_FILENAME=os.getenv("DATABASE_SOURCE_FILENAME")

# Credenciales del servidor destino
SERVER_TARGET_TYPE=os.getenv("SERVER_TARGET_TYPE")
SSH_TARGET_HOST=os.getenv("SSH_TARGET_HOST")
SSH_TARGET_USER=os.getenv("SSH_TARGET_USER")
SSH_TARGET_PASS=os.getenv("SSH_TARGET_PASS")

# Credenciales para acceder a la base objetivo
DATABASE_TARGET_USER =os.getenv("DATABASE_TARGET_USER")
DATABASE_TARGET_PASS =os.getenv("DATABASE_TARGET_PASS")
DATABASE_TARGET_PORT =os.getenv("DATABASE_TARGET_PORT")
DATABASE_TARGET_NAME =os.getenv("DATABASE_TARGET_NAME")
DATABASE_TARGET_FILENAME=os.getenv("DATABASE_TARGET_FILENAME")

DATABASE_LOCAL_HOST=os.getenv("DATABASE_LOCAL_HOST")
DATABASE_LOCAL_USER=os.getenv("DATABASE_LOCAL_USER")
DATABASE_LOCAL_PASS=os.getenv("DATABASE_LOCAL_PASS")
DATABASE_LOCAL_PORT=os.getenv("DATABASE_LOCAL_PORT")

# Ruta de los archivos SQL
SQL_A = DATABASE_SOURCE_NAME+".sql"
SQL_B = DATABASE_TARGET_NAME+".sql"
SQL_C = DATABASE_TARGET_NAME+".bak"
SQL_1 =os.getenv("SCRIPT_STRUCTURE") 
SQL_2 =os.getenv("SCRIPT_DATA")
SQL_3 =os.getenv("SCRIPT_FIX")

MC_EXECUTABLE=os.getenv("MC_EXECUTABLE")
arg_project_file =os.getenv("FILE_MC")
arg_script_file = SQL_1

MDC_EXECUTABLE=os.getenv("MDC_EXECUTABLE")
arg_project_file_2 =os.getenv("FILE_MDC")
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

def dump_database(ssh_client,db_user,db_pass ,db_name, dump_file):
    """Genera el dump de una base de datos en el servidor remoto"""
    print(f"Generando dump de la base de datos {db_name} en el servidor remoto...")
    command = f"mysqldump -u {db_user} -p{db_pass} {db_name} > {dump_file}"
    stdout, stderr = execute_remote_command(ssh_client, command)
    if stderr:
        print(f"\033[31mError ejecutando mysqldump: {stderr}\033[0m")
    else:
        print(f"Dump de {db_name} completado.")
    return stdout

def restore_database(ssh_client,db_name,restore_file):
    """Genera la restauracion de una base de datos en el servidor remoto"""
    check_db_exists = f"mysql -u {DATABASE_SOURCE_USER} -p{DATABASE_SOURCE_PASS} -P {DATABASE_SOURCE_PORT} -e \"SHOW DATABASES LIKE '{db_name}';\""
    drop_db = f"mysql -u {DATABASE_SOURCE_USER} -p{DATABASE_SOURCE_PASS} -P {DATABASE_SOURCE_PORT} -e 'DROP DATABASE `{db_name}`;'"
    create_db = f"mysql -u {DATABASE_SOURCE_USER} -p{DATABASE_SOURCE_PASS} -P {DATABASE_SOURCE_PORT} -e 'CREATE DATABASE `{db_name}`;'"
    execute_sql = f"mysql -u {DATABASE_SOURCE_USER} -p{DATABASE_SOURCE_PASS} -P {DATABASE_SOURCE_PORT} {db_name} < {restore_file};"

    # Verificar si la base de datos existe
    print(f"Verificando si la base de datos {db_name} existe...")
    stdout, stderr = execute_remote_command(ssh_client, check_db_exists)
    db_exists = stdout != ""
    if db_exists:
        print(f"La base de datos {db_name} existe, eliminando...")
        stdout, stderr =execute_remote_command(ssh_client,drop_db)
        stderr_output = stderr != ""
        if stderr_output:
            print(f"\033[31mError eliminando la base de datos: {stderr_output}\033[0m")

    # Crear la base de datos
    print(f"Creando la base de datos {db_name}...")    
    stdout, stderr = execute_remote_command(ssh_client,create_db)
    stderr_output = stderr != ""
    if stderr_output:
        print(f"\033[31mError creando la base de datos: {stderr_output}\033[0m")
    
    # Ejecutar el script SQL
    print(f"Ejecutando script SQL en {db_name}...")
    stdout, stderr = execute_remote_command(ssh_client,execute_sql)
    stderr_output = stderr != ""
    if stderr_output:
        print(f"\033[31mError ejecutando el script SQL: {stderr_output}\033[0m")
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
    connection = mysql.connector.connect(user=DATABASE_TARGET_NAME, password=DATABASE_LOCAL_PASS, database=db_name,port=DATABASE_LOCAL_PORT)
    cursor = connection.cursor()    
    cursor.execute(sql_script, multi=True)        
    connection.commit()
    cursor.close()
    connection.close()
    print(f"Ejecución de {sql_script} en la base de datos {db_name} completada.")

def execute_local_sql_from_file(db_name, sql_file):
    """Ejecuta un script SQL en la base de datos local"""
    print(f"Ejecutando el archivo {sql_file} en la base de datos {db_name}...!")
    connection = mysql.connector.connect(user=DATABASE_TARGET_NAME, password=DATABASE_LOCAL_PASS, database=db_name,port=DATABASE_LOCAL_PORT)
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
        '-u', DATABASE_LOCAL_USER,
        f'--password={DATABASE_LOCAL_PASS}',
        '-h', DATABASE_LOCAL_HOST,
        '-P', str(DATABASE_LOCAL_PORT),
        '-e', sqldropcreate +
        f"USE `{db_name}`;"+
        f"SOURCE {sql_file};"  # Ejecutar el archivo SQL con el comando 'source'
    ]
    
    try:
        # Ejecutar el comando mysql
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
     
        if result.returncode  == 0 and not("ERROR" in result.stderr):
            print(f"Archivo {sql_file} restaurado exitosamente en la base de datos {db_name}.")
        else:
            print(f"\033[31mError al restaurar el archivo {sql_file}: {result.stderr}\033[0m")
    
    except Exception as e:
        print(f"\033[31mOcurrió un error: {e}\033[0m")
        
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

    # # Comenzar desde el root y seguir la ruta de los tags
    # current_element = root
    # for tag in tags:
    #     current_element = current_element.find(tag)
    #     if current_element is None:
    #         print(f"Etiqueta '{tag}' no encontrada.")
    #         return

    # # Cambiar el valor dentro del último tag
    # print(f"Valor anterior: {current_element.text}")
    # current_element.text = new_value

    # Función recursiva para actualizar el valor en todos los elementos coincidentes
    def update_elements(element, tags):
        if not tags:
            element.text = new_value
            return

        current_tag = tags[0]
        remaining_tags = tags[1:]
        # Encuentra todos los elementos coincidentes y actualiza recursivamente
        for child in element.findall(current_tag):
            update_elements(child, remaining_tags)

    # Iniciar el proceso de actualización desde la raíz
    update_elements(root, tags)

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

def remove_lines_from_file(file_path, text_to_remove, output_file=None):
    """
    Elimina líneas de un archivo que contengan un texto específico.

    :param file_path: Ruta del archivo original.
    :param text_to_remove: Texto a buscar para eliminar las líneas que lo contengan.
    :param output_file: (Opcional) Ruta del archivo de salida. Si no se proporciona, sobrescribe el archivo original.
    """
    # Leer las líneas del archivo
    with open(file_path, "r", encoding="latin-1") as file:
        lines = file.readlines()

    # Filtrar las líneas que no contengan el texto a eliminar
    cleaned_lines = [line for line in lines if text_to_remove not in line]

    # Determinar el archivo de salida
    output_path = output_file if output_file else file_path

    # Escribir las líneas limpias en el archivo de salida
    with open(output_path, "w", encoding="utf-8") as file:
        file.writelines(cleaned_lines)

    print(f"Líneas que contienen '{text_to_remove}' han sido eliminadas de {output_path}.")

def remove_first_line(file_path, output_file=None):
    """
    Elimina la primera línea de un archivo y guarda el resultado.

    :param file_path: Ruta del archivo original.
    :param output_file: (Opcional) Ruta del archivo de salida. Si no se proporciona, sobrescribe el archivo original.
    """
    # Leer todas las líneas del archivo
    with open(file_path, "r",encoding="utf-8") as file:
        lines = file.readlines()

    # Filtrar todas las líneas excepto la primera
    cleaned_lines = lines[1:]

    # Determinar el archivo de salida
    output_path = output_file if output_file else file_path

    # Guardar las líneas resultantes
    with open(output_path, "w", encoding="utf-8") as file:
        file.writelines(cleaned_lines)

    print(f"Primera línea eliminada de {output_path}")

def backup_database(host, user, password, database_name, output_file='base.sql'):
    """
    Realiza un respaldo de la base de datos usando mysqldump.
    
    :param host: Dirección del servidor MySQL (por ejemplo, 'localhost').
    :param user: Usuario de MySQL.
    :param password: Contraseña del usuario de MySQL.
    :param database_name: Nombre de la base de datos a respaldar.
    :param output_file: Nombre del archivo donde se guardará el respaldo.
    :return: None
    """
    try:
        # Construir el comando mysqldump
        command = [
            'mysqldump',
            f'--host={host}',
            f'--user={user}',
            f'--password={password}',
            database_name
        ]
        
        # Abrir el archivo de salida en modo escritura binaria
        with open(output_file, 'wb') as output:
            # Ejecutar el comando
            subprocess.run(command, stdout=output, stderr=subprocess.PIPE, check=True)
        print(f"Respaldo completado: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"\033[31mError al realizar el respaldo: {e.stderr.decode()}\033[0m")
    except FileNotFoundError:
        print("\033[31mError: mysqldump no está instalado o no está en el PATH.\033[0m")

#INICIO DE PROGRAMA

path_remote_folder_scripts="/var/www/html/scripts/"

if SERVER_SOURCE_TYPE == "1":#remoto
    print("CONEXION SSH REMOTAMENTE A SERVIDOR ORIGEN")
    # Crear cliente SSH y conectarse al servidor fuente y dumpear  descargar y restaurar
    ssh_client = create_ssh_client(SSH_SOURCE_HOST, SSH_SOURCE_USER, SSH_SOURCE_PASS) 
    # Dump de la base de datos A
    dump_database(ssh_client,DATABASE_SOURCE_USER,DATABASE_SOURCE_PASS,DATABASE_SOURCE_NAME,path_remote_folder_scripts+SQL_A)
    dump_database(ssh_client,DATABASE_SOURCE_USER,DATABASE_SOURCE_PASS,DATABASE_SOURCE_NAME,path_remote_folder_scripts+"original_"+SQL_A)
    download_file(ssh_client, path_remote_folder_scripts+SQL_A, SQL_A)
    remove_first_line(SQL_A)

if SERVER_SOURCE_TYPE == "0":#local
    backup_database(DATABASE_SOURCE_HOST,DATABASE_SOURCE_USER,DATABASE_SOURCE_PASS,DATABASE_SOURCE_NAME,SQL_A)    


if SERVER_TARGET_TYPE == "1":#remoto
    print("CONEXION SSH REMOTAMENTE A SERVIDOR OBJETIVO")
    ssh_client_target = create_ssh_client(SSH_TARGET_HOST, SSH_TARGET_USER, SSH_TARGET_PASS) 
    dump_database(ssh_client_target,DATABASE_TARGET_USER ,DATABASE_TARGET_PASS,DATABASE_TARGET_NAME,path_remote_folder_scripts+SQL_B)
    dump_database(ssh_client_target,DATABASE_TARGET_USER ,DATABASE_TARGET_PASS,DATABASE_TARGET_NAME,path_remote_folder_scripts+"original_"+SQL_B)
    download_file(ssh_client_target, path_remote_folder_scripts+SQL_B, SQL_B)
    remove_first_line(SQL_B)

if SERVER_TARGET_TYPE == "0":#local
    print("BACKUP SERVIDOR OBJETIVO")
    #backup_database(DATABASE_SOURCE_HOST,DATABASE_SOURCE_USER,DATABASE_SOURCE_PASS,DATABASE_SOURCE_NAME,SQL_B)

# Eliminar y crear las bases de datos localmente
print("Eliminando y recreando la base de datos SOURCE localmente...")
restore_sql_file_with_source(DATABASE_SOURCE_NAME, SQL_A)

print("Eliminando y recreando la base de datos TARGET...")
restore_sql_file_with_source(DATABASE_TARGET_NAME, SQL_B)

# Eliminar y crear las bases de datos localmente
#if target_database_is_file:
#   print("Ajustes de tildes...(no)")
#restore_sql_file_with_source(DATABASE_TARGET_NAME, SQL_3,False)

# Ejecutar el programa mc para generar el archivo 1.sql y reemplazar textos
print("Ejecutando programa mc para generar comparacion estructural de Base Datos ...")
crear_archivo_si_no_existe(SQL_1)

update_xml_value(arg_project_file, "left/databaseName",f"{DATABASE_SOURCE_NAME}")
update_xml_value(arg_project_file, "left/userName",f"{DATABASE_LOCAL_USER}")
update_xml_value(arg_project_file, "left/server",f"{DATABASE_LOCAL_HOST}")
update_xml_value(arg_project_file, "left/port",f"{DATABASE_LOCAL_PORT}")

update_xml_value(arg_project_file, "right/databaseName",f"{DATABASE_TARGET_NAME}")
update_xml_value(arg_project_file, "right/userName",f"{DATABASE_LOCAL_USER}")
update_xml_value(arg_project_file, "right/server",f"{DATABASE_LOCAL_HOST}")
update_xml_value(arg_project_file, "right/port",f"{DATABASE_LOCAL_PORT}")

subprocess.run([MC_EXECUTABLE, f"/project:{arg_project_file}", f"/scriptfile:{arg_script_file}"])
replace_in_file(SQL_1, "''", "'")
replace_in_file(SQL_1, "DEFAULT 'NULL'", "")
#replace_in_file(SQL_1, "Ã¡", "á")
#replace_in_file(SQL_1, "DROP COLUMN `A├â┬▒oEmision`", "")
#replace_in_file(SQL_1, ", MODIFY COLUMN `IdAsignacionSede`", " MODIFY COLUMN `IdAsignacionSede`")
replace_in_file(SQL_1, "`comprobanteventa`\n  DROP COLUMN `IdSubTipoDocumento`\n  ,", "`comprobanteventa`\n")
#replace_in_file(SQL_1, "MODIFY COLUMN `IdCorrelativoDocumento`", "`comprobanteventa` MODIFY COLUMN `IdCorrelativoDocumento`")
#replace_in_file(SQL_1, "`AÃ±oEmision`","`AñoEmision`")
replace_in_file(SQL_1, "DROP COLUMN `FechaUltimoCobro`","")
replace_in_file(SQL_1, ", DROP COLUMN `MontoPenalidad`","")
replace_in_file(SQL_1, ", DROP COLUMN `NumeroSIAF`","")
replace_in_file(SQL_1, ", DROP COLUMN `EstadoOrdenCompraServicio`","")
replace_in_file(SQL_1, ", DROP COLUMN `EstadoNotaEntrega`\n  ,"," ")

replace_in_file(SQL_1, ", DROP COLUMN `PorcentajeIGV`","")

replace_in_file(SQL_1, "DROP COLUMN `CodigoEstablecimientoSUNATPuntoPartida`","")
replace_in_file(SQL_1, ", DROP COLUMN `CodigoEstablecimientoSUNATPuntoLlegada`\n  ,"," ")

#replace_in_file(SQL_1, ", ADD COLUMN `EstadoSincronizacion`","ADD COLUMN `EstadoSincronizacion`")
replace_in_file(SQL_1, ", DROP COLUMN `AñoEmisionDUADSI`","")

comentar_linea(SQL_1,"CREATE INDEX `FK_comprobanteventa_subtipodocumento`")
comentar_linea(SQL_1,"DROP FOREIGN KEY `FK_comprobanteventa_subtipodocumento`")

# Restaurar 1.sql en la base de datos B
restore_sql_file_with_source(DATABASE_TARGET_NAME, SQL_1,False)

# # Ejecutar el programa mdc para generar el archivo 2.sql y restaurarlo en la base de datos B
print("Ejecutando programa mdc para generar 2.sql...")
crear_archivo_si_no_existe(SQL_2)

update_xml_value(arg_project_file_2, "schemaMapping/source/string",DATABASE_SOURCE_NAME)
update_xml_value(arg_project_file_2, "schemaMapping/destination/string",DATABASE_TARGET_NAME)

update_xml_value(arg_project_file_2, "left/databaseName",f"{DATABASE_SOURCE_NAME}")
update_xml_value(arg_project_file_2, "left/userName",f"{DATABASE_LOCAL_USER}")
update_xml_value(arg_project_file_2, "left/server",f"{DATABASE_LOCAL_HOST}")
update_xml_value(arg_project_file_2, "left/port",f"{DATABASE_LOCAL_PORT}")

update_xml_value(arg_project_file_2, "right/databaseName",f"{DATABASE_TARGET_NAME}")
update_xml_value(arg_project_file_2, "right/userName",f"{DATABASE_LOCAL_USER}")
update_xml_value(arg_project_file_2, "right/server",f"{DATABASE_LOCAL_HOST}")
update_xml_value(arg_project_file_2, "right/port",f"{DATABASE_LOCAL_PORT}")

update_xml_value(arg_project_file_2, "tableMappings/tableMappings/tableMapping/lTableView/owner",f"{DATABASE_SOURCE_NAME}")
update_xml_value(arg_project_file_2, "tableMappings/tableMappings/tableMapping/rTableView/owner",f"{DATABASE_TARGET_NAME}")

subprocess.run([MDC_EXECUTABLE, f"/project:{arg_project_file_2}", f"/scriptfile:{arg_script_file_2}"])

comentar_linea(arg_script_file_2,f"UPDATE `{DATABASE_TARGET_NAME}`.`sede` SET `CodigoSede`='0000'")
comentar_linea(arg_script_file_2,f"UPDATE `{DATABASE_TARGET_NAME}`.`correlativodocumento`")
comentar_linea(arg_script_file_2,f"UPDATE `{DATABASE_TARGET_NAME}`.`parametrosistema` SET `NombreParametroSistema`='980148718'")
comentar_linea(arg_script_file_2,f"UPDATE `{DATABASE_TARGET_NAME}`.`parametrosistema` SET `NombreParametroSistema`='v0.81.240326.0948'")
comentar_linea(arg_script_file_2,f"DELETE FROM")
comentar_linea(arg_script_file_2,f"4, 'AMBOS', 'A', 'SFACT")
comentar_linea(arg_script_file_2,f"1, 'USO PERSONAL SIN DEVOLUCION'")
comentar_linea(arg_script_file_2,f"2, 'CALIDAD DE PRESTAMO',")
comentar_linea(arg_script_file_2,f"3, 'PARA CONSUMO'")

restore_sql_file_with_source(DATABASE_TARGET_NAME, SQL_2,False)

# # Hacer dump de la base de datos B y subirlo por SCP
print("Generando dump de la base de datos local target...")
backup_database(DATABASE_LOCAL_HOST,DATABASE_LOCAL_USER,DATABASE_LOCAL_PASS,DATABASE_TARGET_NAME,SQL_C)
# subprocess.run(["mysqldump","-u",DATABASE_TARGET_NAME,"-p" + DATABASE_LOCAL_PASS,"-P",DATABASE_LOCAL_PORT,DATABASE_TARGET_NAME,"-r",SQL_B])

#if not target_database_is_file:
    #upload_file(ssh_client, SQL_B, f"/var/www/html/scripts/{SQL_B}")
    # Ejecutar la restauración de la base de datos B en el servidor remoto
    #print("Restaurando la base de datos B en el servidor remoto...")
    #restore_database(ssh_client,DATABASE_TARGET_NAME,path_remote_folder_scripts+SQL_B)
    # Cerrar conexión SSH
if SERVER_SOURCE_TYPE == "1":#remoto
    ssh_client.close() 

if SERVER_TARGET_TYPE == "1":#remoto
    ssh_client_target.close()

print("Proceso completado.")
