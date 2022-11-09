# -*- coding: utf-8 -*-

# Importing the necessary modules for the script to run.
from typer import prompt, Exit
from bb.pr.diff import show_diff
from bb.utils import cmnd, iniparser, request, api, richprint, cp


def gather_facts(
    target: str,
    from_branch: str,
    project: str,
    repository: str,
    username: str,
    token: str,
    bitbucket_host: str,
    title_and_description: str,
) -> list:
    """
    It gathers facts for  the pull request from bitbucket and local git
    repository
    """

    with richprint.live_progress(f"Gathering facts on '{repository}' ..."):
        repo_id = None
        for repo in request.get(
            api.get_repo_info(bitbucket_host, project), username, token
        )[1]["values"]:
            if repo["name"] == repository:
                repo_id = repo["id"]

        reviewers = []
        if repo_id is not None:
            for dict_item in request.get(
                api.default_reviewers(
                    bitbucket_host, project, repo_id, from_branch, target
                ),
                username,
                token,
            )[1]:
                for key in dict_item:
                    if key == "name":
                        reviewers.append({"user": {"name": dict_item[key]}})

        header = [("SUMMARY", "bold yellow"), ("DESCRIPTION", "#FFFFFF")]

        summary = [
            ("Project", project),
            ("Repository", repository),
            ("Repository ID", str(repo_id)),
            ("From Branch", from_branch),
            ("To Branch", target),
            ("Title & Description", title_and_description),
        ]

    table = richprint.table(header, summary, True)
    richprint.console.print(table)
    return [header, reviewers]


def create_pull_request(target: str, yes: bool, diff: bool, rebase: bool) -> None:
    """
    It creates a pull request.
    """
    from_branch = cmnd.from_branch()
    if target == from_branch:
        richprint.console.print("Source & target cannot be the same", style="bold red")
        raise Exit(code=1)

    if rebase:
        with richprint.live_progress(
            f"Rebasing {from_branch} with {target} ... "
        ) as live:
            cmnd.git_rebase(target)
            live.update(richprint.console.print("REBASED", style="bold green"))

    username, token, bitbucket_host = iniparser.parse()
    project, repository = cmnd.base_repo()
    title_and_description = cmnd.title_and_description()
    header, reviewers = gather_facts(
        target,
        from_branch,
        project,
        repository,
        username,
        token,
        bitbucket_host,
        title_and_description,
    )

    if yes or prompt("Proceed [y/n]").lower().strip() == "y":
        with richprint.live_progress(f"Creating Pull Request ..."):
            url = api.pull_request_create(bitbucket_host, project, repository)
            body = api.pull_request_body(
                title_and_description,
                from_branch,
                repository,
                project,
                target,
                reviewers,
            )
            pull_request = request.post(url, username, token, body)

        if pull_request[0] == 201:
            richprint.console.print(
                f"Pull Request Created: {pull_request[1]['links']['self'][0]['href']}",
                highlight=True,
                style="bold green",
            )
            id = pull_request[1]["links"]["self"][0]["href"].split("/")[-1]
            cp.copy_to_clipboard(pull_request[1]["links"]["self"][0]["href"])
        elif pull_request[0] == 409:
            richprint.console.print(
                f"Message: {pull_request[1]['errors'][0]['message']}",
                highlight=True,
                style="bold red",
            )
            richprint.console.print(
                f"Existing Pull Request: {pull_request[1]['errors'][0]['existingPullRequest']['links']['self'][0]['href']}",
                highlight=True,
                style="bold yellow",
            )
            id = pull_request[1]["errors"][0]["existingPullRequest"]["links"]["self"][
                0
            ]["href"].split("/")[-1]
            cp.copy_to_clipboard(
                pull_request[1]["errors"][0]["existingPullRequest"]["links"]["self"][0][
                    "href"
                ]
            )
        else:
            request.http_response_definitions(pull_request[0])
            raise Exit(code=1)

    if diff:
        show_diff(id)
