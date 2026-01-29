class VaultchefError(Exception):
    pass


class ConfigError(VaultchefError):
    pass


class MissingFileError(VaultchefError):
    pass


class ValidationError(VaultchefError):
    pass


class PandocError(VaultchefError):
    pass


class WatchError(VaultchefError):
    pass
