from .LiveAgent import LiveAgent


def create_instance(c_instance):
    return LiveAgent(c_instance)
