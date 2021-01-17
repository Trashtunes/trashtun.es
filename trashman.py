from github import Github
import datetime
import os
import re
import yaml
from io import BytesIO
import time

import requests
import zipfile

datafile = "_data/trash.yml"

access_token = os.environ["GITHUB_TOKEN"]
repository = os.environ["REPOSITORY"]
issue_nr = int(os.environ["ISSUE"])
issue_nr = 4

print("Repository: {}".format(repository))
print("Issue Number: {}".format(issue_nr))


g = Github(access_token)
repo = g.get_repo(repository)
issue = repo.get_issue(number=issue_nr)


def take_trash_from_github(issue):
    body = issue.body
    latest_comment_user = issue.user

    comments = issue.get_comments()
    if comments.totalCount > 0:
        try:
            latest_comment = comments.reversed[0]
            latest_comment_user = latest_comment.user
            body = latest_comment.body
        except IndexError:
            pass

    # regex returns matches in a list of tuples.
    # Each tuple has this structure: ('```', 'content', '```')
    trashdefinitions = re.findall(r"(```)([\s\S]*?)(```)", body)
    # we are interested in the content of the first tuple in a posting
    trashyaml = trashdefinitions[0][1]
    new_trash = yaml.load(trashyaml, Loader=yaml.FullLoader)
    return new_trash, latest_comment_user


def upload_audio_to_s3(new_trash):
    file_url = new_trash.pop("audio_comment")
    r = requests.get(file_url, allow_redirects=True)

    audiofile = " "
    zip = zipfile.ZipFile(BytesIO(r.content))
    files = zip.namelist()
    for file in files:
        if file.endswith(".mp3"):
            # audiofile = zip.open(file)
            audiofile = file

    # TODO: handle upload
    return audiofile


def insert_new_trash(new_trash):
    with open(datafile, "r") as file:
        trash_list = yaml.load(file, Loader=yaml.FullLoader)
        written = False

        # check if an entry already exists
        for index in range(len(trash_list)):
            if trash_list[index]["issue_id"] == new_trash["issue_id"]:
                # update it if it's the case
                trash_list[index] = new_trash
                written = True
                break
        # else append new trash
        if not written:
            trash_list.append(new_trash)

        # reverse sort the complete trahs by date then id
        trash_list.sort(
            key=lambda k: (
                datetime.datetime.strptime(k["date"], "%d.%m.%Y"),
                k.get("issue_id", 0),
            ),
            reverse=True,
        )

    return trash_list


def publish_changes(dry_run, repo, trashyaml, latest_comment_user):
    if dry_run:
        return

    def commit_changes(repo, branch_name, trashyaml):
        commit_message = "Adds track {} as specified in issue #{}".format(
            new_trash["songtitle"], new_trash["issue_id"]
        )

        ref = "refs/heads/" + branch_name
        try:
            repo.create_git_ref(ref, sha=repo.get_branch("master").commit.sha)
            old_file = repo.get_contents(datafile)
        except:
            # ref = repo.get_git_matching_refs("heads/" + branch_name)[0]
            old_file = repo.get_contents(datafile, ref)
            pass

        repo.update_file(
            path=old_file.path,
            message=commit_message,
            content=trashyaml,
            sha=old_file.sha,
            branch=branch_name,
        )

    def create_pr(repo, branch_name):

        pr_title = "Adds {} to Trash Tun.es".format(new_trash["songtitle"])
        pr_body = "Closes #{}".format(new_trash["issue_id"])

        try:
            pr = repo.create_pull(pr_title, pr_body, head=branch_name, base="master")
        except Exception as e:
            pr = repo.get_pulls(
                state="open", sort="created", head=branch_name, base="master"
            )[0]

        return pr

    def merge_pr(repo, pr, user):
        if user in repo.get_collaborators():
            if pr.mergeable:
                pr.merge()
            else:
                pr.create_issue_comment("Couldn't merge automatically.")
                pr.add_to_assignees(user)
        else:
            pr.create_issue_comment(
                "Thank you for your suggestions. Our responsible trash men will take over from here"
            )
            pr.add_to_assignees(repo.get_collaborators())

    branch_name = "_".join(new_trash["songtitle"].lower().split()) + "_#{}".format(
        new_trash["issue_id"]
    )

    commit_changes(repo, branch_name, trashyaml)
    pr = create_pr(repo, branch_name)
    merge_pr(repo, pr, latest_comment_user)


new_trash, latest_comment_user = take_trash_from_github(issue)

new_trash["issue_id"] = issue.number
new_trash["date"] = issue.created_at.strftime("%d.%m.%Y")
new_trash["comment_url"] = upload_audio_to_s3(new_trash)

trash = insert_new_trash(new_trash)
trashyaml = yaml.dump(trash, allow_unicode=True)

publish_changes(
    dry_run=False,
    repo=repo,
    trashyaml=trashyaml,
    latest_comment_user=latest_comment_user,
)
