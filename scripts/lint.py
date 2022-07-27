#!/usr/bin/env python3
"""This CLI helper help to run:

— Pylint with autodiscovering folders and files, baseline, fail-under —
Mypy with baseline and fail-under score
"""
import argparse
import math
import pathlib

from mypy import api as mypy_api
from pylint import lint as py_lint


IGNORE_FOR_PYLINT_AUTODISCOVER: tuple = (
    "doc",
    "bin",
    "alembic",
)


def run_pylint(
    current_dir: pathlib.Path, minimum_score: float, default_pylint_args: str = ""
) -> None:
    """Pylint linting."""
    print("Pylint starts.")
    print(f"Min score: {minimum_score}")
    print(f"Args: {default_pylint_args}")
    # autodiscover folders and files with python code?
    args_for_pylint: list = []
    if not default_pylint_args:
        for one_item in current_dir.iterdir():
            if (
                one_item.is_dir()
                and one_item.name not in IGNORE_FOR_PYLINT_AUTODISCOVER
            ):
                for sub_item in one_item.iterdir():
                    if sub_item.suffix == ".py":
                        args_for_pylint.append(str(sub_item.resolve()))
            elif one_item.suffix == ".py":
                args_for_pylint.append(one_item.name)
    else:
        args_for_pylint = default_pylint_args.split()
    print(f"Args for pylint {args_for_pylint}")
    # linting itself
    pylint_result = py_lint.Run(args_for_pylint, do_exit=False)
    if not hasattr(pylint_result.linter.stats, "global_note"):
        print(pylint_result)
        print("Probably, there is no pylint stats yet")
        raise SystemExit(1)
    if minimum_score is None:
        print("You chould specify a minimum score for checking the result!")
        raise SystemExit(1)
    if pylint_result.linter.stats.global_note < minimum_score and not math.isclose(
        pylint_result.linter.stats.global_note, minimum_score, rel_tol=0.0005
    ):
        print(f"Pylint failed! Minimum score must be {minimum_score}")
        raise SystemExit(1)


def run_mypy(maximum_score: int, extra_mypy_args: str = "") -> None:
    """Mypy linting."""
    print("Mypy starts.")
    config_file: pathlib.Path = pathlib.Path("./mypy.ini")
    exclude_params: list = ["--exclude", "generic-cicd/"]
    mypy_params: list
    if config_file.exists():
        print("Going through mypy.ini flow")
        # in this case we're using good old mypy.ini flow
        mypy_params = [*exclude_params, "--config-file", "mypy.ini", "."]
        if config_file.is_file():
            mypy_params = [
                *exclude_params,
                "--warn-unused-configs",
                "--ignore-missing-imports",
                "--allow-redefinition",
                ".",
            ]
    else:
        print("Going through pyproject.toml flow")
        # otherwise we're hoping for pyproject.toml
        mypy_params = [*exclude_params, "--config-file", "pyproject.toml", "."]
    if extra_mypy_args:
        mypy_params.extend(extra_mypy_args.split())
    mypy_result: mypy_api.run = mypy_api.run(mypy_params)
    errors_count: int = 0
    if len(mypy_result) > 0:
        error_lines = filter(
            lambda item: not item.startswith("note:"),
            mypy_result[0].strip("\n").split("\n"),
        )
        errors_count = len(error_lines) - 1
        print("Type checking report: ", mypy_result[0])  # stdout
    if mypy_result[1]:
        print("Error report: ", mypy_result[1])  # stderr
    if errors_count > maximum_score:
        print(f"Mypy failed! Maximum errors count allowed: {maximum_score}")
        raise SystemExit(1)


def run_cli() -> None:
    """Main procedure."""
    cli_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Python CI helpers"
    )
    cli_parser.add_argument("-action", type=str, required=True)
    cli_parser.add_argument(
        "-project_dir",
        required=True,
        type=pathlib.Path,
        help="Project (where we will run ci) directory",
    )
    cli_parser.add_argument("-pylint_score", type=float)
    cli_parser.add_argument("-pylint_args", type=str)
    cli_parser.add_argument("-mypy_score", type=int)
    cli_parser.add_argument("-extra_mypy_args", type=str)
    arguments: argparse.Namespace = cli_parser.parse_args()

    if arguments.action == "lint_pylint":
        run_pylint(arguments.project_dir, arguments.pylint_score, arguments.pylint_args)
    elif arguments.action == "lint_mypy":
        run_mypy(arguments.mypy_score, arguments.extra_mypy_args)
    else:
        print("No action provided")


if __name__ == "__main__":
    run_cli()
