import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import timedelta

# Constants
TIMEOUT_DURATION = timedelta(seconds=30)
POLL_DURATION = 30  # seconds

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up intents
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True 

# Create a bot instance with a command prefix and the defined intents.
# Using Bot instead of Client to handle commands.
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    """
    Event handler that runs when the bot successfully connects to Discord.
    """
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('Syncing slash commands...')
    try:
        # Synchronize the application commands (slash commands) with Discord.
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    print("-" * 50)

@bot.tree.command(name="votekick", description="Starts a poll to timeout a user for 30 seconds.")
@discord.app_commands.describe(member="The member to vote kick.")
async def votekick(interaction: discord.Interaction, member: discord.Member):
    """
    Slash command to initiate a votekick poll against a member.

    Args:
        interaction (discord.Interaction): The interaction object representing the command invocation.
        member (discord.Member): The member to be timed out.
    """
    # Prevent a user from trying to kick themselves or the bot.
    if member == interaction.user:
        await interaction.response.send_message("You cannot start a votekick against yourself.", ephemeral=True)
        return
    if member == bot.user:
        await interaction.response.send_message("You cannot kick me.", ephemeral=True)
        return
    if member.bot == True:
        await interaction.response.send_message("You cannot votekick a bot.", ephemeral=True)
        return
    
    # Check if the member has a higher role than the bot
    if member.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(f"I don't have the necessary permissions to timeout {member.mention}.", ephemeral=True)

    # Prevent a user from trying to start a votekick against someone who is already timed out.
    if member.is_timed_out():
        await interaction.response.send_message(f"{member.display_name} is already timed out.", ephemeral=True)
        return

    # Check if the bot has permissions to timeout members.
    if not interaction.guild.me.guild_permissions.moderate_members:
        await interaction.response.send_message("I don't have the `Moderate Members` permission to timeout users.", ephemeral=True)
        return
    
    # Defer the initial response to prevent the interaction from timing out
    # while the poll and subsequent logic are processed.
    await interaction.response.defer()

    try:
        # Create the votekick poll and send the message
        poll_question = f"Votekick {member.display_name}"
        poll = discord.Poll(question=poll_question, duration=timedelta(hours=1))
        poll.add_answer(text="Yes", emoji="✅")
        poll.add_answer(text="No", emoji="❌")
        
        poll_message = await interaction.followup.send(
            content=f"**Poll: {poll_question}**\n*This poll will end in 30 seconds. @here*",
            poll=poll,
        )

        print(f"Poll created with ID: {poll_message.id}, against User: {member.id}")

    except Exception as e:
        await interaction.followup.send(f"Failed to create the poll: {e}")
        print(f"Error creating poll: {e}")
        return

    # Wait for the poll to end after 30 seconds
    await asyncio.sleep(POLL_DURATION)
    await poll.end()
    print(f"Poll ({poll_message.id}) has ended.")

    # Get the final poll results
    for options in poll.answers:
        yes_votes = 0
        if options.text == "Yes":
            yes_votes = options.vote_count
            break
    
    # Check if the poll has enough votes to determine a result.
    if poll.total_votes == 0 or poll.total_votes < 2:
        await interaction.followup.send(f"The votekick for {member.mention} failed (not enough votes)")
        print(f"Conclusion: Failed; User: {member.display_name}; Reason: not enough total votes")
        won = False
        return
    else:
        won = (yes_votes / poll.total_votes) > 0.5
    
    # Check if the votekick passed based on the majority of votes.
    if won:
        try:
            # Timeout the member for 30 seconds.
            await member.timeout(TIMEOUT_DURATION, reason="Votekick passed.")
            await interaction.followup.send(f"The votekick for {member.mention} passed.")
            print(f"Conclusion: Passed; User: {member.display_name}")
            
            # log when the timeout ends
            await asyncio.sleep(TIMEOUT_DURATION.total_seconds())
            if not member.is_timed_out():
                print(f"{member.display_name}'s timeout has ended.")
                
        except discord.Forbidden:
            await interaction.followup.send(f"I don't have the necessary permissions to timeout {member.mention}.")
            print(f"Conclusion: Failed; User: {member.display_name}; Reason: bot lacks permissions")
        except Exception as e:
            print(f"Conclusion: Failed; User: {member.display_name}; Reason: {e}")

    else:
        await interaction.followup.send(f"The votekick for {member.mention} has failed.")
        print(f"Conclusion: Failed; User: {member.display_name}; Reason: does not have majority of the votes")

bot.run(TOKEN)