from application.interfaces.presenters.ldaps_presenter import LdapsPresenter


class LdapsController:

    def __init__(self, server_address, path_to_cert_file, port=636):
        self.presenter = LdapsPresenter(
            server_address=server_address,
            path_to_cert_file=path_to_cert_file,
            port=port
        )
        self.presenter.set_server()


    @staticmethod
    def set_request_user(CN, DC):
        """
        :return: user ldaps request
        """
        if isinstance(CN):
            cn_str = "CN="
            delimiter = ",CN="
            cn_str += delimiter.join(map(str, CN))
        else:
            cn_str = "CN="

        if isinstance(DC):
            dc_str = "DC="
            delimiter = ",DC="
            dc_str += delimiter.join(map(str, DC))
        else:
            dc_str = "DC="

        return cn_str + dc_str

    def connect(self, CN, DC, password):
        """
        Connects to the LDAP server
        """
        return self.presenter.connect(
            user=self.set_request_user(CN, DC),
            password=password
        )

