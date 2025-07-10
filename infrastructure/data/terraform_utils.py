import subprocess
import os


def write_tfvars(path):
    tfvars = f'''
pm_api_url = "{os.getenv('PM_API_URL')}"
pm_user = "{os.getenv('PM_USER')}"
pm_password = "{os.getenv('PM_PASSWORD')}"
pm_tls_insecure = true

target_node = "{os.getenv('TARGET_NODE', 'proxmox')}"
hostname = "{os.getenv('HOSTNAME', 'my-lxc')}"
ostmpl = "{os.getenv('OSTMPL')}"
password = "{os.getenv('PASSWORD')}"
pool = "{os.getenv('POOL')}"
storage-location = "{os.getenv('STORAGE_LOCATION', 'local-lvm')}"
storage-size = "{os.getenv('STORAGE_SIZE', '8G')}"
network-bridge = "{os.getenv('NETWORK_BRIDGE', 'vmbr0')}"
network-ip = "{os.getenv('NETWORK_IP')}"
network-mask = "{os.getenv('NETWORK_MASK', '/24')}"
network-gw = "{os.getenv('NETWORK_GW')}"
ssh-certificat-path = "{os.getenv('SSH_CERT_PATH', '~/.ssh/id_rsa')}"
'''
    with open(os.path.join(path, 'terraform.tfvars'), 'w') as f:
        f.write(tfvars)


def execute_terraform(path):
    try:
        write_tfvars(path)

        init = subprocess.run(['terraform', 'init'], cwd=path, capture_output=True, text=True)
        if init.returncode != 0:
            return False, init.stderr

        apply = subprocess.run(['terraform', 'apply', '-auto-approve', '-var-file=terraform.tfvars'], cwd=path,
                               capture_output=True, text=True)
        if apply.returncode != 0:
            return False, apply.stderr

        return True, apply.stdout
    except Exception as e:
        return False, str(e)
