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

    def connect(self, user, password, conn=None):
        """
        Connects to the LDAP server
        :return: Bool depend on if user exists or not
        """
        try:
            if conn is None:
                conn = Connection(self.server, user=user, password=password, auto_bind=True)
            else:
                conn.user = user
                conn.password = password

            if conn.bind():
                return True
        except (LDAPBindError, LDAPSocketOpenError, LDAPException) as e:
            print(f"LDAP error during bind: {e}")

        return False

    def test_connection_and_search(self, search_base):
        """
        Performs an anonymous bind and then a search to validate Base DN.
        """
        try:
            # Establish connection with anonymous bind
            conn = Connection(self.server, auto_bind=True)
            if not conn.bound:
                return False, "Anonymous bind failed."

            # Perform a base-level search to validate the search_base
            if conn.search(search_base, '(objectClass=*)', attributes=['objectClass'], size_limit=1):
                conn.unbind()
                return True, "LDAPS connection and Base DN validation successful."
            else:
                conn.unbind()
                return False, f"Base DN '{search_base}' not found or not accessible."

        except (LDAPBindError, LDAPSocketOpenError, LDAPException) as e:
            return False, f"LDAP error: {e}"
