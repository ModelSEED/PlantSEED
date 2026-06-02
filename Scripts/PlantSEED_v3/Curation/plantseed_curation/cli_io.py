"""Tiny Console abstraction for the interactive CLI.

Replaces the original `builtins.input` monkey-patch + `sys.exit()` mid-flow
in Curation_Tool.py (bug fix #6). The default behaviour is identical — type
"!!" to exit cleanly — but the input source and the exit action are both
injectable, so tests can drive the CLI with a list of canned answers and
intercept the exit instead of actually calling sys.exit.
"""

import sys

from .constants import EXIT_SHORTCUT


class ExitRequested(Exception):
    """Raised by Console.prompt when the curator types EXIT_SHORTCUT.
    Tests can catch this; the default exit_action raises it after printing."""


def _default_exit():
    print("\nExiting script.")
    raise ExitRequested()


class Console:
    def __init__(self, input_fn=None, output_fn=None, exit_action=None):
        # Default to real I/O when used as a CLI; tests pass an iterator's
        # __next__ as input_fn and a list-append as output_fn.
        self._input = input_fn if input_fn is not None else input
        self._print = output_fn if output_fn is not None else print
        self._exit = exit_action if exit_action is not None else _default_exit

    def print(self, *args, **kwargs):
        # `print()` with no args produces an empty line. Forward that as ""
        # so a list.append output_fn (used in tests) still gets a single arg.
        if not args:
            self._print("")
        else:
            self._print(*args, **kwargs)

    def prompt(self, message=""):
        val = self._input(message)
        if val is None:
            self._exit()
            return ""
        if val.strip() == EXIT_SHORTCUT:
            self._exit()
            return ""
        return val

    def prompt_required(self, message):
        while True:
            val = self.prompt(message).strip()
            if val:
                return val

    def numbered_select(self, message, options):
        self._print()
        for i, opt in enumerate(options, 1):
            self._print(f"  {i}. {opt}")
        while True:
            raw = self.prompt(f"{message} ").strip()
            try:
                idx = int(raw) - 1
            except ValueError:
                self._print(f"Enter a number between 1 and {len(options)}.")
                continue
            if 0 <= idx < len(options):
                return options[idx]
            self._print(f"Enter a number between 1 and {len(options)}.")


def install_global_exit_shortcut():
    """Back-compat helper: wrap builtins.input so the !! shortcut works for
    any stray input() call that hasn't been routed through Console yet.

    Tests do not call this — they construct a Console with a scripted
    input_fn instead.
    """
    import builtins
    original = builtins.input

    def _wrapped(prompt=""):
        val = original(prompt)
        if val.strip() == EXIT_SHORTCUT:
            print("\nExiting script.")
            sys.exit(0)
        return val

    builtins.input = _wrapped
