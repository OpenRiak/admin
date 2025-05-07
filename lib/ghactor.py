#  =======================================================================
#
#  Copyright (c) 2024-2025 Workday, Inc.
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

import scr

from gh import Actors, GitHubError, GitHubRest, IdNames, NameIds, ObjID
from scr import Config, Name, Names

from typing import Optional

# ===================================================================
# Type Aliases
# ===================================================================

# AIRecs  = Mapping[ActorID, Mapping[str, Any]]
# ANRecs  = Mapping[Actor, Mapping[str, Any]] # always contains 'id' => ActorID

class GitHubActors(GitHubRest):

    # ===================================================================
    # Operations
    # ===================================================================

    def _actor_id(self, actor_name: Name, actor_type: str) -> ObjID:
        nids: NameIds
        if actor_type == 'Team':
            nids = self._team_ni_cache()[0]
        else:
            msg = f"unknown actor type '{actor_type}'"
            raise GitHubError(msg)
        if (nid := nids.get(actor_name)) is None:
            msg = f"unknown {actor_type.lower()} '{actor_name}'"
            raise GitHubError(msg)
        return nid

    def _actor_name(self, actor_id: ObjID, actor_type: str) -> Name:
        idns: IdNames
        if actor_type == 'Team':
            idns = self._team_ni_cache()[1]
        else:
            msg = f"unknown actor type '{actor_type}'"
            raise GitHubError(msg)
        if (name := idns.get(actor_id)) is None:
            msg = f"unknown {actor_type.lower()} '{actor_id}'"
            raise GitHubError(msg)
        return name

    def _teams(self) -> Names:
        if (teams := self.__teams) is None:
            # populate the cache
            self._team_ids()
            teams = self.__teams
        return teams

    def _team_ids(self) -> NameIds:
        # populates the cache of *configured* teams
        if (tids := self.__team_ids) is None:
            team_name_ids: NameIds = self._team_ni_cache()[0]
            if teams := self.__teams:
                tids = {n: i for n, i in team_name_ids.items() if n in teams}
            else:
                tids = team_name_ids
                self.__teams = tuple(tids.keys())
            self.__team_ids = tids
        return tids

    def _team_ni_cache(self) -> (NameIds, IdNames):
        # populates the cache of *all* teams
        team_name_ids: NameIds
        team_id_names: IdNames
        if (team_name_ids := self.__team_name_ids) is not None:
            team_id_names = self.__team_id_names
        else:
            team_name_ids = self._paged_rec_name_ids(
                f"/orgs/{self._org}/teams", {'sort': 'full_name'})
            team_id_names = {i: n for n, i in team_name_ids.items()}
            self.__team_name_ids = team_name_ids
            self.__team_id_names = team_id_names
        return team_name_ids, team_id_names

    # ===================================================================
    # Internal
    # ===================================================================

    def __init__(self):
        """
        Consumes `CONFIG['teams']` and/or `CONFIG['map_actors']` if present.
        """
        super().__init__()
        conf: Config = scr.CONFIG
        if teams := conf.get('teams'):
            if isinstance(teams, str):
                # it's a file, read it as a list of words
                teams = scr.read_file(scr.resolve_conf_path(teams)).split()
            # whether read from a file or from config, it's now a list
            # de-duplicate regardless of source
            teams = tuple(frozenset(teams))
        self._map_actors: bool = bool(conf.get('map_actors'))
        self.__teams: Optional[Actors] = teams
        self.__team_ids: Optional[NameIds] = None
        self.__team_name_ids: Optional[NameIds] = None
        self.__team_id_names: Optional[IdNames] = None
