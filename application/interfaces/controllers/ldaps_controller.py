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
        if isinstance(CN, list):
            cn_str = "CN="
            delimiter = ",CN="
            cn_str += delimiter.join(map(str, CN))
        else:
            cn_str = f"CN={CN}"


        if isinstance(DC, list):
            dc_str = ",DC="
            delimiter = ",DC="
            dc_str += delimiter.join(map(str, DC))
        else:
            dc_str = f",DC={DC}"

        return cn_str + dc_str

    def connect(self, CN, DC, password):
        """
        Connects to the LDAP server
        """
        print(self.set_request_user(CN, DC))
        return self.presenter.connect(
            user=self.set_request_user(CN, DC),
            password=password
        )

