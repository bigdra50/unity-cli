"""
Shell Completion Script Generator
=================================

Generate static shell completion scripts for bash, zsh, fish, and powershell.

Usage:
    unity-cli completion bash >> ~/.bashrc
    unity-cli completion zsh >> ~/.zshrc
    unity-cli completion fish > ~/.config/fish/completions/unity-cli.fish
"""

from __future__ import annotations

# Supported shells
SUPPORTED_SHELLS = ("bash", "zsh", "fish", "powershell")

# Static completion scripts

ZSH_SCRIPT = """\
#compdef unity-cli

_unity_cli() {
    local -a commands
    local -a global_opts

    global_opts=(
        '--relay-host[Relay server host]:host:'
        '--relay-port[Relay server port]:port:'
        '--instance[Target Unity instance]:instance:'
        '-i[Target Unity instance]:instance:'
        '--timeout[Timeout in seconds]:timeout:'
        '-t[Timeout in seconds]:timeout:'
        '--json[Output JSON format]'
        '-j[Output JSON format]'
        '--help[Show help]'
    )

    commands=(
        'instances:List connected Unity instances'
        'state:Get editor state'
        'play:Enter play mode'
        'stop:Exit play mode'
        'pause:Toggle pause'
        'refresh:Refresh asset database'
        'open:Open Unity project'
        'completion:Generate shell completion script'
        'console:Console log commands'
        'scene:Scene management commands'
        'tests:Test execution commands'
        'gameobject:GameObject commands'
        'component:Component commands'
        'menu:Menu item commands'
        'asset:Asset commands'
        'config:Configuration commands'
        'project:Project information'
        'editor:Unity Editor management'
        'selection:Editor selection'
        'screenshot:Take screenshot'
    )

    _arguments -C \\
        $global_opts \\
        '1:command:->command' \\
        '*::arg:->args'

    case $state in
        command)
            _describe -t commands 'unity-cli command' commands
            ;;
        args)
            case $words[1] in
                console)
                    local -a console_cmds
                    console_cmds=('get:Get console logs' 'clear:Clear console logs' '--help:Show help')
                    _describe -t commands 'console command' console_cmds
                    ;;
                scene)
                    local -a scene_cmds
                    scene_cmds=('active:Get active scene' 'hierarchy:Get scene hierarchy' 'load:Load scene' 'save:Save scene' '--help:Show help')
                    _describe -t commands 'scene command' scene_cmds
                    ;;
                tests)
                    case $words[2] in
                        run|list)
                            local -a test_modes
                            test_modes=('edit:Run EditMode tests' 'play:Run PlayMode tests' '--help:Show help')
                            _describe -t modes 'test mode' test_modes
                            ;;
                        *)
                            local -a tests_cmds
                            tests_cmds=('run:Run tests' 'list:List tests' 'status:Test status' '--help:Show help')
                            _describe -t commands 'tests command' tests_cmds
                            ;;
                    esac
                    ;;
                gameobject)
                    local -a go_cmds
                    go_cmds=('find:Find GameObjects' 'create:Create GameObject' 'modify:Modify GameObject' 'delete:Delete GameObject' '--help:Show help')
                    _describe -t commands 'gameobject command' go_cmds
                    ;;
                component)
                    local -a comp_cmds
                    comp_cmds=('list:List components' 'inspect:Inspect component' 'add:Add component' 'remove:Remove component' '--help:Show help')
                    _describe -t commands 'component command' comp_cmds
                    ;;
                menu)
                    local -a menu_cmds
                    menu_cmds=('exec:Execute menu item' 'list:List menu items' 'context:Execute ContextMenu' '--help:Show help')
                    _describe -t commands 'menu command' menu_cmds
                    ;;
                asset)
                    local -a asset_cmds
                    asset_cmds=('prefab:Create prefab' 'scriptable-object:Create ScriptableObject' 'info:Asset info' '--help:Show help')
                    _describe -t commands 'asset command' asset_cmds
                    ;;
                config)
                    local -a config_cmds
                    config_cmds=('show:Show config' 'init:Initialize config' '--help:Show help')
                    _describe -t commands 'config command' config_cmds
                    ;;
                project)
                    local -a project_cmds
                    project_cmds=('info:Project info' 'version:Unity version' 'packages:List packages' 'tags:Tags and layers' 'quality:Quality settings' 'assemblies:Assembly definitions' '--help:Show help')
                    _describe -t commands 'project command' project_cmds
                    ;;
                editor)
                    local -a editor_cmds
                    editor_cmds=('list:List editors' 'install:Install editor' '--help:Show help')
                    _describe -t commands 'editor command' editor_cmds
                    ;;
                completion)
                    local -a shells
                    shells=('bash' 'zsh' 'fish' 'powershell')
                    _describe -t shells 'shell' shells
                    ;;
            esac
            ;;
    esac
}

compdef _unity_cli unity-cli
"""

BASH_SCRIPT = """\
_unity_cli() {
    local cur prev words cword
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    words=("${COMP_WORDS[@]}")
    cword=$COMP_CWORD

    commands="instances state play stop pause refresh open completion console scene tests gameobject component menu asset config project editor selection screenshot"

    # Handle third level (e.g., tests run <mode>)
    if [[ $cword -ge 3 ]]; then
        local cmd="${words[1]}"
        local subcmd="${words[2]}"
        case "${cmd}" in
            tests)
                case "${subcmd}" in
                    run|list)
                        COMPREPLY=( $(compgen -W "edit play" -- ${cur}) )
                        return 0
                        ;;
                esac
                ;;
        esac
    fi

    # Handle options starting with -
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "--help --relay-host --relay-port --instance --timeout --json" -- ${cur}) )
        return 0
    fi

    # Handle second level (subcommands)
    case "${prev}" in
        unity-cli)
            COMPREPLY=( $(compgen -W "${commands} --help" -- ${cur}) )
            return 0
            ;;
        console)
            COMPREPLY=( $(compgen -W "get clear --help" -- ${cur}) )
            return 0
            ;;
        scene)
            COMPREPLY=( $(compgen -W "active hierarchy load save --help" -- ${cur}) )
            return 0
            ;;
        tests)
            COMPREPLY=( $(compgen -W "run list status --help" -- ${cur}) )
            return 0
            ;;
        gameobject)
            COMPREPLY=( $(compgen -W "find create modify delete --help" -- ${cur}) )
            return 0
            ;;
        component)
            COMPREPLY=( $(compgen -W "list inspect add remove --help" -- ${cur}) )
            return 0
            ;;
        menu)
            COMPREPLY=( $(compgen -W "exec list context --help" -- ${cur}) )
            return 0
            ;;
        asset)
            COMPREPLY=( $(compgen -W "prefab scriptable-object info --help" -- ${cur}) )
            return 0
            ;;
        config)
            COMPREPLY=( $(compgen -W "show init --help" -- ${cur}) )
            return 0
            ;;
        project)
            COMPREPLY=( $(compgen -W "info version packages tags quality assemblies --help" -- ${cur}) )
            return 0
            ;;
        editor)
            COMPREPLY=( $(compgen -W "list install --help" -- ${cur}) )
            return 0
            ;;
        completion)
            COMPREPLY=( $(compgen -W "bash zsh fish powershell" -- ${cur}) )
            return 0
            ;;
    esac
}

complete -F _unity_cli unity-cli
"""

FISH_SCRIPT = """\
# unity-cli fish completion

set -l commands instances state play stop pause refresh open completion console scene tests gameobject component menu asset config project editor selection screenshot

# Subcommand lists
set -l tests_subcmds run list status
set -l console_subcmds get clear
set -l scene_subcmds active hierarchy load save
set -l gameobject_subcmds find create modify delete
set -l component_subcmds list inspect add remove
set -l menu_subcmds exec list context
set -l asset_subcmds prefab scriptable-object info
set -l config_subcmds show init
set -l project_subcmds info version packages tags quality assemblies
set -l editor_subcmds list install
set -l completion_subcmds bash zsh fish powershell
set -l test_modes edit play

# Helper function: check if we've seen a specific subcommand sequence
function __fish_unity_cli_using_subcommand
    set -l cmd (commandline -opc)
    set -l argc (count $cmd)
    if test $argc -ge 2
        if test "$cmd[2]" = "$argv[1]"
            if test $argc -ge 3; and set -q argv[2]
                test "$cmd[3]" = "$argv[2]"
                return $status
            end
            return 0
        end
    end
    return 1
end

# Helper function: check if we need argument for tests run/list
function __fish_unity_cli_needs_test_mode
    set -l cmd (commandline -opc)
    set -l argc (count $cmd)
    # unity-cli tests run <cursor> -> argc=3
    if test $argc -eq 3
        if test "$cmd[2]" = "tests"
            if test "$cmd[3]" = "run" -o "$cmd[3]" = "list"
                return 0
            end
        end
    end
    return 1
end

complete -c unity-cli -f

# Top-level commands
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a instances -d 'List connected Unity instances'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a state -d 'Get editor state'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a play -d 'Enter play mode'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a stop -d 'Exit play mode'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a pause -d 'Toggle pause'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a refresh -d 'Refresh asset database'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a open -d 'Open Unity project'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a completion -d 'Generate shell completion'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a console -d 'Console commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a scene -d 'Scene commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a tests -d 'Test commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a gameobject -d 'GameObject commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a component -d 'Component commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a menu -d 'Menu commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a asset -d 'Asset commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a config -d 'Config commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a project -d 'Project commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a editor -d 'Editor commands'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a selection -d 'Editor selection'
complete -c unity-cli -n "not __fish_seen_subcommand_from $commands" -a screenshot -d 'Take screenshot'

# tests subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand tests; and not __fish_seen_subcommand_from $tests_subcmds" -a run -d 'Run tests'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand tests; and not __fish_seen_subcommand_from $tests_subcmds" -a list -d 'List tests'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand tests; and not __fish_seen_subcommand_from $tests_subcmds" -a status -d 'Test status'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand tests; and not __fish_seen_subcommand_from $tests_subcmds" -l help -d 'Show help'

# tests run/list mode argument
complete -c unity-cli -n "__fish_unity_cli_needs_test_mode" -a edit -d 'EditMode tests'
complete -c unity-cli -n "__fish_unity_cli_needs_test_mode" -a play -d 'PlayMode tests'
complete -c unity-cli -n "__fish_unity_cli_needs_test_mode" -l help -d 'Show help'

# console subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand console; and not __fish_seen_subcommand_from $console_subcmds" -a get -d 'Get console logs'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand console; and not __fish_seen_subcommand_from $console_subcmds" -a clear -d 'Clear console'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand console; and not __fish_seen_subcommand_from $console_subcmds" -l help -d 'Show help'

# scene subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand scene; and not __fish_seen_subcommand_from $scene_subcmds" -a active -d 'Get active scene'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand scene; and not __fish_seen_subcommand_from $scene_subcmds" -a hierarchy -d 'Scene hierarchy'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand scene; and not __fish_seen_subcommand_from $scene_subcmds" -a load -d 'Load scene'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand scene; and not __fish_seen_subcommand_from $scene_subcmds" -a save -d 'Save scene'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand scene; and not __fish_seen_subcommand_from $scene_subcmds" -l help -d 'Show help'

# gameobject subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand gameobject; and not __fish_seen_subcommand_from $gameobject_subcmds" -a find -d 'Find GameObjects'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand gameobject; and not __fish_seen_subcommand_from $gameobject_subcmds" -a create -d 'Create GameObject'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand gameobject; and not __fish_seen_subcommand_from $gameobject_subcmds" -a modify -d 'Modify GameObject'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand gameobject; and not __fish_seen_subcommand_from $gameobject_subcmds" -a delete -d 'Delete GameObject'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand gameobject; and not __fish_seen_subcommand_from $gameobject_subcmds" -l help -d 'Show help'

# component subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand component; and not __fish_seen_subcommand_from $component_subcmds" -a list -d 'List components'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand component; and not __fish_seen_subcommand_from $component_subcmds" -a inspect -d 'Inspect component'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand component; and not __fish_seen_subcommand_from $component_subcmds" -a add -d 'Add component'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand component; and not __fish_seen_subcommand_from $component_subcmds" -a remove -d 'Remove component'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand component; and not __fish_seen_subcommand_from $component_subcmds" -l help -d 'Show help'

# menu subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand menu; and not __fish_seen_subcommand_from $menu_subcmds" -a exec -d 'Execute menu item'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand menu; and not __fish_seen_subcommand_from $menu_subcmds" -a list -d 'List menu items'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand menu; and not __fish_seen_subcommand_from $menu_subcmds" -a context -d 'Execute ContextMenu'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand menu; and not __fish_seen_subcommand_from $menu_subcmds" -l help -d 'Show help'

# asset subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand asset; and not __fish_seen_subcommand_from $asset_subcmds" -a prefab -d 'Create prefab'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand asset; and not __fish_seen_subcommand_from $asset_subcmds" -a scriptable-object -d 'Create ScriptableObject'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand asset; and not __fish_seen_subcommand_from $asset_subcmds" -a info -d 'Asset info'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand asset; and not __fish_seen_subcommand_from $asset_subcmds" -l help -d 'Show help'

# config subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand config; and not __fish_seen_subcommand_from $config_subcmds" -a show -d 'Show config'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand config; and not __fish_seen_subcommand_from $config_subcmds" -a init -d 'Initialize config'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand config; and not __fish_seen_subcommand_from $config_subcmds" -l help -d 'Show help'

# project subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand project; and not __fish_seen_subcommand_from $project_subcmds" -a info -d 'Project info'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand project; and not __fish_seen_subcommand_from $project_subcmds" -a version -d 'Unity version'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand project; and not __fish_seen_subcommand_from $project_subcmds" -a packages -d 'List packages'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand project; and not __fish_seen_subcommand_from $project_subcmds" -a tags -d 'Tags and layers'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand project; and not __fish_seen_subcommand_from $project_subcmds" -a quality -d 'Quality settings'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand project; and not __fish_seen_subcommand_from $project_subcmds" -a assemblies -d 'Assembly definitions'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand project; and not __fish_seen_subcommand_from $project_subcmds" -l help -d 'Show help'

# editor subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand editor; and not __fish_seen_subcommand_from $editor_subcmds" -a list -d 'List editors'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand editor; and not __fish_seen_subcommand_from $editor_subcmds" -a install -d 'Install editor'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand editor; and not __fish_seen_subcommand_from $editor_subcmds" -l help -d 'Show help'

# completion subcommands
complete -c unity-cli -n "__fish_unity_cli_using_subcommand completion; and not __fish_seen_subcommand_from $completion_subcmds" -a bash -d 'Bash completion'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand completion; and not __fish_seen_subcommand_from $completion_subcmds" -a zsh -d 'Zsh completion'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand completion; and not __fish_seen_subcommand_from $completion_subcmds" -a fish -d 'Fish completion'
complete -c unity-cli -n "__fish_unity_cli_using_subcommand completion; and not __fish_seen_subcommand_from $completion_subcmds" -a powershell -d 'PowerShell completion'

# Global options
complete -c unity-cli -l relay-host -d 'Relay server host'
complete -c unity-cli -l relay-port -d 'Relay server port'
complete -c unity-cli -l instance -s i -d 'Target Unity instance'
complete -c unity-cli -l timeout -s t -d 'Timeout in seconds'
complete -c unity-cli -l json -s j -d 'Output JSON format'
complete -c unity-cli -l help -d 'Show help'
"""

POWERSHELL_SCRIPT = """\
Register-ArgumentCompleter -Native -CommandName unity-cli -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commands = @{
        '' = @('instances', 'state', 'play', 'stop', 'pause', 'refresh', 'open', 'completion', 'console', 'scene', 'tests', 'gameobject', 'component', 'menu', 'asset', 'config', 'project', 'editor', 'selection', 'screenshot', '--help')
        'console' = @('get', 'clear', '--help')
        'scene' = @('active', 'hierarchy', 'load', 'save', '--help')
        'tests' = @('run', 'list', 'status', '--help')
        'tests run' = @('edit', 'play', '--help')
        'tests list' = @('edit', 'play', '--help')
        'gameobject' = @('find', 'create', 'modify', 'delete', '--help')
        'component' = @('list', 'inspect', 'add', 'remove', '--help')
        'menu' = @('exec', 'list', 'context', '--help')
        'asset' = @('prefab', 'scriptable-object', 'info', '--help')
        'config' = @('show', 'init', '--help')
        'project' = @('info', 'version', 'packages', 'tags', 'quality', 'assemblies', '--help')
        'editor' = @('list', 'install', '--help')
        'completion' = @('bash', 'zsh', 'fish', 'powershell')
    }

    $elements = $commandAst.CommandElements
    $subcommand = ''
    if ($elements.Count -gt 1) {
        $subcommand = $elements[1].Extent.Text
    }
    if ($elements.Count -gt 2) {
        $subcommand = $elements[1].Extent.Text + ' ' + $elements[2].Extent.Text
    }

    $completions = $commands[$subcommand]
    if (-not $completions) {
        # Try single level subcommand
        if ($elements.Count -gt 1) {
            $completions = $commands[$elements[1].Extent.Text]
        }
        if (-not $completions) {
            $completions = $commands['']
        }
    }

    $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
"""


def get_completion_script(shell: str, prog_name: str = "unity-cli") -> str:
    """Generate shell completion script.

    Args:
        shell: Target shell (bash, zsh, fish, powershell)
        prog_name: Program name (unused, kept for compatibility)

    Returns:
        Shell completion script as string

    Raises:
        ValueError: If shell is not supported
    """
    shell = shell.lower()

    if shell not in SUPPORTED_SHELLS:
        raise ValueError(f"Unsupported shell: {shell}. Supported: {', '.join(SUPPORTED_SHELLS)}")

    scripts = {
        "bash": BASH_SCRIPT,
        "zsh": ZSH_SCRIPT,
        "fish": FISH_SCRIPT,
        "powershell": POWERSHELL_SCRIPT,
    }

    return scripts[shell]
