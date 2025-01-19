#  =======================================================================
#
#  Copyright (c) 2022-2025 Workday, Inc.
#
#  This file is provided to you under the Apache License,
#  Version 2.0 (the "License"); you may not use this file
#  except in compliance with the License.  You may obtain
#  a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.
#
#  =======================================================================

import json
import re
import scr

from gh import JSON, Name, Names, Repo, Repos
from ghactor import GitHubActors

from typing import Optional, Union

class GitHubRepos(GitHubActors):

    # ===================================================================
    # Operations
    # ===================================================================

    def _branches(self, repo: Repo, teams: Optional[Names] = None) -> Names:
        patt: Union[re.Pattern, str, None] = None
        if not teams:
            teams = self._teams()
        if teams and teams[0] != 'all':
            if len(teams) > 1:
                patt = '^(' + '|'.join(teams) + ')[-/]'
            else:
                patt = '^' + teams[0] + '[-/]'
            patt = re.compile(patt)
        # unlike repos, the branches endpoint doesn't offer sorting
        brnames = self._paged_rec_names(f"/repos/{self._org}/{repo}/branches")
        return sorted(filter(patt.match, brnames) if patt else brnames)

    def _forks(self, repo: Repo) -> (Name, Names):
        """
        Retrieves the repo's fork information. If the repo is itself a fork,
        the first element of the return value is the parent (upstream) repo's
        name. Otherwise, the first element is `None`.

        The second element of the return value contains the names of the
        repo's child (downstream) forks, which may be empty.
        :param repo: The repo to gather information from.
        :return: `(ParentRepo | None, Sequence[ChildFork])`
        """
        rec = json.load(self._recv(f"/repos/{self._org}/{repo}", 'GET'))
        up: Optional[Name] = rec['parent']['full_name'] if rec['fork'] else None
        dn: list[Name] = self._fold_pages(
                f"/repos/{self._org}/{repo}/forks", _cb_fork_names, [])
        return up, dn

    def _repos(self) -> Repos:
        if (repos := self.__repos) is None:
            repos = self._paged_rec_names(
                f"/orgs/{self._org}/repos", {'sort': 'full_name'})
            self.__repos = repos
        return repos


    # ===================================================================
    # Internal
    # ===================================================================

    def __init__(self):
        """
        Consumes `CONFIG['repos']` if present.
        """
        super().__init__()
        if repos := scr.CONFIG.get('repos'):
            if isinstance(repos, str):
                # it's a file, read it as a list of words
                repos = scr.read_file(scr.resolve_conf_path(repos)).split()
            # whether read from a file or from config, it's now a list
            # de-duplicate regardless of source
            repos = tuple(frozenset(repos))
        self.__repos: Optional[Repos] = repos

# ===================================================================
# Static Helpers
# ===================================================================

def _cb_fork_names(acc: list[Name], rec: JSON) -> list[Name]:
    acc.append(rec['full_name'])
    return acc
