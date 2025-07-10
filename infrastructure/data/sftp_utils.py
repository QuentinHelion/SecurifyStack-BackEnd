import paramiko
import os
from stat import S_ISDIR

def connect_sftp():
    host = os.getenv("SFTP_HOST")
    port = int(os.getenv("SFTP_PORT", 22))
    username = os.getenv("SFTP_USER")
    password = os.getenv("SFTP_PASS")

    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    return paramiko.SFTPClient.from_transport(transport)

def is_directory(sftp, path):
    try:
        return S_ISDIR(sftp.stat(path).st_mode)
    except IOError:
        return False


