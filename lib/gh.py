# ========================================================================
#
# Copyright (c) 2023-2025 Workday, Inc.
#
# This file is provided to you under the Apache License,
# Version 2.0 (the "License"); you may not use this file
# except in compliance with the License.  You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# ========================================================================

import json
import logging
import re
import scr
import urllib.parse
import urllib.request

from http.client import HTTPResponse
from scr import Name, Names
from typing import (
    Any, Callable, Mapping, NoReturn, Optional, Sequence, TypeVar, Union )
from urllib.request import Request

# ===================================================================
# Type Aliases
# ===================================================================

# Simple
Cache   = dict[str, Any]
Headers = dict[str, str]
JSON    = dict[str, Any]
ObjID   = int
ObjName = str
Query   = Mapping[str, Any]
Repo    = Name
Repos   = Sequence[Repo]
RestRC  = int
RestRCs = Sequence[RestRC]
RestOp  = str   # 'DELETE', 'GET', 'POST', 'PUT', etc.
UrlPath = str
URL     = str
URLs    = Sequence[URL]

# Derived
Actor   = Name
ActorID = ObjID
Actors  = Sequence[Actor]
IdNames = Mapping[ObjID, Name]
NameIds = Mapping[Name, ObjID]
Rule    = JSON
Rules   = Sequence[Rule]

FoldAccumulator   = TypeVar('FoldAccumulator')
PageFoldCallback  = Callable[[FoldAccumulator, JSON], FoldAccumulator]

# ===================================================================
# GitHub API
# ===================================================================

# 100 per page is the GH maximum
_GitHubRecsPerPage: int = 100

class GitHubRest:
    """
    Basic GitHub REST API operations.
    Not really much use on its own, meant to be sub-classed.
    """

    def _extract_recs(
            self, path: UrlPath, key: str, elems: Sequence[str],
            initial_query: Optional[Query] = None) \
            -> Mapping[Union[ObjID, ObjName], JSON]:
        """
        Buils a `Mapping` of records extracted from those returned from a
        paged GH API.

        For each JSON record `rec` returned from the equivalent of
            `_paged_recs(path, initial_query)`
        a mapping is added to the result as if by (but less tolerant than)
            `{rec[key]: scr.dict_with(rec, elems)}`.

        `key` and `elems` must all be top-level elements in the retrieved
        record - depth traversal is not supported.
        :param path: The GH REST API path, beginning with '/'.
        :param key: The record field that identifies the object.
        :param elems: Aditional fields included in the mapping.
        :return: The result `Mapping`.
        :raises KeyError: A specified element was not present in a retrieved
            record.
        """
        def cb(rec: JSON, acc: dict[Union[int, str], JSON]):
            acc[rec[key]] = {e: rec[e] for e in elems}
            return acc
        return self._fold_pages(path, cb, {}, initial_query)

    def _fold_pages(
            self, path: UrlPath,
            callback: PageFoldCallback,
            accumulator: FoldAccumulator,
            initial_query: Optional[Query] = None) -> FoldAccumulator:
        """
        Ingest records from a paged API path.
        :param path: The GH REST API path, beginning with '/'.
        :param callback: Fold callback, invoked with each JSON object returned
            by GET on `path`.
            The function returns the `accumulator` to be passed to its next
            invocation. The result of the last invocation is returned.
        :param accumulator: Initial accumulator value.
            Whether the input object is changed is determined by the
            `callback` implementation.
        :param initial_query: Initial query parameters.
            If `per_page` is unset the default is used.
            If `page` is unset paging starts at `1`.
            Any other mappings are used unchanged.
            The input object is unchanged.
        :return: The final `accumulator`.
        """
        for rec in self._paged_recs(path, initial_query):
            accumulator = callback(accumulator, rec)
        return accumulator

    def _paged_recs(
            self, path: UrlPath,
            initial_query: Optional[Query] = None) -> list[JSON]:
        """
        Collect records from a paged API path.
        :param path: The GH REST API path, beginning with '/'.
        :param initial_query: Initial query parameters.
            If `per_page` is unset the default is used.
            If `page` is unset paging starts at `1`.
            Any other mappings are used unchanged.
            The input object is unchanged.
        :return: A list of the returned records in the order received.
        """
        query: dict[str, Union[str, int]]
        if initial_query:
            if isinstance(initial_query, dict):
                query = initial_query.copy()
            else:
                query = dict(initial_query)
            if 'per_page' not in query:
                query['per_page'] = _GitHubRecsPerPage
        else:
            query = {'per_page': _GitHubRecsPerPage}
        page: Optional[int] = query.get('page', 1)
        recs = []
        append_rec  = recs.append
        append_list = recs.extend
        while page:
            query['page'] = page
            res = self._recv(path, 'GET', query=query)
            page = self._parse_next_page(res)
            js = json.load(res)
            if isinstance(js, list):
                append_list(js)
            else:
                append_rec(js)
        return recs

    def _paged_rec_names(
            self, path: UrlPath,
            initial_query: Optional[Query] = None) -> Names:
        """
        Get the names of the JSON records returned from `path`.
        :param path: The GH REST API path, beginning with '/'.
        :param initial_query: Initial query parameters.
            If `per_page` is unset the default is used.
            If `page` is unset paging starts at `1`.
            Any other mappings are used unchanged.
            The input object is unchanged.
        :return: All the records' `name` attributes in the order returned.
        """
        return tuple(self._fold_pages(
            path, _cb_rec_names, [], initial_query))

    def _paged_rec_name_ids(
            self, path: UrlPath,
            initial_query: Optional[Query] = None) -> NameIds:
        """
        Get the `name => id` mappings of the JSON records returned from `path`.
        :param path: The GH REST API path, beginning with '/'.
        :param initial_query: Initial query parameters.
            If `per_page` is unset the default is used.
            If `page` is unset paging starts at `1`.
            Any other mappings are used unchanged.
            The input object is unchanged.
        :return: A `Mapping` of `name => id`.
        """
        return self._fold_pages(
            path, _cb_rec_name_ids, {}, initial_query)

    def _recv(self,
            path: UrlPath, op: RestOp, ok: RestRCs = (200,),
            query: Optional[Query] = None) -> HTTPResponse:
        url = self._url(path, query)
        req = Request(url, headers=self._headers, method=op)
        return self._rest_op(req, ok)

    def _send(self,
              path: UrlPath, op: RestOp, data: JSON, ok: RestRCs = (200,),
              query: Optional[Query] = None) -> HTTPResponse:
        url = self._url(path, query)
        content = json.dumps(data).encode()
        req = Request(
            url, headers=self._headers, method=op, data=content)
        return self._rest_op(req, ok)

    def _rest_op(self, req: Request, ok: RestRCs) -> HTTPResponse:
        method = req.get_method()
        logging.info(f"{method}: {req.full_url}")
        if method in ('PUT', 'POST', 'PATCH'):
            logging.info(f"{method}: {req.data}")
        res: HTTPResponse = _opener.open(req)
        # We can't log the result body here, as it's read-once, but we can
        # log the URL and status.
        status = res.status
        if status in ok:
            logging.info(f"{method}: {status}: {res.reason}")
        else:
            # will log the error
            self._bad_status(res, method)
        return res

    def _parse_next_page(self, res: HTTPResponse) -> Optional[int]:
        if not (patt := self.__next_page_re):
            patt = re.compile(r'<([^>]+)>\s*;\s*rel="next"')
            self.__next_page_re = patt
        if hl := res.headers.get('link'):
            if url := patt.findall(hl):
                q_str = urllib.parse.urlparse(url[0]).query
                q_dict = dict(urllib.parse.parse_qsl(q_str))
                return int(q_dict['page'])

    @staticmethod
    def _url(path: UrlPath, query: Optional[Query] = None) -> URL:
        if query:
            q_quot = urllib.parse.urlencode(
                query, doseq=True, safe='', quote_via=urllib.parse.quote)
        else:
            q_quot = ''
        p_quot = urllib.parse.quote(path)
        parts = ('https', 'api.github.com', p_quot, q_quot, '')
        return urllib.parse.urlunsplit(parts)

    @staticmethod
    def _bad_status(res: HTTPResponse, method: str) -> NoReturn:
        msg = f"{method}: {res.status}: {res.reason}: {res.url}"
        logging.error(msg)
        raise GitHubError(msg)

    def __init__(self):
        """
        Sets up basic GitHub REST capabilities.
        Requires `CONFIG['auth'] => <gh-auth-token>`.
        """
        super().__init__()
        proj = scr.PROJ_NAME
        prog = scr.PROG_NAME
        self._org: Name = proj
        self._headers: Headers = {
            'Authorization':        scr.CONFIG['auth'],
            'Accept':               'application/vnd.github+json',
            'Content-Type':         'application/vnd.github+json',
            'User-Agent':           f"{proj}-{prog}",
            'X-GitHub-Api-Version': '2022-11-28'
        }
        self.__next_page_re: Optional[re.Pattern] = None

class GitHubError(Exception):
    pass

# ===================================================================
# Static Helpers
# ===================================================================

class _ErrorPassThru(urllib.request.HTTPErrorProcessor):
    def http_response(self, request, response):
        return response
    def https_response(self, request, response):
        return response

_opener: urllib.request.OpenerDirector = \
    urllib.request.build_opener(_ErrorPassThru)

dflt_creds_file: str = '~/.github.credentials'

def read_auth_token(cred_file: str) -> str:
    body = scr.read_file(cred_file)
    opts = (re.ASCII | re.MULTILINE)
    # GH access tokens start with 'ghp_'
    for tok in re.findall(r'^github\.token=(.+)$', body, opts):
        if tok.startswith('ghp_'):
            # GH requires a 'Bearer' token
            return 'Bearer ' + tok
    raise ValueError(f"Credentials not complete in {cred_file}")

def _cb_rec_names(acc: list[Name], rec: JSON) -> list[Name]:
    acc.append(rec['name'])
    return acc

def _cb_rec_name_ids(
        acc: dict[Name, ObjID], rec: JSON) -> dict[Name, ObjID]:
    acc[rec['name']] = rec['id']
    return acc
