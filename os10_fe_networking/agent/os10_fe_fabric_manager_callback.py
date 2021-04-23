import abc


class OS10FEFabricManagerCallback(object, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def pre_ensure_configuration(self):
        """

        :return:
        """

    @abc.abstractmethod
    def post_ensure_configuration(self):
        """

        :return:
        """

    @abc.abstractmethod
    def pre_detach_port_from_vlan(self):
        """

        :return:
        """

    @abc.abstractmethod
    def post_detach_port_from_vlan(self):
        """

        :return:
        """

    @abc.abstractmethod
    def pre_delete_vlan(self):
        """

        :return:
        """

    @abc.abstractmethod
    def post_delete_vlan(self):
        """

        :return:
        """


class WriteMemoryCallback(OS10FEFabricManagerCallback):

    def __init__(self, client):
        self.client = client

    def pre_ensure_configuration(self):
        pass

    def post_ensure_configuration(self):
        """

        :return:
        """
        self.client.write_memory()

    def pre_detach_port_from_vlan(self):
        pass

    def post_detach_port_from_vlan(self):
        """

        :return:
        """
        self.client.write_memory()

    def pre_delete_vlan(self):
        pass

    def post_delete_vlan(self):
        """

        :return:
        """
        self.client.write_memory()