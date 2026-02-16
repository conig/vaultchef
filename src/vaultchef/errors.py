class VaultchefError(Exception):
    pass


class ConfigError(VaultchefError):
    pass


class MissingFileError(VaultchefError):
    pass


class ValidationError(VaultchefError):
    pass


class ShoppingParseError(ValidationError):
    pass


class PandocError(VaultchefError):
    pass


class WatchError(VaultchefError):
    pass
