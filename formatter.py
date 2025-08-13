from models import GitHubStats

def format_summary(username: str, stats: GitHubStats) -> str:
    summary = f"📊 **GitHub Annual Summary for @{username}** (past 365 days)\n\n"
    summary += f"🚀 **Commits:** {stats.total_commits}\n"
    summary += f"❓ **Issues Opened:** {stats.total_issues}\n"
    summary += f"🔄 **Pull Requests Opened:** {stats.total_prs}\n"
    summary += f"👀 **PR Reviews:** {stats.total_reviews}\n"
    summary += f"🏗️ **Repos Contributed To:** {stats.total_repos_contrib}\n"
    summary += f"📈 **Lines Added (in PRs):** {stats.additions}\n"
    summary += f"📉 **Lines Deleted (in PRs):** {stats.deletions}\n"
    summary += f"📜 **Lines Added (in Commits):** {stats.commit_additions}\n" 
    summary += f"📝 **Lines Deleted (in Commits):** {stats.commit_deletions}\n" 
    summary += f"⭐ **Total Stars on Repos:** {stats.total_stars}\n"
    summary += f"🍴 **Total Forks on Repos:** {stats.total_forks}\n\n"
    summary += "Share this bot! Created by Gleb Kalyta."
    return summary