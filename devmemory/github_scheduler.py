"""Opt-in polling, shared rate gate and bounded persistent attempt history."""
import time, sqlite3
from github_sync import GitHubError, GitHubRateLimit, fetch_snapshot

class SyncBusy(Exception): pass

class SyncDeferred(Exception):
    def __init__(self,seconds):
        self.seconds=seconds
        super().__init__('GitHub sync cooldown; retry in '+str(seconds)+' seconds')

def run_sync(store,lock,project,automatic=False,fetcher=fetch_snapshot,clock=time.time):
    if not lock.acquire(blocking=False):
        raise SyncBusy()
    try:
        job=store.begin_github(project,automatic,int(clock()))
        if job is None: return None
        try:
            result=store.sync_github(project,fetcher)
        except GitHubError as e:
            store.finish_github(job,int(clock()),error=str(e),rate_limited=isinstance(e,GitHubRateLimit))
            raise
        except (ValueError,sqlite3.Error):
            store.finish_github(job,int(clock()),error='Local sync failed')
            raise
        except Exception:
            store.finish_github(job,int(clock()),error='Unexpected sync failure')
            raise GitHubError('Unexpected sync failure') from None
        store.finish_github(job,int(clock()),result=result)
        return result
    finally:
        lock.release()

def scheduler_tick(store,lock,fetcher=fetch_snapshot,clock=time.time):
    project=store.due_github(int(clock()))
    if not project: return None
    try:
        return run_sync(store,lock,project,automatic=True,fetcher=fetcher,clock=clock)
    except (SyncBusy,SyncDeferred,GitHubError,ValueError,sqlite3.Error):
        return None

def scheduler_loop(store,lock,stop,fetcher=fetch_snapshot):
    while not stop.wait(30):
        try: scheduler_tick(store,lock,fetcher=fetcher)
        except sqlite3.Error:
            # Never log repository content or secrets. Retry at the next tick.
            pass
