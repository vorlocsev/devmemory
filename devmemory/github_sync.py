"""Bounded GitHub GET snapshots. Credentials never enter the journal or follow redirects."""
import json, re, urllib.request, urllib.error
from pathlib import Path
from functools import partial
from urllib.parse import quote

REPO=re.compile(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}\Z')
SHA=re.compile(r'[a-f0-9]{40}\Z')
LIMIT=5
MAX_RESPONSE=512*1024

class GitHubError(Exception): pass
class GitHubRateLimit(GitHubError): pass

def normalize_repo(value):
    if not isinstance(value,str) or not REPO.fullmatch(value) or value.split('/')[1] in ('.','..'):
        raise ValueError('Use GitHub owner/repository, not a URL')
    return value.lower()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def validate_token(value):
    # Fine-grained PAT format only. The prefix does not prove its permissions.
    if not isinstance(value,str) or (value and not re.fullmatch(r'github_pat_[A-Za-z0-9_]{20,250}',value)):
        raise ValueError('Configure an empty or valid fine-grained GitHub PAT')
    return value

def load_token(mode,data,environ):
    if mode=='standalone':
        return validate_token(environ.get('DEVMEMORY_GITHUB_TOKEN',''))
    path=Path(data)/'options.json'
    if not path.exists(): return ''
    try:
        with path.open('rb') as file:
            raw=file.read(65537)
        if len(raw)>65536: raise ValueError()
        options=json.loads(raw)
        if not isinstance(options,dict): raise ValueError()
        return validate_token(options.get('github_token',''))
    except (OSError,ValueError,RecursionError):
        raise ValueError('Invalid GitHub credential configuration; check app options') from None

def request_json(path,token=''):
    # No arbitrary URL, hostname, redirect or mutating HTTP method.
    allowed=r'/repos/[a-z0-9][a-z0-9-]{0,38}/[a-z0-9_.-]{1,100}/(?:commits\?per_page=5|pulls\?state=all&sort=updated&direction=desc&per_page=5|actions/runs\?per_page=5)'
    if not re.fullmatch(allowed,path) or path.split('/')[3] in ('.','..'):
        raise GitHubError('Disallowed GitHub API path')
    token=validate_token(token)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    headers={
        'Accept':'application/vnd.github+json','User-Agent':'DevMemory/0.3.0',
        'X-GitHub-Api-Version':'2022-11-28'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request('https://api.github.com'+path,headers=headers,method='GET')
    try:
        with opener.open(req,timeout=4) as response:
            raw=response.read(MAX_RESPONSE+1)
            if len(raw)>MAX_RESPONSE: raise GitHubError('GitHub response exceeds limit')
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        if e.code==401: raise GitHubError('GitHub credential rejected; check token configuration') from None
        if e.code in (403,429): raise GitHubRateLimit('GitHub rate limit or access denied; retry later') from None
        raise GitHubError('GitHub HTTP '+str(e.code)) from None
    except (OSError,ValueError,RecursionError):
        raise GitHubError('GitHub unavailable or invalid response') from None

def sha(value):
    if not isinstance(value,str) or not SHA.fullmatch(value): raise GitHubError('Invalid GitHub commit SHA')
    return value

def clean(value,n):
    if not isinstance(value,str): raise GitHubError('Invalid GitHub metadata')
    return value.strip()[:n].strip()

def number(value):
    if type(value) is not int or value<=0: raise GitHubError('Invalid GitHub identifier')
    return value

def collection(value):
    if not isinstance(value,list) or len(value)>LIMIT: raise GitHubError('Invalid GitHub collection')
    return value

def fetch_snapshot(repository,fetch=request_json):
    repo=normalize_repo(repository)
    prefix='/repos/'+quote(repo,safe='/')
    web='https://github.com/'+repo
    try:
        commits=collection(fetch(prefix+'/commits?per_page=5'))
        pulls=collection(fetch(prefix+'/pulls?state=all&sort=updated&direction=desc&per_page=5'))
        runs=collection(fetch(prefix+'/actions/runs?per_page=5')['workflow_runs'])
        out=[]
        for c in commits:
            s=sha(c['sha'])
            out.append(dict(title='GitHub commit '+s[:12],body='Commit message (external data):\n'+clean(c['commit']['message'],4000),source=web+'/commit/'+s,sha=s))
        for p in pulls:
            n=number(p['number']); s=sha(p['head']['sha'])
            # Head SHA may belong to a fork. Never equate PR head with main or a tested checkout.
            headrepo=p['head'].get('repo')
            head=clean(headrepo['full_name'],200) if headrepo else 'unavailable'
            body='PR title (external data): '+clean(p['title'],240)+'\nState: '+clean(p['state'],32)+'\nMerged at: '+clean(p.get('merged_at') or 'not recorded',80)+'\nHead repository: '+head+'\nHead SHA: '+s+'\nBase ref: '+clean(p['base']['ref'],200)+'\nPR metadata only; not a CI or acceptance result.'
            out.append(dict(title='GitHub PR #'+str(n),body=body,source=web+'/pull/'+str(n),sha=s))
        for r in runs:
            n=number(r['id']); attempt=number(r['run_attempt']); s=sha(r['head_sha'])
            body='Workflow: '+clean(r['name'],240)+'\nAttempt: '+str(attempt)+'\nStatus: '+clean(r['status'],40)+'\nConclusion: '+clean(r.get('conclusion') or 'not reported',40)+'\nEvent: '+clean(r['event'],40)+'\nHead SHA: '+s+'\nGitHub-reported run metadata; checkout SHA and hardware acceptance not verified.'
            out.append(dict(title='GitHub CI #'+str(n)+' attempt '+str(attempt),body=body,source=web+'/actions/runs/'+str(n)+'/attempts/'+str(attempt),sha=s))
        return out
    except (KeyError,TypeError,AttributeError,IndexError):
        raise GitHubError('Unexpected GitHub response shape') from None


def make_fetcher(token):
    token=validate_token(token)
    def fetch(repository):
        records=fetch_snapshot(repository,partial(request_json,token=token))
        # Never persist an exact configured secret, even if an upstream message echoes it.
        if token:
            for record in records:
                for key in ('title','body','source'):
                    record[key]=record[key].replace(token,'[REDACTED]')
        return records
    return fetch
