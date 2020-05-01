import argparse
import json
import os

import inquirer
from blessings import Terminal
from inquirer.themes import Theme
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter
from prompt_toolkit.output.color_depth import ColorDepth
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator


class CustomTheme(Theme):
    """
    Custom theme for prompts. Inherits from Theme and in init sets
    colors for inquirer prompt and static method get_prompt_style()
    returns style for prompt_toolkit prompt.
    """
    term = Terminal()
    dark_cyan = '#0AA'
    bright_cyan = '#5FF'
    bright_blue = '#55F'
    bright_yellow = '#FF5'
    gray = 'gray'

    def __init__(self):
        super().__init__()
        self.Question.mark_color = self.term.bold_bright_yellow
        self.Question.brackets_color = self.term.bold_bright_blue
        self.List.selection_color = self.term.bold_bright_cyan
        self.List.selection_cursor = '❯'
        self.List.unselected_color = self.term.cyan

    @staticmethod
    def get_prompt_style():
        return Style.from_dict({
            'brackets': f'{CustomTheme.bright_blue} bold',
            'question_mark': f'{CustomTheme.bright_yellow} bold',
            # Completions menu
            'completion-menu.completion': 'bg:default',
            'completion-menu.completion.current': 'bg:default',
            # Meta
            'completion-menu.meta.completion': 'bg:#999999 #000000',
            'completion-menu.meta.completion.current':
                f'fg:{CustomTheme.bright_cyan} bg:default bold',
            # Fuzzy
            'completion-menu.completion fuzzymatch.outside':
                f'fg:{CustomTheme.dark_cyan}',
            'completion-menu.completion fuzzymatch.inside':
                f'fg:{CustomTheme.dark_cyan} nobold',
            'completion-menu.completion fuzzymatch.inside.character':
                'nounderline',
            'completion-menu.completion.current fuzzymatch.outside':
                f'fg:{CustomTheme.bright_cyan} bold',
            'completion-menu.completion.current fuzzymatch.inside': 'bold'
        })


def parse_args():
    """
    Parses script arguments.
    Flow of the script (project selection / project search)
    depends on the provided argument.
    """
    parser = argparse.ArgumentParser()

    project_group = parser.add_mutually_exclusive_group(required=True)
    project_group.add_argument(
        '--project-config', type=str, help='Name of the project config to use.'
    )
    project_group.add_argument(
        '--find-project', action='store_true',
        help=(
            'If present, try to find project by name in paths predefined'
            ' in the global config file.'
        )
    )
    return parser.parse_args()


def get_subproject_choices(config):
    """
    Lists directories in directory specified by project_path in config.
    Only used when project config is selected in script arguments.

    Parameters
    ----------
    config : dict
        Contains settings.

    Returns
    -------
    list of strings
        Paths to all subprojects
    """
    return filter_directories([
        project for project in os.listdir(config['project_path'])
            if os.path.isdir(os.path.join(config['project_path'], project))
    ], config)


def get_default_shell():
    """ Returns name of default shell of the system. """
    shell_path = os.environ.get('SHELL', '/bin/bash')
    _, _, shell = shell_path.rpartition('/')
    return shell


def open_project_terminal(project_path, shell, config):
    """
    Opens new terminal in project_path with given shell
    and runs custom commands as well as opens editor specified in config.

    Parameters
    ----------
    project_path : str
        Path of the project that should be opened.
    shell : str
        Name of the shell to open in terminal.
    config: dict
        Contains settings.
    """
    no_color = '\\033[0m'
    light_cyan = '\\033[1;36m'
    light_green = '\\033[1;32m'

    commands_to_execute = config['custom_commands'] + [f'{config["editor"]} .']
    commands_plus_echo = [
        f'echo -e \\"{light_cyan}Executing command:{no_color}\\"'\
        f' \\"{light_green}{command}{no_color}\\";{command};'
            for command in commands_to_execute
    ]
    os.system(
        f"""
        gnome-terminal -e '{shell} -c "
        cd {project_path};
        {''.join(commands_plus_echo)}
        {shell}"'
        """
    )


def check_dependency_manager(project_path, config):
    """
    Checks if any of the dependency managers is present in the project.
    If setting for dependency manager activation for commands
    is set to True prepends activation of env to commands
    or activate env without spawning new shell (if possible).
    If this setting is set to False and setting for asking
    to activate env is True asks user if he wants to run
    commands in activated env.

    Parameters
    ----------
    project_path: str
        Path to project.
    config: dict
        Contains settings.
    """
    dir_content = os.listdir(project_path)
    for manager_info in config['dependency_managers']:
        if manager_info['file'] in dir_content:
            manager = manager_info
            break
    else:
        return None

    if config.get('automatically_run_commands_in_env', False):
        config['custom_commands'] = add_env_to_custom_commands(
            manager, config['custom_commands']
        )
    elif config.get('ask_for_env_activation', False):
        questions = [
            inquirer.List(
                'manager',
                message=(
                    f'Do you want to activate / run custom commands'
                    f' in {manager["name"]}?'
                ),
                choices=('Yes please', 'Nope'),
            )
        ]

        answers = inquirer.prompt(questions, theme=CustomTheme())
        if answers is None:
            exit(0)
        if answers['manager'] == 'Yes please':
            config['custom_commands'] = add_env_to_custom_commands(
            manager, config['custom_commands']
        )


def add_env_to_custom_commands(manager, custom_commands):
    """
    Based on dependency manager manager either prepend command
    of the manager before each of the custom command or add
    its activation before executing custom commands.
    """
    if manager['activation']:
        # manager can be activated like for example virtualenv
        return [manager['activation']] + custom_commands
    else:
        # manager cant be activated without spawning new shell
        return [
            manager['command'] + ' ' + command for command in custom_commands
        ]


def ask_for_subproject_from_choices(choices):
    """ Returns project selected by user from choices """
    questions = [
        inquirer.List(
            'project',
            message='What project do you want to open?',
            choices=choices,
        ),
    ]
    answers = inquirer.prompt(questions, theme=CustomTheme())
    if answers is None:
        exit(0)
    return answers['project']


def select_project(config):
    """
    Based on config asks user to select subproject from project
    or sets project to be opened automatically.

    Parameters
    ----------
    config : dict
        Contains settings.

    Returns
    -------
    str
        Path to project to be opened.
    """
    if config['multiple_subprojects']:
        projects = get_subproject_choices(config)
        selected_subproject = ask_for_subproject_from_choices(projects)
    else:
        selected_subproject = ''

    return os.path.join(config['project_path'], selected_subproject)


def filter_directories(directories, config):
    """
    Filters out directories that should be excluded or starts with
    prefix that should be ignored.
    """
    return [
        d for d in directories if d not in config['exclude_dirs']
            and d.startswith(tuple(config['exclude_prefixes'])) is False
    ]


def find_project_by_name(config):
    """
    Implements search prompt to find project by name entered
    by user. Uses fuzzy logic to match search with project names.

    Parameters
    ----------
    config : dict
        Contains settings.

    Returns
    -------
    str
        Path to project selected by user based on his search.
    """
    def get_possible_project_directories(config):
        possible_directories = []
        for projects_path in config['default_projects_paths']:
            for root, dirs, files in os.walk(projects_path):
                # modifying dirs directly to prune search tree
                dirs[:] = filter_directories(dirs, config)
                possible_directories.append(root)
        return possible_directories

    possible_directories = get_possible_project_directories(config)
    parts = [os.path.split(d) for d in possible_directories]
    projects_paths_dict = {project: path for path, project in parts}

    completer = FuzzyWordCompleter(
        projects_paths_dict.keys(), meta_dict=projects_paths_dict
    )
    validator = Validator.from_callable(
        lambda text: ' ' not in text,
        error_message=('Spaces in project name? Really?'),
    )

    message = [
        ('class:brackets', '['),
        ('class:question_mark', '?'),
        ('class:brackets', ']'),
        ('', ' Select project by name: ')
    ]
    try:
        project = prompt(
            message, completer=completer, validator=validator,
            validate_while_typing=True, style=CustomTheme.get_prompt_style(),
            color_depth=ColorDepth.ANSI_COLORS_ONLY
        )
    except KeyboardInterrupt:
        print('\nCancelled by user\n')
        exit(0)

    return os.path.join(projects_paths_dict[project], project)


def load_configs(project_config):
    """
    Loads global and user project config. Project config
    can rewrite attributes set in global config.

    Parameters
    ----------
    project_config : str or None
        Name of the user config.

    Returns
    -------
    dict
        Dictionary containing configuration.
    """
    with open('configs/global_config.json', 'r') as cf:
        config = json.load(cf)
    if project_config:
        project_config = project_config if project_config[:-4] == '.json' \
            else f'{project_config}.json'
        with open(os.path.join('configs/user_configs', project_config)) as cf:
            config.update(json.load(cf))
    return config


def main():
    args = parse_args()
    config = load_configs(args.project_config)
    if args.project_config:
        project_path = select_project(config)
    else:
        # find_project is present in args
        project_path = find_project_by_name(config)

    shell = get_default_shell()
    check_dependency_manager(project_path, config)
    open_project_terminal(project_path, shell, config)


if __name__ == '__main__':
    main()
