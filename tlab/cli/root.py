# Copyright (c) 2022 Shuhei Nitta. All rights reserved.

import click

import tlab


@click.group(
    name="tlab"
)
@click.version_option(tlab.__version__)
def main() -> None:
    """
    """
