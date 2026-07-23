"""Validated terminal summary inputs and deterministic INDEX folding."""

from __future__ import annotations

from pathlib import Path


SUMMARY_MAX_BYTES = 64 * 1024


class SummaryInputError(ValueError):
    def __init__(self, code: str, action: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.action = action
        self.message = message


def read_summary(*, inline: str | None, file_path: str | None) -> str:
    if (inline is None) == (file_path is None):
        raise SummaryInputError(
            "ERROR_SUMMARY_INVALID",
            "fix_command_arguments",
            "Exactly one of --summary or --summary-file is required",
        )
    if inline is not None:
        if "\r" in inline or "\n" in inline:
            raise _invalid("--summary must be a single line")
        data = inline.encode("utf-8")
        _validate_summary(inline, data)
        return inline

    assert file_path is not None
    if file_path == "-":
        raise SummaryInputError(
            "ERROR_SUMMARY_FILE_READ",
            "inspect_summary_file",
            "stdin is unsupported for --summary-file",
        )
    path = Path(file_path)
    if not path.is_file():
        raise SummaryInputError(
            "ERROR_SUMMARY_FILE_READ",
            "inspect_summary_file",
            f"Summary file is unavailable: {path}",
        )
    try:
        data = path.read_bytes()
    except OSError as error:
        raise SummaryInputError(
            "ERROR_SUMMARY_FILE_READ",
            "inspect_summary_file",
            f"Summary file could not be read: {path}: {error}",
        ) from error
    if len(data) > SUMMARY_MAX_BYTES:
        raise SummaryInputError(
            "ERROR_SUMMARY_TOO_LARGE",
            "inspect_summary_file",
            f"Summary exceeds {SUMMARY_MAX_BYTES} UTF-8 bytes",
        )
    try:
        value = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise SummaryInputError(
            "ERROR_SUMMARY_FILE_ENCODING",
            "inspect_summary_file",
            "Summary file must be valid UTF-8",
        ) from error
    _validate_summary(value, data)
    return value


def fold_summary_for_index(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", " ⏎ ")


def _validate_summary(value: str, data: bytes) -> None:
    if len(data) > SUMMARY_MAX_BYTES:
        raise SummaryInputError(
            "ERROR_SUMMARY_TOO_LARGE",
            "fix_command_arguments",
            f"Summary exceeds {SUMMARY_MAX_BYTES} UTF-8 bytes",
        )
    if not value.strip():
        raise _invalid("Summary must not be empty or whitespace-only")
    if "\x00" in value:
        raise _invalid("Summary must not contain NUL")


def _invalid(message: str) -> SummaryInputError:
    return SummaryInputError("ERROR_SUMMARY_INVALID", "fix_command_arguments", message)

