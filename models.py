from pydantic import BaseModel
from typing import Optional

class GitHubStats(BaseModel):
    total_commits: int = 0
    total_issues: int = 0
    total_prs: int = 0
    total_reviews: int = 0
    total_repos_contrib: int = 0
    additions: int = 0
    deletions: int = 0
    total_stars: int = 0
    total_forks: int = 0
    commit_additions: int = 0
    commit_deletions: int = 0