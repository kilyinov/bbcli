# -*- coding: utf-8 -*-

"""
    bb.pr.delete - deletes a pull request(s) given for the given id(s)
"""

import json

from typer import confirm

from bb.pr.diff import show_diff
from bb.utils import cmnd, request, richprint
from bb.utils.api import bitbucket_api


def delete_pull_request(_id: list, yes: bool, diff: bool) -> None:
    """
    Delete pull request(s) by ID
    """
    project, repository = cmnd.base_repo()

    for _no in _id:
        with richprint.live_progress(f"Fetching info on {_no} ..."):
            url = bitbucket_api.pull_request_info(project, repository, _no)
            pull_request_info = request.get(url)

        table = richprint.table(
            [("SUMMARY", "bold yellow"), ("DESCRIPTION", "#FFFFFF")],
            [
                ("ID", str(pull_request_info[1]["id"])),
                ("State", pull_request_info[1]["state"]),
                ("From Branch", pull_request_info[1]["fromRef"]["displayId"]),
                ("To Branch", pull_request_info[1]["toRef"]["displayId"]),
                ("Title", pull_request_info[1]["title"]),
                (
                    "Description",
                    (
                        pull_request_info[1]["description"]
                        if "description" in pull_request_info[1].keys()
                        else "-"
                    ),
                ),
            ],
            True,
        )
        richprint.console.print(table)

        if diff or confirm(
            f"Review diff between '{pull_request_info[1]['fromRef']['displayId']}' & '{pull_request_info[1]['toRef']['displayId']}' in PR #{_no}"
        ):
            show_diff(_no)

        if yes or confirm("Proceed"):
            with richprint.live_progress("Deleting Pull Request ..."):
                body = json.dumps({"version": int(pull_request_info[1]["version"])})
                pull_request = request.delete(url, body)

            if pull_request != 204:
                raise ValueError("Cannot delete pull request, Response<204>")

            richprint.console.print(
                f"Pull Request Deleted: {pull_request_info[1]['links']['self'][0]['href']}",
                highlight=True,
                style="bold green",
            )
