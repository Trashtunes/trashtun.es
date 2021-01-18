from github import Github
import datetime
import os
import traceback
import re
import yaml
from io import BytesIO
import time
from pprint import pprint
import requests
import zipfile


class Trashman:

    latest_comment_user = ""
    datafile = "_data/trash.yml"

    def comment_error(self, error, latest_comment_user=None):
        if not latest_comment_user:
            latest_comment_user = self.latest_comment_user

        errortext_template = (
            " **Error**\n"
            "Encountered an error while handling your trash:\n"
            " \n"
            "```\n"
            "{}\n"
            " \n"
            " \n"
            "{}\n"
            "```\n"
            " \n"
            "I hope this error is helpful.\n"
            "You can retry by appending a new comment to this issue with the same formatting or by editing the issue content.\n"
            " \n"
            "And as always, remember to  **REUSE**, **REDUCE** and **RAVE**\n"
        )

        errortext = errortext_template.format(error, traceback.format_exc())
        self.issue.create_comment(self.g.render_markdown(errortext, context=self.repo))
        self.issue.add_to_assignees(latest_comment_user)
        print("::error file=,line=,col=::" + str(error))
        raise (error)

    def take_trash_from_github(self, issue):
        print("::group::Loading yaml from issue/comment")

        print("Setting default body and user from issue")
        body = issue.body
        latest_comment_user = issue.user

        print("Loading body and user from last comment")

        comments = issue.get_comments()
        if comments.totalCount > 0:
            try:
                for comment in comments.reversed:
                    if comment.user.name:

                        latest_comment_user = comment.user
                        body = comment.body
                        break
            except IndexError:
                pass

        print("Comment: \n{}".format(body))
        print("User: {}".format(latest_comment_user.name))

        try:
            # regex returns matches in a list of tuples.
            # Each tuple has this structure: ('```', 'content', '```')
            trashdefinitions = re.findall(r"(```)([\s\S]*?)(```)", body)
            # we are interested in the content of the first tuple in a posting
            trashyaml = trashdefinitions[0][1]

            print("YAML-String: \n{}".format(trashyaml))
            new_trash = yaml.load(trashyaml, Loader=yaml.FullLoader)
        except Exception as e:
            self.comment_error(e, latest_comment_user)

        print("Parsed YAML: \n{}".format(new_trash))
        print("::endgroup::")

        return new_trash, latest_comment_user

    def upload_audio_to_s3(self, issue, new_trash):
        print("::group::Uploading audio to S3")

        file_url = new_trash.pop("audio_comment")
        print("Identified audio url: {}".format(file_url))

        try:
            print("Downloading file")
            r = requests.get(file_url, allow_redirects=True)
        except Exception as e:
            self.comment_error(e)

        audiofile = " "

        try:
            zip = zipfile.ZipFile(BytesIO(r.content))
            files = zip.namelist()
            for file in files:
                if file.endswith(".mp3"):
                    print("Unzipping file: {}".format(file))
                    # TODO: handle unzipping
                    # audiofile = zip.open(file)

            # TODO: handle upload
            audiofile = file
            # TODO:audiofile contains public s3 locator
        except Exception as e:
            self.comment_error(e)

        print("::endgroup::")
        return audiofile

    def insert_new_trash(self, new_trash):
        print("::group::Inserting trash to existing file")
        with open(self.datafile, "r") as file:
            trash_list = yaml.load(file, Loader=yaml.FullLoader)
            print("Loaded existing data file")
            pprint(trash_list)
            written = False

            print(
                "Check if datafile has an entry with the matching index: {}".format(
                    new_trash["issue_id"]
                )
            )
            for index in range(len(trash_list)):
                try:
                    if trash_list[index]["issue_id"] == new_trash["issue_id"]:
                        print("Found entry with matching id")
                        trash_list[index] = new_trash
                        written = True
                        break
                except KeyError:
                    pass

            if not written:
                print("No matching entry found. Appending new trash.")
                trash_list.append(new_trash)

            print("Sorting all entries by data and if possible by id")
            trash_list.sort(
                key=lambda k: (
                    datetime.datetime.strptime(k["date"], "%d.%m.%Y"),
                    k.get("issue_id", 0),
                ),
                reverse=True,
            )
            print("::endgroup::")
        return trash_list

    def commit_changes(self, branch_name, trashyaml, new_trash):
        print("::group::Commiting changes")

        commit_message = "Adds track {} as specified in issue #{}".format(
            new_trash["songname"], new_trash["issue_id"]
        )

        ref = "refs/heads/" + branch_name
        try:
            self.repo.create_git_ref(ref, sha=self.repo.get_branch("master").commit.sha)
            print("Created new branch: {}".format(ref))
            old_file = self.repo.get_contents(self.datafile)
        except:
            print("Reused old branch: {}".format(ref))
            old_file = self.repo.get_contents(self.datafile, ref)
            pass

        self.repo.update_file(
            path=old_file.path,
            message=commit_message,
            content=trashyaml,
            sha=old_file.sha,
            branch=branch_name,
        )
        print("Commited file")
        print("::endgroup::")
        return

    def create_pr(self, branch_name, new_trash):
        print("::group::Creating PR")
        pr_title = "Adds {} to Trash Tun.es".format(new_trash["songname"])
        pr_body = "Closes #{}".format(new_trash["issue_id"])

        try:
            pr = self.repo.create_pull(
                pr_title, pr_body, head=branch_name, base="master"
            )
            print("Created new PR")
        except Exception as e:
            pr = self.repo.get_pulls(
                state="open", sort="created", head=branch_name, base="master"
            )[0]
            print("Reused existing PR")

        print("::endgroup::")

        return pr

    def merge_pr(self, pr, user):
        print("::group::Trying to merge PR")
        if user in self.repo.get_collaborators():
            print("User {} has the right to commit".format(user))
            time.sleep(4)
            if self.pr.mergeable:
                pr.merge()
                print("Merged commit")
            else:
                print(
                    "Couldn't merge automatically. Merge status: {}".format(
                        self.pr.mergeable_state
                    )
                )
                pr.create_issue_comment("Couldn't merge automatically.")
                pr.add_to_assignees(user)

        else:
            print("User {} has not the right to commit".format(user))
            pr.create_issue_comment(
                "Thank you for your suggestions. Our responsible trash men will take over from here"
            )
            print("Created issue comment")
            pr.add_to_assignees(repo.get_collaborators())
            print("Assigned collaborators")

        print("::endgroup::")
        return

    def publish_changes(self, trashyaml, new_trash):

        branch_name = "_".join(new_trash["songname"].lower().split()) + "_#{}".format(
            new_trash["issue_id"]
        )

        print("::group::Interacting with repository content")
        self.commit_changes(branch_name, trashyaml, new_trash)
        pr = self.create_pr(branch_name, new_trash)
        self.merge_pr(pr, self.latest_comment_user)
        print("::endgroup::")

    def main(self):

        access_token = os.environ["GITHUB_TOKEN"]
        repository = os.environ["REPOSITORY"]
        issue_nr = int(os.environ["ISSUE"])

        issue_nr = 12

        print("Repository: {}".format(repository))
        print("Issue Number: {}".format(issue_nr))

        self.g = Github(access_token)
        self.repo = self.g.get_repo(repository)
        self.issue = self.repo.get_issue(number=issue_nr)

        if not self.repo.get_label("new trash") in self.issue.labels:
            exit()

        self.new_trash, self.latest_comment_user = self.take_trash_from_github(
            self.issue
        )

        self.new_trash["issue_id"] = self.issue.number
        self.new_trash["date"] = self.issue.created_at.strftime("%d.%m.%Y")
        self.new_trash["comment_url"] = self.upload_audio_to_s3(
            self.issue, self.new_trash
        )

        trash = self.insert_new_trash(self.new_trash)
        trashyaml = yaml.dump(trash, allow_unicode=True)

        self.publish_changes(trashyaml=trashyaml, new_trash=self.new_trash)


if __name__ == "__main__":
    Trashman().main()