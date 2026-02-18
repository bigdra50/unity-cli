"""Shell completion command."""

from __future__ import annotations

from typing import Annotated

import typer

from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.output import get_err_console, is_no_color

_COMPLETION_SCRIPTS = {
    "zsh": """#compdef u unity unity-cli

_unity_cli() {
  eval $(env _TYPER_COMPLETE_ARGS="${words[1,$CURRENT]}" _U_COMPLETE=complete_zsh u)
}

_unity_cli "$@"
""",
    "bash": """_unity_cli() {
  local IFS=$'\\n'
  COMPREPLY=($(env _TYPER_COMPLETE_ARGS="${COMP_WORDS[*]}" _U_COMPLETE=complete_bash u))
  return 0
}

complete -o default -F _unity_cli u unity unity-cli
""",
    "fish": """complete -c u -f -a "(env _TYPER_COMPLETE_ARGS=(commandline -cp) _U_COMPLETE=complete_fish u)"
complete -c unity -f -a "(env _TYPER_COMPLETE_ARGS=(commandline -cp) _U_COMPLETE=complete_fish unity)"
complete -c unity-cli -f -a "(env _TYPER_COMPLETE_ARGS=(commandline -cp) _U_COMPLETE=complete_fish unity-cli)"
""",
}


def register(app: typer.Typer) -> None:
    @app.command("completion")
    def completion(
        shell: Annotated[
            str | None,
            typer.Option("--shell", "-s", help="Shell type: zsh, bash, fish"),
        ] = None,
    ) -> None:
        """Generate shell completion script.

        Examples:
            u completion -s zsh > ~/.zsh/completions/_unity-cli
            u completion -s bash >> ~/.bashrc
            u completion -s fish > ~/.config/fish/completions/unity-cli.fish
        """
        import os

        # Auto-detect shell if not specified
        if shell is None:
            shell_env = os.environ.get("SHELL", "")
            if "zsh" in shell_env:
                shell = "zsh"
            elif "bash" in shell_env:
                shell = "bash"
            elif "fish" in shell_env:
                shell = "fish"
            else:
                shell = "zsh"  # Default to zsh

        shell = shell.lower()
        if shell not in _COMPLETION_SCRIPTS:
            import sys

            if is_no_color():
                print(f"Unsupported shell: {shell}", file=sys.stderr)
                print(f"Supported shells: {', '.join(_COMPLETION_SCRIPTS.keys())}", file=sys.stderr)
            else:
                get_err_console().print(f"[red]Unsupported shell: {shell}[/red]")
                get_err_console().print(f"Supported shells: {', '.join(_COMPLETION_SCRIPTS.keys())}")
            raise typer.Exit(ExitCode.USAGE_ERROR)

        # Output script to stdout (no Rich formatting)
        print(_COMPLETION_SCRIPTS[shell], end="")
