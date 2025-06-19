import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import timedelta

# Define the necessary intents for the bot.
# Guilds and members intents are required to access member information.
load_dotenv()  # Load environment variables from a .env file
TOKEN = os.getenv('DISCORD_TOKEN')  # Get the bot token from environment variables
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

    # Check if the bot has permissions to timeout members.
    if not interaction.guild.me.guild_permissions.moderate_members:
        await interaction.response.send_message("I don't have the `Moderate Members` permission to time out users.", ephemeral=True)
        return
        

    # Create the poll question and options.
    poll_question = f"Votekick {member.display_name}"

    # Defer the initial response to prevent the interaction from timing out
    # while the poll and subsequent logic are processed.
    await interaction.response.defer()

    # Send the poll. Discord polls for bots are created by sending a message.
    # The poll functionality is implicitly handled by Discord's UI.
    # The `duration` is in hours, so we set it to 1 hour but end it after 1 minute.
    try:
        poll = discord.Poll(question=poll_question, duration=timedelta(hours=1))
        
        poll.add_answer(text="Yes", emoji="✅")
        poll.add_answer(text="No", emoji="❌")

        poll_message = await interaction.followup.send(
            content=f"**Poll: {poll_question}**\n*This poll will end in 1 minute.*",
            poll=poll,
        )
        print(f"Poll created with ID: {poll_message.id}")
    except Exception as e:
        await interaction.followup.send(f"Failed to create the poll: {e}")
        print(f"Error creating poll: {e}")
        return

    # Wait for the poll to end (1 minute + a small buffer).
    await asyncio.sleep(5)
    await poll.end()

    while not poll.is_finalized:
        await asyncio.sleep(1)
    
    print("Poll ended.")

    # Fetch the message again to get the final poll results.
    try:
        poll_results = poll.get_answer(poll_message.id)
    except discord.NotFound:
        await interaction.followup.send("Could not find the original poll message.", ephemeral=True)
        print("Poll message not found.")
        return
    
    if poll_results:
        # Check if the "Yes" votes are more than 50% of the total votes.
        if poll_results.text == "Yes":
            try:
                # Timeout the member for 30 seconds.
                await member.timeout(timedelta(seconds=30), reason="Votekick passed.")
                await interaction.followup.send(f"The votekick for {member.mention} passed.")
                print(f"Timed out {member.display_name} for 30 seconds.")
            except discord.Forbidden:
                await interaction.followup.send(f"I don't have the necessary permissions to time out {member.mention}.")
            except Exception as e:
                print(f"An error occurred while trying to time out the user: {e}")
        else:
            await interaction.followup.send(f"The votekick for {member.mention} has failed.")
    else:
        print("Could not retrieve poll results.")

bot.run(TOKEN)