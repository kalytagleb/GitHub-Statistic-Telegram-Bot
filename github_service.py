import httpx
import datetime
from typing import Optional
from models import GitHubStats
from config import GITHUB_TOKEN
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitHubService:
    BASE_URL = "https://api.github.com/graphql"
    REST_BASE_URL = "https://api.github.com"

    async def fetch_annual_stats(self, username: str) -> Optional[GitHubStats]:
        logger.info(f"Fetching stats for username: {username}")
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
                    commitContributionsByRepository(maxRepositories: 100) {
                        repository {
                            nameWithOwner
                        }
                        contributions(first: 100) {
                            edges {
                                node {
                                    commitCount
                                    occurredAt
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

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                logger.info("Sending GraphQL request")
                response = await client.post(self.BASE_URL, json={"query": query, "variables": variables}, headers=headers)

                if response.status_code != 200:
                    logger.error(f"HTTP error: {response.status_code} - {response.text}")
                    return None
        
                data = response.json()
                logger.info(f"API response: {data}")
                if "errors" in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    return None
        
                user_data = data.get("data", {}).get("user")
                if not user_data:
                    logger.error(f"User not found or no data returned for username: {username}")
                    return None
        
                logger.info("Successfully fetched user data")
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
                    additions=additions_pr,
                    deletions=deletions_pr, 
                    total_stars=total_stars,
                    total_forks=total_forks,
                    commit_additions=commit_additions,
                    commit_deletions=commit_deletions
                )
            
            except httpx.ReadTimeout as e:
                logger.error(f"ReadTimeout error for username {username}: {str(e)}")
                return None
    
    async def _fetch_commit_lines(self, client: httpx.AsyncClient, username: str, from_date: datetime.datetime) -> tuple[int, int]:
        additions = 0
        deletions = 0
        headers = {"Accept": "application/vnd.github.v3+json"}

        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        logger.info(f"Fetching repos for {username}")
        try:
            repos = await client.get(
                f"{self.REST_BASE_URL}/users/{username}/repos",
                headers=headers,
                params={"per_page": 100, "sort": "updated"}
            )
            if repos.status_code != 200:
                logger.error(f"Failed to fetch repos: {repos.status_code} - {repos.text}")
                return additions, deletions

            repo_list = repos.json()
            for repo in repo_list:
                repo_name = repo["full_name"]
                logger.info(f"Fetching commits for {repo_name}")
                commits = await client.get(
                    f"{self.REST_BASE_URL}/repos/{repo_name}/commits",
                    headers=headers,
                    params={"author": username, "since": from_date.isoformat(), "per_page": 100}
                )
                if commits.status_code != 200:
                    logger.warning(f"Failed to fetch commits for {repo_name}: {commits.status_code}")
                    continue

                for commit in commits.json():
                    commit_sha = commit["sha"]
                    logger.info(f"Fetching commit details for {commit_sha}")
                    commit_details = await client.get(
                        f"{self.REST_BASE_URL}/repos/{repo_name}/commits/{commit_sha}",
                        headers=headers
                    )
                    if commit_details.status_code == 200:
                        stats = commit_details.json().get("stats", {})
                        additions += stats.get("additions", 0)
                        deletions += stats.get("deletions", 0)
                    else:
                        logger.warning(f"Failed to fetch commit details for {commit_sha}: {commit_details.status_code}")
                        
        except httpx.ReadTimeout as e:
            logger.error(f"ReadTimeout in _fetch_commit_lines for {username}: {str(e)}")
            return additions, deletions

        return additions, deletions