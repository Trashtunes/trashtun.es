from github import Github
import datetime
import os
import re
import yaml
from io import BytesIO

import requests
import zipfile

access_token = os.environ["GITHUB_TOKEN"]
repository = os.environ["REPOSITORY"]
issue_nr = int(os.environ["ISSUE"])

print("Repository: {}".format(repository))
print("Issue Number: {}".format(issue_nr))


g = Github(access_token)
repo = g.get_repo(repository)
issue = repo.get_issue(number=issue_nr)


def take_trash_from_github(issue):
    body = issue.body
    comments = issue.get_comments()

    if comments.totalCount > 0:
        try:
            latest_comment = comments.reversed[0]
            body = latest_comment.body
        except IndexError:
            pass

    # regex returns matches in a list of tuples.
    # Each tuple has this structure: ('```', 'content', '```')
    trashdefinitions = re.findall(r"(```)([\s\S]*?)(```)", body)
    # we are interested in the content of the first tuple in a posting
    trashyaml = trashdefinitions[0][1]
    new_trash = yaml.load(trashyaml, Loader=yaml.FullLoader)
    return new_trash


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
    with open("./_data/trash.yml", "r") as file:
        trash_list = yaml.load(file, Loader=yaml.FullLoader)
        written = False

        # check if an entry already exists
        for index in range(len(trash_list)):
            if trash_list[index]["id"] == new_trash["id"]:
                # update it if it's the case
                trash_list[index] = new_trash
                written = True
                break
        # else append new trash
        if not written:
            trash_list.append(new_trash)

        # reverse sort the complete trahs by date then id
        trash_list.sort(
            key=lambda k: (datetime.datetime.strptime(k["date"], "%d.%m.%Y"), k["id"]),
            reverse=True,
        )

    return trash_list


new_trash = take_trash_from_github(issue)

new_trash["id"] = issue.number
new_trash["date"] = issue.created_at.strftime("%d.%m.%Y")
new_trash["comment_url"] = upload_audio_to_s3(new_trash)

trash = insert_new_trash(new_trash)

with open("./_data/trash.yml", "w") as file:
    yaml.dump(trash, file, allow_unicode=True)
