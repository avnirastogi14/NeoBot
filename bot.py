import discord
from discord.ext import commands
import asyncio
from pymongo import MongoClient
import re
from difflib import SequenceMatcher
import os
from dotenv import load_dotenv
import traceback
import sys

# Load environment variables
load_dotenv(dotenv_path='C:/Users/Hrida/OneDrive/Documents/Desktop/Avni_College/foss_p/Model/data.env')

# Define debug_print at the top
def debug_print(message):
    """Print debug messages if DEBUG is True"""
    global DEBUG
    if DEBUG:
        print(f"[DEBUG] {message}")

# Set up intents and bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    description="A simple team management bot with NLP",
    help_command=None
)

# Debug flag and MongoDB setup
DEBUG = True
try:
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    debug_print(f"Attempting MongoDB connection with URI: {mongo_uri}")
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()
    db = mongo_client["discordbot"]
    roles_collection = db["roles"]
    debug_print("Connected to MongoDB successfully")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    traceback.print_exc()
    print("Continuing without database functionality...")
    roles_collection = None

# NLP setup - Simplified to avoid issues
nlp_enabled = False
intent_recognition_pipeline = None

# Enhanced command mapping with more variations
command_mapping = {
    "add_team": {"commands": ["add team", "create team", "new team", "make team"], 
                "keywords": ["add", "create", "new", "make", "team"], 
                "context": "Create a new team."},
    "add_member": {"commands": ["add member", "add user", "include member"], 
                  "keywords": ["add", "include", "member", "user"], 
                  "context": "Add a member to a team."},
    "remove_member": {"commands": ["remove member", "kick member", "delete member"], 
                     "keywords": ["remove", "kick", "delete", "member"], 
                     "context": "Remove a member from a team."},
    "update_name": {"commands": ["update name", "rename team", "change name", "update team name"], 
                   "keywords": ["update", "rename", "change", "name", "team"], 
                   "context": "Update a team name."},
    "update_repo": {"commands": ["update repo", "set repo", "change repo", "update repository"], 
                   "keywords": ["update", "set", "change", "repo", "repository"], 
                   "context": "Update a team's GitHub repo."},
    "update_role": {"commands": ["update role", "set role to", "change role", "update role", "set role"], 
                   "keywords": ["update", "set", "change", "repo", "repository"], 
                   "context": "Update a team's GitHub repo."},
    "show_info": {"commands": ["show info", "view info", "team info", "display info"], 
                 "keywords": ["show", "view", "display", "info", "information"], 
                 "context": "Show team information."},
    "set_status": {"commands": ["set status", "update status", "change status"], 
                  "keywords": ["set", "update", "change", "status"], 
                  "context": "Set a team's status."},
    "delete_team": {"keywords": ["delete", "remove", "team"],
                    "commands": ["delete team", "remove team", "delete entire team", "remove entire team"]
                },
}

def calculate_string_similarity(str1, str2):
    similarity = SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    debug_print(f"String similarity between '{str1}' and '{str2}': {similarity}")
    return similarity

def calculate_semantic_similarity(text1, text2):
    # Fallback to string similarity for simplicity and reliability
    return calculate_string_similarity(text1, text2)

def get_best_command(user_input):
    debug_print(f"Finding best command match for: '{user_input}'")
    command_scores = []
    user_words = set(user_input.lower().split())  # Splitting input into words
    debug_print(f"User words: {user_words}")

    for command_key, command_data in command_mapping.items():
        keywords = set(command_data["keywords"])  # Keywords to match
        keyword_matches = len(keywords.intersection(user_words))  # Count keyword matches
        keyword_score = keyword_matches / len(keywords) if keywords else 0  # Score based on keywords
        debug_print(f"Command: {command_key}, Keyword matches: {keyword_matches}, Keyword score: {keyword_score}")
        
        # Check for command similarities based on string similarity calculation
        command_similarities = [calculate_string_similarity(user_input, cmd) for cmd in command_data["commands"]]
        context_score = 0.5  # You can tweak this value as needed
        
        # Get the best similarity score
        command_score = max(command_similarities) if command_similarities else 0
        debug_print(f"Command: {command_key}, Context score: {context_score}, Best command similarity: {command_score}")
        
        # Calculate the final score combining keyword match, command similarity, and context score
        final_score = (0.4 * keyword_score) + (0.3 * context_score) + (0.3 * command_score)
        command_scores.append({"command": command_key, "score": final_score})
        debug_print(f"Command: {command_key}, Final score: {final_score}")
    
    # Sort commands by score and return the best match
    command_scores.sort(key=lambda x: x["score"], reverse=True)
    best = command_scores[0] if command_scores and command_scores[0]["score"] > 0.1 else None
    debug_print(f"Best command: {best}")
    return best

def extract_command_args(user_input):
    debug_print(f"Extracting arguments from: '{user_input}'")
    args = {}
    STOP_WORDS = {"add", "team", "new", "create", "to", "for", "the", "with", "and", "update", "role", "repo", "repository", "status", "show", "info"}
    user_input_lower = user_input.lower()

    # Enhanced role pattern matching
    role_patterns = [
        r"\brole\s+(\w+)", 
        r"\bfor\s+role\s+(\w+)",
        r"\bfrom\s+role\s+(\w+)",
        r"\bto\s+role\s+(\w+)"
    ]
    for pattern in role_patterns:
        role_match = re.search(pattern, user_input, re.IGNORECASE)
        if role_match and role_match.group(1).lower() not in STOP_WORDS:
            args["role"] = role_match.group(1).lower()
            debug_print(f"Found role: {args['role']}")
            break
    else:
        args["role"] = None

    # Enhanced team name pattern matching
    team_patterns = [
        r"\bteam\s+(\w+)", 
        r"\bname\s+(\w+)",
        r"\bteam\s+name\s+(\w+)",
        r"\bto\s+(\w+)"
    ]
    for pattern in team_patterns:
        team_match = re.search(pattern, user_input, re.IGNORECASE)
        if team_match and team_match.group(1).lower() not in STOP_WORDS:
            args["team_name"] = team_match.group(1).capitalize()
            debug_print(f"Found team name: {args['team_name']}")
            break
    else:
        args["team_name"] = None

    # Enhanced repo pattern matching
    repo_patterns = [
        r"(https?://github\.com/[^\s]+)",
        r"(github\.com/[^\s]+)"
    ]
    for pattern in repo_patterns:
        repo_match = re.search(pattern, user_input, re.IGNORECASE)
        if repo_match:
            repo_url = repo_match.group(1)
            if not repo_url.startswith("http"):
                repo_url = "https://" + repo_url
            args["project_repo"] = repo_url
            debug_print(f"Found project repo: {args['project_repo']}")
            break
    else:
        args["project_repo"] = None

    # Enhanced member pattern matching
    member_patterns = [
        r"\bmember\s+(\w+)", 
        r"\buser\s+(\w+)",
        r"\bperson\s+(\w+)"
    ]
    args["team_members"] = []
    for pattern in member_patterns:
        members_match = re.search(pattern, user_input, re.IGNORECASE)
        if members_match:
            args["team_members"] = [members_match.group(1).capitalize()]
            debug_print(f"Found team member: {args['team_members']}")
            break

    # Enhanced status pattern matching
    status_patterns = [
        r"\bstatus\s+(\w+)",
        r"\bto\s+(\w+)\s+status"
    ]
    for pattern in status_patterns:
        status_match = re.search(pattern, user_input_lower)
        if status_match:
            args["status"] = status_match.group(1).capitalize()
            debug_print(f"Found status: {args['status']}")
            break
    else:
        args["status"] = None

    debug_print(f"Extracted arguments: {args}")
    return args

# Enhanced ask_user function with validation
async def ask_user(ctx, question, validation_func=None, error_message=None):
    try:
        debug_print(f"Asking user: '{question}'")
        await ctx.send(question)
        
        attempts = 0
        max_attempts = 3
        
        while attempts < max_attempts:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            try:
                msg = await bot.wait_for("message", check=check, timeout=30.0)
                response = msg.content.strip()
                debug_print(f"User responded: '{response}'")
                
                # If validation function is provided, check the response
                if validation_func is None or validation_func(response):
                    return response
                else:
                    attempts += 1
                    if attempts < max_attempts:
                        await ctx.send(error_message or "❌ Invalid input. Please try again.")
                    else:
                        await ctx.send("❌ Too many invalid attempts. Command cancelled.")
                        return None
            except asyncio.TimeoutError:
                debug_print("User response timed out")
                await ctx.send("⏰ Timeout! Please try again.")
                return None
                
    except Exception as e:
        debug_print(f"Error in ask_user: {e}")
        await ctx.send("❌ Error processing your input. Try again.")
        return None

# Validation functions for different input types
def validate_role(input_str):
    STOP_WORDS = {"add", "team", "new", "create", "to", "for", "the", "with", "and", "update", "role", "repo", "repository", "status", "show", "info"}
    return input_str and input_str.lower() not in STOP_WORDS

def validate_team_name(input_str):
    STOP_WORDS = {"add", "team", "new", "create", "to", "for", "the", "with", "and", "update", "role", "repo", "repository", "status", "show", "info"}
    return input_str and input_str.lower() not in STOP_WORDS

def validate_repo_url(input_str):
    return input_str and (input_str.startswith("http") or input_str.startswith("github.com"))

def validate_member_name(input_str):
    STOP_WORDS = {"add", "team", "new", "create", "to", "for", "the", "with", "and", "update", "role", "repo", "repository", "status", "show", "info"}
    return input_str and input_str.lower() not in STOP_WORDS

def validate_status(input_str):
    return input_str and len(input_str) > 1

@bot.event
async def on_ready():
    debug_print(f"Bot is ready. Logged in as {bot.user}")
    print(f"Bot is ready. Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    debug_print(f"Received message: '{message.content}' from {message.author}")
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    debug_print(f"Command error: {error}")
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❓ Command not found. Use `!help` for options.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: {error.param}")
    else:
        print(f"Error: {error}")
        traceback.print_exc()
        await ctx.send(f"❌ An error occurred: {str(error)[:100]}...")

@bot.command(name="cmd")
async def handle_natural_command(ctx, *, message: str = None):
    try:
        debug_print(f"Command received: '{message}' from {ctx.author}")

        if not message or not message.strip():
            await ctx.send("❓ Please provide a command. Use `!help` for options.")
            return

        debug_print(f"Processing command: '{message}'")
        # Get command intent
        best_match = get_best_command(message)
        if not best_match:
            await ctx.send("🤔 I didn't understand your command. Try using one of the formats shown in `!help`. For example: `!cmd add team`")
            return

        intent = best_match["command"]
        args = extract_command_args(message)
        debug_print(f"Identified intent: {intent} with args: {args}")

        # Extract arguments
        role = args.get("role")
        team_name = args.get("team_name")
        project_repo = args.get("project_repo")
        team_members = args.get("team_members", [])
        status = args.get("status")

        # Check if MongoDB is available
        if roles_collection is None:
            await ctx.send("❌ Database connection is not available. Please check server logs.")
            return

        # Handle different commands
        if intent == "add_team":
            # Ask for missing information
            if not role:
                role = await ask_user(ctx, 
                                     "What's the role name for the new team? (e.g., frontend)",
                                     validate_role,
                                     "❌ Please provide a valid role name (not a command word).")
                if not role:
                    return
            if not team_name:
                team_name = await ask_user(ctx, 
                                          "What's the team name? (e.g., Alpha)",
                                          validate_team_name,
                                          "❌ Please provide a valid team name.")
                if not team_name:
                    return
            if not project_repo:
                project_repo = await ask_user(ctx, 
                                             "What's the GitHub repo? (e.g., https://github.com/org/repo)",
                                             validate_repo_url,
                                             "❌ Please provide a valid GitHub URL (starting with https://github.com/).")
                if not project_repo:
                    return
                
                # Add https:// if missing
                if not project_repo.startswith("http"):
                    project_repo = "https://" + project_repo

            # Check if team already exists
            existing_team = roles_collection.find_one({"role": role.lower()})
            if existing_team:
                await ctx.send(f"❌ Role **{role}** already exists.")
                return

            # Create new team
            new_team = {"role": role.lower(), "team_name": team_name, "project_repo": project_repo, "team_members": [], "status": "Not started"}
            roles_collection.insert_one(new_team)
            await ctx.send(f"✅ Team **{team_name}** created for role **{role}**!")

        elif intent == "add_member":
            # Ask for missing information
            if not role:
                role = await ask_user(ctx, 
                                     "Which role to add a member to? (e.g., frontend)",
                                     validate_role,
                                     "❌ Please provide a valid role name.")
                if not role:
                    return
            if not team_members or len(team_members) == 0:
                member = await ask_user(ctx, 
                                       "Who's the new member? (e.g., Alice)",
                                       validate_member_name,
                                       "❌ Please provide a valid member name.")
                if not member:
                    return
                team_members = [member.capitalize()]

            # Check if role exists (case-insensitive)
            role_exists = roles_collection.find_one({"role": role.lower()})
            if not role_exists:
                await ctx.send(f"❌ No role **{role}** found.")
                return


            # Add member
            roles_collection.update_one({"role": role.lower()}, {"$addToSet": {"team_members": {"$each": team_members}}})
            await ctx.send(f"✅ Added **{team_members[0]}** to **{role}**!")

        elif intent == "remove_member":
            # Ask for missing information
            if not role:
                role = await ask_user(ctx, 
                                     "Which role to remove a member from? (e.g., frontend)",
                                     validate_role,
                                     "❌ Please provide a valid role name.")
                if not role:
                    return
            if not team_members or len(team_members) == 0:
                member = await ask_user(ctx, 
                                       "Who to remove? (e.g., Alice)",
                                       validate_member_name,
                                       "❌ Please provide a valid member name.")
                if not member:
                    return
                team_members = [member.capitalize()]

            # Check if role exists
            role_exists = roles_collection.find_one({"role": role.lower()})
            if not role_exists:
                await ctx.send(f"❌ No role **{role}** found.")
                return

            # Remove member
            roles_collection.update_one({"role": role.lower()}, {"$pullAll": {"team_members": team_members}})
            await ctx.send(f"✅ Removed **{team_members[0]}** from **{role}**!")

        elif intent == "delete_team":
            # Handle delete team command
            if not role:
                role = await ask_user(ctx, 
                                     "Which team's data do you want to delete? (e.g., frontend)",
                                     validate_role,
                                     "❌ Please provide a valid role name.")
                if not role:
                    return

            # Check if role exists
            role_exists = roles_collection.find_one({"role": role.lower()})
            if not role_exists:
                await ctx.send(f"❌ No role **{role}** found.")
                return

            # Delete the entire team
            roles_collection.delete_one({"role": role.lower()})
            await ctx.send(f"✅ Team **{role}** and all its data have been deleted!")

        elif intent == "update_name":
            # Ask for missing information
            if not role:
                role = await ask_user(ctx, 
                                     "Which role's name to update? (e.g., frontend)",
                                     validate_role,
                                     "❌ Please provide a valid role name.")
                if not role:
                    return
            if not team_name:
                team_name = await ask_user(ctx, 
                                          "What's the new team name? (e.g., Beta)",
                                          validate_team_name,
                                          "❌ Please provide a valid team name.")
                if not team_name:
                    return

            # Check if role exists
            role_exists = roles_collection.find_one({"role": role.lower()})
            if not role_exists:
                await ctx.send(f"❌ No role **{role}** found.")
                return

            # Update team name
            result = roles_collection.update_one({"role": role.lower()}, {"$set": {"team_name": team_name}})
            debug_print(f"Update result: {result.modified_count} documents updated.")
            if result.modified_count == 0:
                await ctx.send(f"❌ No changes were made to the role **{role}**.")
            else:
                await ctx.send(f"✅ Team name for **{role}** updated to **{team_name}**! Now, you can add new members or update the repo with `!cmd update repo`.")

        elif intent == "update_repo":
            # Ask for missing information
            if not role:
                role = await ask_user(ctx, 
                                     "Which role's repo to update? (e.g., frontend)",
                                     validate_role,
                                     "❌ Please provide a valid role name.")
                if not role:
                    return
            if not project_repo:
                project_repo = await ask_user(ctx, 
                                             "What's the new GitHub repo? (e.g., https://github.com/org/repo)",
                                             validate_repo_url,
                                             "❌ Please provide a valid GitHub URL.")
                if not project_repo:
                    return
                
                # Add https:// if missing
                if not project_repo.startswith("http"):
                    project_repo = "https://" + project_repo

            # Check if role exists
            role_exists = roles_collection.find_one({"role": role.lower()})
            if not role_exists:
                await ctx.send(f"❌ No role **{role}** found.")
                return

            # Update repo
            roles_collection.update_one({"role": role.lower()}, {"$set": {"project_repo": project_repo}})
            await ctx.send(f"✅ Repo for **{role}** updated to {project_repo}!")

        elif intent == "update_role":
            # Ask for the role name
            if not role:
                role = await ask_user(ctx, 
                                    "Which role to update? (e.g., frontend)", 
                                    validate_role, 
                                    "❌ Please provide a valid role name.")
                if not role:
                    return

            # Check if the role exists in MongoDB
            role_exists = roles_collection.find_one({"role": role.lower()})
            if not role_exists:
                await ctx.send(f"❌ No role **{role}** found.")
                return

            # Ask for the new role name (or the updated name)
            new_role_name = await ask_user(ctx, 
                                        "What's the new role name? (e.g., backend)", 
                                        validate_role, 
                                        "❌ Please provide a valid role name.")
            if not new_role_name:
                return

            # Update the role name in the MongoDB database
            roles_collection.update_one(
                {"role": role.lower()},
                {"$set": {"role": new_role_name.lower()}}
            )

            await ctx.send(f"✅ Role **{role}** updated to **{new_role_name}**!")


        elif intent == "show_info":
            # Ask for missing information
            if not role:
                role = await ask_user(ctx, 
                                     "Which role's info to show? (e.g., frontend)",
                                     validate_role,
                                     "❌ Please provide a valid role name.")
                if not role:
                    return

            # Get role data
            role_data = roles_collection.find_one({"role": role.lower()})
            if not role_data:
                await ctx.send(f"❌ No role **{role}** found.")
                return

            # Display team info
            members = ", ".join(role_data.get("team_members", [])) or "None"
            await ctx.send(f"**Info for {role}**:\nName: {role_data['team_name']}\nRepo: {role_data.get('project_repo', 'None')}\nMembers: {members}\nStatus: {role_data.get('status', 'Not started')}")

        elif intent == "set_status":
            # Ask for missing information
            if not role:
                role = await ask_user(ctx, 
                                     "Which role's status to update? (e.g., frontend)",
                                     validate_role,
                                     "❌ Please provide a valid role name.")
                if not role:
                    return
            if not status:
                status = await ask_user(ctx, 
                                       "What's the new status? (e.g., In Progress)",
                                       validate_status,
                                       "❌ Please provide a valid status.")
                if not status:
                    return

            # Check if role exists
            role_exists = roles_collection.find_one({"role": role.lower()})
            if not role_exists:
                await ctx.send(f"❌ No role **{role}** found.")
                return

            # Update status
            roles_collection.update_one({"role": role.lower()}, {"$set": {"status": status.capitalize()}})
            await ctx.send(f"✅ Status for **{role}** updated to **{status}**!")
        else:
            await ctx.send("❌ Command not recognized. Use `!help` for available commands.")

    except Exception as e:
        debug_print(f"Critical failure in handle_natural_command: {e}")
        traceback.print_exc()
        await ctx.send(f"❌ Something went wrong: {str(e)[:50]}... Please try again with a simpler command.")

@bot.command(name="help")
async def custom_help_command(ctx):
    debug_print(f"Help command requested by {ctx.author}")
    help_text = (
        "👋 **Simple Team Bot Help**\n"
        "Use `!cmd` with one task at a time. Examples:\n"
        "- `!cmd add team` - Create a new team (will ask for role and repo).\n"
        "- `!cmd add member` - Add a member to a team (will ask for role and name).\n"
        "- `!cmd remove member` - Remove a member from a team (will ask for role and name).\n"
        "- `!cmd update name` - Rename a team (will ask for role and new name).\n"
        "- `!cmd update repo` - Update a team's GitHub repo (will ask for role and URL).\n"
        "- `!cmd show info` - View team details (will ask for role).\n"
        "- `!cmd set status` - Set a team's status (will ask for role and status).\n"
        "💡 Tip: Keep commands short and specific. I'll prompt for missing details!"
    )
    await ctx.send(help_text)

@bot.command(name="test")
async def test_command(ctx):
    debug_print(f"Test command executed by {ctx.author}")
    await ctx.send("✅ I'm working! Try `!cmd` or `!help`.")

@bot.command(name="debug")
async def toggle_debug(ctx):
    global DEBUG
    DEBUG = not DEBUG
    debug_print(f"Debug mode toggled to {DEBUG} by {ctx.author}")
    await ctx.send(f"🛠️ Debug mode {'enabled' if DEBUG else 'disabled'}.")

@bot.command(name="update team")
async def update_team(ctx, *, message: str = None):
    if message:
        await handle_natural_command(ctx, message=message)
    else:
        await ctx.send("❓ Please specify the full team update details.")

if __name__ == "__main__":
    try:
        debug_print("Starting bot...")
        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            print("Error: DISCORD_BOT_TOKEN not found in data.env. Please set it and restart.")
            exit(1)
        debug_print(f"Bot token loaded: {token[:4]}...{token[-4:]}")
        bot.run(token)
    except Exception as e:
        print(f"Fatal error starting bot: {e}")
        traceback.print_exc()