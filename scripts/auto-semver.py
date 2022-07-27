#!/usr/bin/env python3
"""Automatic semantic versioning.

Requirements:
    — pip install GitPython
    — pip install semver

Env variables:
    — AUTOSEMVER_GIT_PUSH_USER   (this and next variables required for pushing to git from CI/CD pipeline)
    — AUTOSEMVER_GIT_PUSH_TOKEN

    — CI_ENVIRONMENT_NAME  (this env variable is glued with "release-" prefix and
                            this is gets your "release-prod" protection from cleanup tag)

    — CI_COMMIT_TAG

Usage:
    ./auto-versioning.py version  (run automatic versioning)
    ./auto-versioning.py mark  (this command made git tag to protect your release)
"""
import os
import typing

import git
from semver import VersionInfo


class _Settings:
    """Basic settings.

    I love encapsulation.
    """

    TAG_PREFIX: typing.Final[str] = "v"
    RELEASE_PREFIX: typing.Final[str] = "release-"
    BASIC_MARKER_OF_MERGE: typing.Final[str] = "Merge branch"
    DEFAULT_TAG_IF_NOT_TAG: typing.Final[str] = "1.0.0"
    REMOTE_PORT_TO_REPLACE: typing.Final[str] = ":7999"
    PUSH_REPO_PREFIX: typing.Final[
        str
    ] = f"https://{os.environ['AUTOSEMVER_GIT_PUSH_USER']}:{os.environ['AUTOSEMVER_GIT_PUSH_TOKEN']}@"
    CURRENT_ENVIRONMENT: typing.Final[str] = os.environ["CI_ENVIRONMENT_NAME"]
    CURRENT_COMMIT_TAG: typing.Final[str] = os.environ["CI_COMMIT_TAG"]


settings: _Settings = _Settings()


class _GitTagHelpers:
    """High level wrapper around gitpython lib.

    Contains couple useful in our CI methods.
    """

    def __init__(self, current_repo: git.Repo):
        self._current_repo = current_repo

    def prepare_repo_for_push(self):
        """This function allows to push in current git repo from current copy
        in CI/CD."""
        origin_object: git.Remote = self._current_repo.remotes.origin
        with origin_object.config_writer as config_writer:
            config_writer.set(
                "url",
                settings.PUSH_REPO_PREFIX
                + origin_object.url.split("@")[1].replace(
                    settings.REMOTE_PORT_TO_REPLACE, ""
                ),
            )

    def add_tag(self, new_tag_value: str, from_ref=None) -> None:
        """Push new tag."""
        self._current_repo.create_tag(
            new_tag_value, ref=from_ref if from_ref else "HEAD"
        )
        self._current_repo.remotes.origin.push(new_tag_value)

    def remove_tag(self, tag_name: str) -> None:
        """Helper for tag remove."""
        self._current_repo.delete_tag(tag_name)
        self._current_repo.remotes.origin.push(f":{tag_name}")

    def fetch_ordered_tags(self) -> tuple:
        """Return sorted tags."""
        return tuple(
            sorted(
                self._current_repo.tags,
                key=lambda _tag_obj: _tag_obj.commit.committed_datetime,
            )
        )


def _predict_next_tag(
    current_repository: git.Repo, tag_api: _GitTagHelpers
) -> tuple[str, str] | None:
    """Beautiful automatic versioning."""
    latest_commit: git.Commit = current_repository.commit()
    last_message: str = latest_commit.message.lower()
    if settings.BASIC_MARKER_OF_MERGE.lower().strip() in last_message:
        tags_list: tuple = tag_api.fetch_ordered_tags()
        if len(tags_list) < 1:
            return str(None), settings.DEFAULT_TAG_IF_NOT_TAG
        last_tag_object: git.Tag = tags_list[-1]
        if last_tag_object.commit == latest_commit:
            print("Last commit already tagged")
            return None
        last_tag: VersionInfo = VersionInfo.parse(
            last_tag_object.name.lower().lstrip(settings.TAG_PREFIX)
        )
        if "bugfix/" in last_message or "hotfix/" in last_message:
            return str(last_tag), str(last_tag.bump_patch())
        elif "feature/" in last_message:
            return str(last_tag), str(last_tag.bump_minor())
    return None


def generate_auto_version() -> None:
    """Process automatic version analyse."""
    current_repository: git.Repo = git.Repo()
    tag_api: _GitTagHelpers = _GitTagHelpers(current_repository)
    predict_pair: tuple[str, str] | None = _predict_next_tag(
        current_repository, tag_api
    )
    if predict_pair is not None:
        new_full_tag: str = settings.TAG_PREFIX + predict_pair[1]
        tag_api.prepare_repo_for_push()
        tag_api.add_tag(new_full_tag)
        print(f"Automatic versioning: {predict_pair[0]} ——> {new_full_tag}🏷️")
    else:
        print("Skipped automatic versioning")


def mark_release() -> None:
    """Process automatic version analyse."""
    full_environ_protection_tag: typing.Final[
        str
    ] = f"{settings.RELEASE_PREFIX}{settings.CURRENT_ENVIRONMENT}"
    current_repository: git.Repo = git.Repo()
    tag_api: _GitTagHelpers = _GitTagHelpers(current_repository)
    tag_api.prepare_repo_for_push()
    try:
        tag_api.remove_tag(full_environ_protection_tag)
    except git.exc.GitCommandError:
        print(f"There is no {full_environ_protection_tag} tag, but it's fine")
    tag_api.add_tag(full_environ_protection_tag, settings.CURRENT_COMMIT_TAG)
    print(
        f"Added tag {full_environ_protection_tag} for commit {settings.CURRENT_COMMIT_TAG}"
    )


if __name__ == "__main__":
    import argparse

    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("action", help="action to perform")
    current_arguments: argparse.Namespace = parser.parse_args()
    if current_arguments.action == "version":
        generate_auto_version()
    elif current_arguments.action == "mark":
        mark_release()
    else:
        print("No action")
