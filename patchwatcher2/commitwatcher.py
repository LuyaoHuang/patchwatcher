import git
import re
import logging
from utils import downloadsourcecode

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='patchwatcher.log')

class CommitWatcher(object):
    def __init__(self, name, repo_url=None, repo_path=None):
        self.name = name
        self.repo_url = repo_url
        if repo_path:
            self.repo = git.Repo(repo_path)
            self.git = self.repo.git
        elif repo_url:
            if not downloadsourcecode(repo_url):
                raise Exception("Fail to clone source code")
            self.repo = git.Repo("./%s" % name)
            self.git = self.repo.git
        else:
            raise Exception("Need repo_url or repo_path")

    def pull(self):
        """
        return commit list as sucess, None is failed
        """
        ret_list = []

        commit_id, _ = self.head_commit()
        try:
            out = self.git.pull()
        except git.GitCommandError:
            logging.error("Fail to run get pull")
            return

        if 'Already up-to-date' in out:
            return ret_list
        else:
            tmp = self.get_commit_by_commit(commit_id, 'master')
            if tmp:
                return tmp.keys()

    def head_commit(self):
        out = self.git.log('HEAD^..master','--pretty=oneline')
        head = self._parse_git_log(out)
        return head.keys()[0], head.values()[0]

    def _parse_git_log(self, output):
        ret = {}

        for line in output.splitlines():
            match = re.match('^([0-9a-f]+) (.+)', line)
            if not match:
                logging.warning("git log failed, output: %s" % output)
                return
            commit, subject = match.groups()
            ret[commit] = subject

        return ret

    def get_commit_by_date(self, date_since, date_before):

        output = self.git.log('--since="%s"' % date_since, '--before="%s"' % date_before, '--pretty=oneline')
        return self._parse_git_log(output)

    def get_commit_by_commit(self, from_commit, to_commit):
        output = self.git.log('%s..%s' % (from_commit, to_commit), '--pretty=oneline')
        return self._parse_git_log(output)

    def get_commit_infos(self, commit_id):
        """
        Since there is no diff info in gitpython
        commit object, we need parse it by ourselves
        """
        ret_infos= {}
        try:
            output = self.git.show(commit_id)
        except git.GitCommandError:
            logging.error("Fail to get %s info" % commit_id)
            return

        next_line = ""
        diff = ""
        desc = ""
        for line in output.splitlines():
            if next_line == 'desc':
                match = re.match('^diff --git (.+) (.+)', line)
                if match:
                    diff += line
                    next_line = 'diff'
                    continue
                match = re.match('^    (.+)', line)
                if match:
                    new_line = match.group(1)
                else:
                    new_line = line

                desc += '%s\n' % new_line
                continue

            if next_line == 'diff':
                diff += '%s\n' % line
                continue

            if line == '':
                continue

            if next_line == 'subject':
                match = re.match('^    (.+)', line)
                if not match:
                    logging.error("Fail to parse subject %s" % line)
                    return
                ret_infos['subject'] = match.group(1)
                next_line = 'desc'
                continue

            match = re.match('^Author: (.+)', line)
            if match:
                ret_infos['author'] = match.group(1)
                continue

            match = re.match('^Date: (.+)', line)
            if match:
                ret_infos['date'] = match.group(1)
                next_line = 'subject'
                continue

        ret_infos['desc'] = desc
        ret_infos['diff'] = diff
        ret_infos['commit'] = commit_id
        return ret_infos
