import os
import subprocess
import re

class TerraformService:
    @staticmethod
    def write_tfvars_file(terraform_script_path, tfvars):
        tfvars_content = '\n'.join([f'{key} = "{value}"' if isinstance(value, str) else f'{key} = {value}' for key, value in tfvars.items()])
        tfvars_file_path = os.path.join('/root/TerraformCode', terraform_script_path, 'terraform.tfvars')
        with open(tfvars_file_path, 'w') as tfvars_file:
            tfvars_file.write(tfvars_content)

    @staticmethod
    def run_terraform_command(terraform_script_path, vmid):
        state_file = f"States/terraform_{vmid}.tfstate"
        try:
            command = f'cd /root/TerraformCode/{terraform_script_path} && terraform init && terraform plan && terraform apply -state={state_file} -auto-approve'
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command, output=output, stderr=error)

            return output.decode('utf-8'), None
        except subprocess.CalledProcessError as e:
            return e.output.decode('utf-8'), e.stderr.decode('utf-8')

    @staticmethod
    def unlock_terraform_state(terraform_script_path, lock_id):
        try:
            command = f'cd /root/TerraformCode/{terraform_script_path} && terraform force-unlock -force {lock_id}'
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command, output=output, stderr=error)

            return output.decode('utf-8'), None
        except subprocess.CalledProcessError as e:
            return e.output.decode('utf-8'), e.stderr.decode('utf-8')

    @staticmethod
    def handle_terraform_command(terraform_script_path, vmid):
        output, error = TerraformService.run_terraform_command(terraform_script_path, vmid)
        
        if error and 'Error acquiring the state lock' in error:
            lock_id_match = re.search(r'ID: +([a-f0-9-]+)', error)
            if lock_id_match:
                lock_id = lock_id_match.group(1)
                unlock_output, unlock_error = TerraformService.unlock_terraform_state(terraform_script_path, lock_id)
                if unlock_error:
                    return None, f"Failed to unlock state: {unlock_error}"

                output, error = TerraformService.run_terraform_command(terraform_script_path, vmid)

        return output, error
