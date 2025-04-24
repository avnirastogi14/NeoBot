# 🤖 NeoBot — AI-Powered Discord Server Manager

NeoBot is a smart Discord bot that uses **natural language processing (NLP)** to understand user input and automate role-based tasks in a Discord server. It's built with a focus on simplicity, flexibility, and AI-driven intent recognition — a modern alternative to Carl-bot.

---

## 🔧 Key Features

- 🧠 **Intent Recognition**: Uses a fine-tuned DistilBERT model to identify user intent from plain English.
- 💬 **Natural Language Commands**: Say goodbye to rigid command syntax — just type what you mean.
- 🗃️ **MongoDB Integration**: Stores and retrieves team role data, GitHub repo links, and status updates.
- 📘 **Command Mapping**: Supports intelligent fallback to the closest matching command using multiple similarity checks.

---


---

## 🧠 Supported Commands (via Natural Language)

| Command         | Description                                       |
|----------------|---------------------------------------------------|
| `addroledata`  | Add or update GitHub repository info for a role   |
| `showroledata` | View GitHub repo and status for a specific role   |
| `setstatus`    | Update the project status for a team/role         |

Examples:
- `"Add a GitHub repo for team Echo with users Max, Leo, and Ava"`
- `"What’s the repo linked to role Design?"`
- `"Update the milestone for Developers to completed"`

---

## 🛠️ Setup Instructions

### 1. Clone the Repository
```
git clone https://github.com/your-username/NeoBot.git
cd NeoBot
```
2. Install Dependencies
```pip install -r requirements.txt```
3. Configure Environment
Set your MongoDB URI and Discord token securely in a .env file:
```
MONGODB_URI=your_mongodb_uri
DISCORD_TOKEN=your_discord_token
```
Or, update the values directly in bot.py and intent_engine.py (not recommended for production).

---

##📦 Dependencies
- transformers
- torch
- pymongo
- discord.py (if using bot integration)
