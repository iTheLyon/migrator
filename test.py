from dotenv import load_dotenv
import os
load_dotenv()

SERVER_SOURCE_TYPE=os.getenv("SERVER_SOURCE_TYPE")
SSH_SOURCE_HOST=os.getenv("SSH_SOURCE_HOST")
SSH_SOURCE_USER =os.getenv("SSH_SOURCE_USER")
SSH_SOURCE_PASS =os.getenv("SSH_SOURCE_PASS")

print(f"type server : {SERVER_SOURCE_TYPE}")
print(f"Database Host: {SSH_SOURCE_HOST}")
print(f"Database user: {SSH_SOURCE_USER}")