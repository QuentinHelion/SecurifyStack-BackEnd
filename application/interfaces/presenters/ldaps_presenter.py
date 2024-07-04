"""
Presenter for LDAP Server
"""

import ssl
from ldap3 import Server, Connection, ALL, Tls
from ldap3.core.exceptions import LDAPSocketOpenError, LDAPBindError, LDAPException


class LdapsPresenter:
    """
    LdapsPresenter provides access to the LDAP server
    """

    def __init__(self, server_address, path_to_cert_file, port=636):
        self.port = port
        self.server_address = server_address
        self.cert_file = path_to_cert_file
        self.server = None

    def set_server(self, validate=ssl.CERT_REQUIRED, version=ssl.PROTOCOL_TLSv1_2):
        """
        Sets up the LDAP server
        """
        tls_configuration = Tls(
            validate=validate,
            version=version,
            ca_certs_file=self.cert_file,
        )
        self.server = Server(
            self.server_address,
            port=self.port,
            use_ssl=True,
            tls=tls_configuration,
            get_info=ALL
        )

    def connect(self, user, password):
        """
        Connects to the LDAP server
        :return: Bool depend on if user exists or not
        """

        result = False
        try:
            conn = Connection(self.server, user=user, password=password, auto_bind=True)
            if conn.bind():
                result = True
            conn.unbind()

        except LDAPBindError as e:
            print(f"LDAP bind error: {e}")
        except LDAPSocketOpenError as e:
            print(f"LDAP socket open error: {e}")
        except LDAPException as e:
            print(f"LDAP exception: {e}")

        return result
