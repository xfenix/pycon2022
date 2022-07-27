#!/usr/bin/env python3
"""This EXAMPLE script iterate over CI files, add all CD pipelines to each and
send this bunch to gitlab linter if all tries are valid, then this script will
be happy, otherwise deal with error."""
import os
import pathlib

import requests
import yaml


VALIDATE_CI_API: str = "https://gitlab.company.com/api/v4/ci/lint"
ROOT_DIR: pathlib.Path = pathlib.Path(__file__).parents[2]
FOLDERS_TO_GATHER: tuple = (ROOT_DIR / "ci", ROOT_DIR / "cd")
GITLAB_TOKEN: str = os.getenv("GITLAB_TOKEN", "")
GITLAB_CI_ALL_TPL: str = """
include:
{}
""".strip()
GITLAB_CI_ONE_FILE_TPL: str = """
- project: 'xfenix/pycon2022'
  file: '{}'
""".strip()
requests.packages.urllib3.disable_warnings()


if not GITLAB_TOKEN:
    print("Please, provide API token")
    raise SystemExit(1)


def search_when_without_rules_and_rise(file_path: pathlib.Path) -> None:
    """Checking .yml correct usage rules "when" in stages."""
    with open(file_path) as file:
        data: dict = yaml.load(file, Loader=yaml.BaseLoader)
        for job in data:
            if isinstance(data[job], dict):
                for stages in data[job]:
                    if stages == "when":
                        print(
                            f'Please usage "when" only in "rules" - job={job} in file={file_path}'
                        )
                        raise SystemExit(1)


def run_cli() -> None:
    """Validation of .gitlab-ci.yml."""
    prepared_ci_templates: list = []
    prepared_cd_templates: list = []
    for one_folder in FOLDERS_TO_GATHER:
        for one_file in one_folder.glob("*.yml"):
            search_when_without_rules_and_rise(one_file)
            if one_folder.name == "cd" and one_file.name.startswith("bot"):
                continue
            (
                prepared_ci_templates
                if one_folder.name == "ci"
                else prepared_cd_templates
            ).append(
                GITLAB_CI_ONE_FILE_TPL.format(f"{one_folder.name}/{one_file.name}")
            )
    for one_ci_tpl in prepared_ci_templates:
        compiled_one_tpl: str = GITLAB_CI_ALL_TPL.format(
            one_ci_tpl + "\n" + "\n".join(prepared_cd_templates)
        )
        ci_lint_response: requests.Response = requests.post(
            VALIDATE_CI_API,
            json={"content": compiled_one_tpl},
            headers={"PRIVATE-TOKEN": GITLAB_TOKEN},
            verify=False,
        )
        if ci_lint_response.status_code != requests.codes["OK"]:
            raise SystemExit(1)
        decoded_answer: dict = ci_lint_response.json()
        if decoded_answer["status"] != "valid":
            print(decoded_answer["errors"])
            raise SystemExit(1)
    print("Configuration is valid!")


if __name__ == "__main__":
    run_cli()
