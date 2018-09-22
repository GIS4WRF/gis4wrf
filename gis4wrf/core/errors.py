class UserError(Exception):
    ''' Any error that can be dealt with by the user and
        is not a bug in the software. '''
    pass

class UnsupportedError(UserError):
    ''' Any feature not currently supported by the plugin but
        which can in theory be implemented. '''
    pass

class DistributionError(UserError):
    def __init__(self, name: str, msg: str) -> None:
        super().__init__(msg)
        self.dist_name = name

class WRFDistributionError(DistributionError):
    def __init__(self, msg: str) -> None:
        super().__init__('WRF', msg)

class WPSDistributionError(DistributionError):
    def __init__(self, msg: str) -> None:
        super().__init__('WPS', msg)
