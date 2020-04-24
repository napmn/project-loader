import argparse
import os

import inquirer
from blessings import Terminal
from inquirer.themes import Theme
from prompt_toolkit import prompt
from prompt_toolkit.completion import (
    FuzzyWordCompleter, WordCompleter, FuzzyCompleter
)
from prompt_toolkit.output.color_depth import ColorDepth
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator


# custom commands to be executed
CUSTOM_COMMANDS = [
    # 'sudo systemctl stop postgresql'
    'pip freeze'
]


# add more managers for different languages
DEPENDENCY_MANAGERS = [
    {
        'name': 'poetry',
        'file': 'pyproject.toml',
        'command': 'poetry shell'
    },
    {
        'name': 'virtualenviroment',
        'file': 'venv',
        'command': 'source venv/bin/activate'
    },
    {
        'name': 'pipenv',
        'file': 'Pipfile',
        'command': 'pipenv shell'
    },
]


DEFAULT_PROJECTS_PATHS = [
    # '/home/lukas/Documents/fun',
    # '/home/lukas/Documents/upwork',
    '/home/lukas/Documents',
]


EXCLUDE_DIRS = {
    'venv', 'node_modules', 'lib', 'obj', 'bin', 'out', 'outputs', 'inputs',
    'tmp', 'src', 'source', 'img', 'images', 'static', 'templates', 'models',
    'data', 'opt', 'etc', 'test', 'tests', 'assets', 'results'
}


EXCLUDE_PREFIXES = (
    '.', '__', 'config', 'build', 'doc', 'media'
)


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
    parser = argparse.ArgumentParser()

    project_group = parser.add_mutually_exclusive_group(required=True)
    project_group.add_argument(
        '--projects-path', type=str,
        help='Path to the directory containing projects.'
    )
    project_group.add_argument(
        '--find-project', action='store_true',
        help=(
            'If present, try to find project by name in paths predefined'
            ' in the script'
        )
    )
    parser.add_argument(
        '--editor', type=str, required=False, default='code',
        help=(
            'Editor command to be used for opening editor.'
            ' Default is code for vscode.'
        )
    )
    parser.add_argument(
        '--activate-env', action='store_true', required=False, default=False,
        help=(
            'If this argument is present script will activate enviroment'
            ' if found in the project directory'
        )
    )
    return parser.parse_args()


def get_projects_choices(projects_dir):
    """
    Lists directories in projects_dir. Only used when projects-path is
    present in script arguments.
    """
    return [
        project for project in os.listdir(projects_dir) if os.path.isdir(
            os.path.join(projects_dir, project)
        )
    ]


def get_default_shell():
    """ Returns name of default shell of the system. """
    shell_path = os.environ.get('SHELL', '/bin/bash')
    _, _, shell = shell_path.rpartition('/')
    return shell


def open_project_terminal(project_path, shell, editor_command):
    no_color = '\\033[0m'
    light_cyan = '\\033[1;36m'
    light_green = '\\033[1;32m'

    commands_to_execute = CUSTOM_COMMANDS + [f'{editor_command} .']
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


def check_dependency_manager(project_path, activate_env):
    global CUSTOM_COMMANDS
    dir_content = os.listdir(project_path)
    for manager_info in DEPENDENCY_MANAGERS:
        if manager_info['file'] in dir_content:
            manager = manager_info
            break
    else:
        return None

    if activate_env:
        CUSTOM_COMMANDS = [manager['command']] + CUSTOM_COMMANDS
    else:
        questions = [
            inquirer.List(
                'manager',
                message=f'Do you want to activate {manager["name"]}?',
                choices=('Yes please', 'Hell no'),
            ),
        ]

        answers = inquirer.prompt(questions, theme=CustomTheme())
        if answers is None:
            exit(0)
        if answers['manager'] == 'Yes please':
            CUSTOM_COMMANDS = [manager['command']] + CUSTOM_COMMANDS


def ask_for_project_from_choices(projects_path):
    projects = get_projects_choices(projects_path)
    questions = [
        inquirer.List(
            'project',
            message='What project do you want to open?',
            choices=projects,
        ),
    ]
    answers = inquirer.prompt(questions, theme=CustomTheme())
    if answers is None:
        exit(0)

    return os.path.join(projects_path, answers['project'])


def find_project_by_name():
    def get_possible_project_directories():
        possible_directories = []
        for projects_path in DEFAULT_PROJECTS_PATHS:
            for root, dirs, files in os.walk(projects_path):
                dirs[:] = [
                    d for d in dirs if d not in EXCLUDE_DIRS
                        and d.startswith(EXCLUDE_PREFIXES) is False
                ]
                possible_directories.append(root)
        return possible_directories

    possible_directories = get_possible_project_directories()
    parts = [os.path.split(d) for d in possible_directories]
    projects_paths_dict = {project: path for path, project in parts}

    completer = FuzzyWordCompleter(
        projects_paths_dict.keys(), meta_dict=projects_paths_dict
    )
    validator = Validator.from_callable(
        lambda text: ' ' not in text,
        error_message=(
            'Search must not contain spaces. Dont bother with them.'
        ),
    )

    message = [
        ('class:brackets', '['),
        ('class:question_mark', '?'),
        ('class:brackets', ']'),
        ('', ' Select project by name: ')
    ]

    project = prompt(
        message, completer=completer, validator=validator,
        validate_while_typing=True, style=CustomTheme.get_prompt_style(),
        color_depth=ColorDepth.ANSI_COLORS_ONLY
    )
    if project is None:
        exit(1)

    return os.path.join(projects_paths_dict[project], project)


def main():
    args = parse_args()
    if args.projects_path:
        project_path = ask_for_project_from_choices(args.projects_path)
    else:
        # find_project is present in args
        project_path = find_project_by_name()

    shell = get_default_shell()

    dependency_manager = check_dependency_manager(
        project_path, args.activate_env
    )

    open_project_terminal(project_path, shell, args.editor)


if __name__ == '__main__':
    main()
