import os
import subprocess
import re


class TerraformService:
    @staticmethod
    def write_tfvars_file(terraform_script_path, tfvars):
        tfvars_content = []
        for key, value in tfvars.items():
            if isinstance(value, list):
                formatted_value = '[' + \
                    ', '.join(f'"{item}"' for item in value) + ']'
                tfvars_content.append(f'{key} = {formatted_value}')
            elif isinstance(value, str):
                tfvars_content.append(f'{key} = "{value}"')
            else:
                tfvars_content.append(f'{key} = {value}')

        tfvars_content = '\n'.join(tfvars_content)
        tfvars_file_path = os.path.join(
            '/root/SecurifyStack/TerraformCode', terraform_script_path, 'terraform.tfvars')
        with open(tfvars_file_path, 'w') as tfvars_file:
            tfvars_file.write(tfvars_content)

    @staticmethod
    def generate_state_file_name(case, request_json):
        if case == 'Deploy-1':
            vmid = request_json.get('vm_id')
            return f"terraform_{vmid}.tfstate"
        elif case == 'Deploy-any-count':
            start_vmid = request_json.get('start_vmid')
            vm_count = request_json.get('vm_count')
            return f"terraform_{start_vmid}_{vm_count}.tfstate"
        elif case == 'Deploy-any-names':
            start_vmid = request_json.get('start_vmid')
            vm_count = len(request_json.get('hostnames'))
            return f"terraform_{start_vmid}_{vm_count}.tfstate"
        else:
            raise ValueError("Invalid case for state file generation")

    @staticmethod
    def run_terraform_command(terraform_script_path, state_file_name):
        state_file = f"States/{state_file_name}"
        try:
            command = f'cd /root/SecurifyStack/TerraformCode/{terraform_script_path} && terraform init && terraform plan && terraform apply -state={state_file} -auto-approve'
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, command, output=output, stderr=error)

            return output.decode('utf-8'), None
        except subprocess.CalledProcessError as e:
            return e.output.decode('utf-8'), e.stderr.decode('utf-8')

    @staticmethod
    def unlock_terraform_state(terraform_script_path, lock_id):
        try:
            command = f'cd /root/SecurifyStack/TerraformCode/{terraform_script_path} && terraform force-unlock -force {lock_id}'
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, command, output=output, stderr=error)

            return output.decode('utf-8'), None
        except subprocess.CalledProcessError as e:
            return e.output.decode('utf-8'), e.stderr.decode('utf-8')

    @staticmethod
    def handle_terraform_command(terraform_script_path, state_file_name):
        output, error = TerraformService.run_terraform_command(
            terraform_script_path, state_file_name)

        if error and 'Error acquiring the state lock' in error:
            lock_id_match = re.search(r'ID: +([a-f0-9-]+)', error)
            if lock_id_match:
                lock_id = lock_id_match.group(1)
                unlock_output, unlock_error = TerraformService.unlock_terraform_state(
                    terraform_script_path, lock_id)
                if unlock_error:
                    return None, f"Failed to unlock state: {unlock_error}"

                output, error = TerraformService.run_terraform_command(
                    terraform_script_path, state_file_name)

        return output, error
