"""
Check all type of args for flask request
"""


class Args:
    """
    This class contain all methods
    """

    @staticmethod
    def args_text(args):
        """
        check if given args exist and is
        :return: bool depend on checked args
        """
        # Check if the text is provided
        if not args:
            return False

        # Check if the text is empty
        if not args.strip():  # Using strip() to remove leading and trailing whitespace
            return False

        return True

    @staticmethod
    def args_file(args):
        """
        check if given file exist and if is emtpy
        :return: bool depend on checked file
        """
        # Check if the file path is provided
        if not args:
            return False

        if args is None:
            return False

        if args.filename == '':
            return False

        return True
