import httpx
import datetime
from typing import Optional
from models import GitHubStats
from config import GITHUB_TOKEN

class GitHubService:
    BASE_URL = "https://api.github.com/graphql"
    REST_BASE_URL = "https://api.github.com"

    async def fetch_annual_stats(self, username: str) -> Optional[GitHubStats]:
        to_date = datetime.datetime.now(datetime.timezone.utc)
        from_date = to_date - datetime.timedelta(days=365)
        from_str = from_date.isoformat()
        to_str = to_date.isoformat()

        query = """ 
        query ($username: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $username) {
                contributionsCollection(from: $from, to: $to) {
                    totalCommitContributions
                    totalIssueContributions
                    totalPullRequestContributions
                    totalPullRequestReviewContributions
                    totalRepositoriesWithContributedCommits
                    pullRequestContributions(first: 100) {
                        edges {
                            node {
                                pullRequest {
                                    additions
                                    deletions
                                }
                            }
                        }
                    }
                    commitContributionsByRepository(first: 100) {
                        edges {
                            node {
                                repository {
                                    nameWithOwner
                                }
                                contributions(first: 100) {
                                    edges {
                                        node {
                                            commitCount
                                            occuredAt
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                repositories(first: 100, ownerAffiliations: [OWNER]) {
                    edges {
                        node {
                            stargazerCount
                            forkCount
                        }
                    }
                }
            }
        }
        """

        variables = {"username": username, "from": from_str, "to": to_str}

        headers = {"Content-Type": "application/json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        async with httpx.AsyncClient() as client:
            response = await client.post(self.BASE_URL, json={"query": query, "variables": variables}, headers=headers)

        if response.status_code != 200:
            return None
        
        data = response.json()
        if "errors" in data:
            return None
        
        user_data = data.get("data", {}).get("user")
        if not user_data:
            return None
        
        contrib = user_data["contributionsCollection"]
        repos = user_data["repositories"]["edges"]

        pr_contribs = contrib.get("pullRequestContributions", {}).get("edges", [])
        additions_pr = sum(edge["node"]["pullRequest"]["additions"] for edge in pr_contribs)
        deletions_pr = sum(edge["node"]["pullRequest"]["deletions"] for edge in pr_contribs)

        total_stars = sum(node["node"]["stargazerCount"] for node in repos)
        total_forks = sum(node["node"]["forkCount"] for node in repos)

        commit_additions, commit_deletions = await self._fetch_commit_lines(client, username, from_date)

        return GitHubStats(
            total_commits=contrib.get("totalCommitContributions", 0),
            total_issues=contrib.get("totalIssueContributions", 0),
            total_prs=contrib.get("totalPullRequestContributions", 0),
            total_reviews=contrib.get("totalPullRequestReviewContributions", 0),
            total_repos_contrib=contrib.get("totalRepositoriesWithContributedCommits", 0),
            additions=additions_pr, # Lines from PRs
            deletions=deletions_pr, # Lines from PRs
            total_stars=total_stars,
            total_forks=total_forks,
            commit_additions=commit_additions,
            commit_deletions=commit_deletions
        )
    
    async def _fetch_commit_lines(self, client: httpx.AsyncClient, username: str, from_date: datetime.datetime) -> 