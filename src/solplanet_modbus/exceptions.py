"""Errors raised by this library.

Modbus transport and protocol errors are not wrapped — they surface as the
``modbus_connection`` exceptions the caller already handles.
"""

from __future__ import annotations


class SolplanetError(Exception):
    """Base class for every error this library raises."""


class UnknownInverterAddressError(SolplanetError, ValueError):
    """An inverter Modbus address outside the logger's documented port ranges."""


class SolplanetValueValidationError(SolplanetError, ValueError):
    """A control value outside the range the protocol allows."""
