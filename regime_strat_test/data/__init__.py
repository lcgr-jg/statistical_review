"""Data loaders. Bloomberg-dependent helpers are imported lazily."""

__all__ = ["load_curves", "load_inventory", "load_atm_iv"]


def __getattr__(name: str):
    if name == "load_curves":
        from .curves import load_curves
        return load_curves
    if name == "load_inventory":
        from .inventory import load_inventory
        return load_inventory
    if name == "load_atm_iv":
        from .vols import load_atm_iv
        return load_atm_iv
    raise AttributeError(name)
