"""Tests for the script/query.py CLI (no real backend needed).

The connection plumbing, read counting and field rendering all come from
``modbus_connection.cli_helper`` and are tested there; what is left here is the
wiring — the Ai-logger defaults, inverter selection, and the exit codes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from modbus_connection import ModbusConnectionError, ServerDeviceFailureError
from modbus_connection.mock import MockModbusConnection

from solplanet_modbus import AILOGGER_UNIT_ID, DEFAULT_PORT

from .conftest import INPUT

_SPEC = importlib.util.spec_from_file_location(
    "solplanet_query", Path(__file__).resolve().parents[1] / "script" / "query.py"
)
assert _SPEC and _SPEC.loader
query = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(query)


def _mock_connection() -> MockModbusConnection:
    connection = MockModbusConnection()
    connection.for_unit(AILOGGER_UNIT_ID).input.update(INPUT)
    return connection


def _serve(monkeypatch: pytest.MonkeyPatch, connection: MockModbusConnection) -> None:
    """Hand ``_run`` a mock connection instead of opening a real one."""

    async def connect_from_args(args: object) -> MockModbusConnection:
        return connection

    monkeypatch.setattr(query, "connect_from_args", connect_from_args)


def test_parse_args_uses_the_ai_logger_defaults() -> None:
    args = query._parse_args(["192.168.1.50", "--inverter", "3"])
    assert args.transport == "tcp"
    assert args.target == "192.168.1.50"
    assert args.framer == "socket"  # the logger speaks native Modbus TCP
    assert args.port == DEFAULT_PORT
    assert args.unit == AILOGGER_UNIT_ID
    assert args.inverters == [3]


def test_parse_args_collects_repeated_inverters() -> None:
    args = query._parse_args(
        ["1.2.3.4", "--inverter", "3", "--inverter", "51", "--weather", "--meter"]
    )
    assert args.inverters == [3, 51]
    assert args.weather is True
    assert args.meter is True


def test_parse_args_requires_inverters_or_discovery(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        query._parse_args(["1.2.3.4"])
    assert "--discover" in capsys.readouterr().err


def test_parse_args_rejects_transports_the_logger_cannot_speak() -> None:
    for transport in ("serial", "udp", "tls"):
        with pytest.raises(SystemExit):
            query._parse_args(["1.2.3.4", "--transport", transport])


def test_parse_args_rejects_an_unknown_rs485_port() -> None:
    with pytest.raises(SystemExit):
        query._parse_args(["1.2.3.4", "--discover", "--port-scan", "4"])


async def test_run_prints_every_section(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _serve(monkeypatch, _mock_connection())
    args = query._parse_args(
        ["1.2.3.4", "--inverter", "3", "--inverter", "51", "--weather", "--meter"]
    )
    assert await query._run(args) == 0
    out = capsys.readouterr().out
    assert "Inverter 3 — identity" in out
    assert "Inverter 51 — measurements" in out
    assert "QA10010022920081" in out
    assert "Site totals" in out
    # The station renders both its sensors as sub-blocks.
    assert "Weather station" in out
    assert "sensors[2]" in out
    assert "Energy meter" in out
    assert "Modbus reads)" in out


async def test_run_discovers_inverters(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _serve(monkeypatch, _mock_connection())
    args = query._parse_args(["1.2.3.4", "--discover", "--port-scan", "1"])
    assert await query._run(args) == 0
    out = capsys.readouterr().out
    assert "Scanning for inverters..." in out
    assert "COM1 address 3: ASW8000 QA10010022920081" in out
    assert "Inverter 3 — identity" in out


async def test_discovery_without_a_port_scans_the_whole_map(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _serve(monkeypatch, _mock_connection())
    args = query._parse_args(["1.2.3.4", "--discover"])
    assert await query._run(args) == 0
    out = capsys.readouterr().out
    assert "COM1 address 3:" in out
    assert "COM2 address 51:" in out


async def test_discovery_does_not_duplicate_a_named_inverter(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _serve(monkeypatch, _mock_connection())
    args = query._parse_args(
        ["1.2.3.4", "--inverter", "3", "--discover", "--port-scan", "1"]
    )
    assert await query._run(args) == 0
    assert capsys.readouterr().out.count("Inverter 3 — identity") == 1


async def test_run_reports_an_empty_scan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _serve(monkeypatch, MockModbusConnection())
    args = query._parse_args(["1.2.3.4", "--discover", "--port-scan", "3"])
    assert await query._run(args) == 1
    assert "No inverters found." in capsys.readouterr().err


async def test_run_reports_a_connection_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def refuse(args: object) -> MockModbusConnection:
        raise ModbusConnectionError("no route to host")

    monkeypatch.setattr(query, "connect_from_args", refuse)
    args = query._parse_args(["1.2.3.4", "--inverter", "3"])
    assert await query._run(args) == 1
    assert "Could not connect: no route to host" in capsys.readouterr().err


async def test_run_reports_a_failed_read(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    connection = _mock_connection()
    connection.for_unit(AILOGGER_UNIT_ID).fail_read(
        1000,
        ServerDeviceFailureError(message="slave device failure"),
        register_type="input",
    )
    _serve(monkeypatch, connection)
    args = query._parse_args(["1.2.3.4", "--inverter", "3"])
    assert await query._run(args) == 1
    assert "Error reading logger" in capsys.readouterr().err


def test_main_runs_the_parsed_args(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["query.py", "1.2.3.4", "--inverter", "3"])
    _serve(monkeypatch, _mock_connection())
    assert query.main() == 0
