#!/usr/bin/env python3
"""Random str generator."""
import argparse
import random
import string


def run_cli() -> None:
    """Main procedure."""
    cli_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Random str generator"
    )
    cli_parser.add_argument("-length", "-l", default=32, type=int, required=False)
    cli_parser.add_argument("--upper", nargs="?", const=True, default=False)
    arguments: argparse.Namespace = cli_parser.parse_args()
    print(
        "".join(
            random.choices(
                string.ascii_uppercase
                if arguments.upper
                else string.ascii_lowercase + string.digits,
                k=arguments.length,
            )
        )
    )


if __name__ == "__main__":
    run_cli()
