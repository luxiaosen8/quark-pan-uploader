from __future__ import annotations

from inspect import Parameter, signature
from typing import Any


def call_with_supported_kwargs(func, /, *args, **kwargs):
    try:
        sig = signature(func)
    except (TypeError, ValueError):
        return func(*args, **kwargs)
    parameters = sig.parameters.values()
    if any(param.kind is Parameter.VAR_KEYWORD for param in parameters):
        return func(*args, **kwargs)
    supported = {name: value for name, value in kwargs.items() if name in sig.parameters}
    return func(*args, **supported)


def call_with_supported_positional_args(func, /, *args: Any):
    try:
        sig = signature(func)
    except (TypeError, ValueError):
        return func(*args)
    parameters = list(sig.parameters.values())
    if any(param.kind is Parameter.VAR_POSITIONAL for param in parameters):
        return func(*args)
    positional_cap = sum(
        1
        for param in parameters
        if param.kind in {Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD}
    )
    return func(*args[:positional_cap])
