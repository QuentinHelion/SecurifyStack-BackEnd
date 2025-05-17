"""
Ldaps Controller interface
"""

from application.interfaces.presenters.ldaps_presenter import LdapsPresenter


class LdapsController:
    """
    Ldaps Controller interface
    """

    def __init__(self, server_address, path_to_cert_file, port=636):
        self.presenter = LdapsPresenter(
            server_address=server_address,
            path_to_cert_file=path_to_cert_file,
            port=port
        )
        self.presenter.set_server()

    @staticmethod
    def set_request_user(cn, dc):
        """
        :return: user ldaps request
        """
        if isinstance(cn, list):
            cn_str = "CN="
            delimiter = ",CN="
            cn_str += delimiter.join(map(str, cn))
        else:
            cn_str = f"CN={cn}"

        if isinstance(dc, list):
            dc_str = ",DC="
            delimiter = ",DC="
            dc_str += delimiter.join(map(str, dc))
        else:
            dc_str = f",DC={dc}"

        return cn_str + dc_str

    def connect(self, bind_dn, password):
        """
        Connects to the LDAP server using a full DN
        """
        print(f"Attempting LDAP bind with DN: {bind_dn}")
        return self.presenter.connect(
            user=bind_dn,
            password=password
        )
