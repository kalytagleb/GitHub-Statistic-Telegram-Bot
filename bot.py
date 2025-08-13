from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from github_service import GitHubService
from formatter import format_summary

github_service = GitHubService()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a GitHub username for an annual contribution summary.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    if not username:
        await update.message.reply_text("Please send a valid GitHub username.")
        return
    
    stats = await github_service.fetch_annual_stats(username)
    if not stats:
        await update.message.reply_text("Could not fetch data. Check the username or try later.")
        return
    
    summary = format_summary(username, stats)
    await update.message.reply_text(summary, parse_mode='Markdown')