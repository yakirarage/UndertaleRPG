import disnake
import typing
import random

from utility.constants import CColors, EmbedColors, Links, Emotes

tips = [
    "You can use the `/help` command to see a list of all available commands.",
    "You can use the `/invite` command to invite the bot to your server.",
    "You can use the `/stats` command to see your current stats.",
    "Tip: The /use command allows you to use or equip an item from your inventory.",
    "You can use the `/equip` command to equip a weapon or armor from your inventory.",
    "You can use the `/unequip` command to unequip your current weapon or armor.",
    "You can use the `/fight` command to start a battle with a monster.",
    "You can use the `/run` command to run away from a battle.",
]

async def send_tip(inter: disnake.MessageInteraction):
    """Send a random tip to the user."""
    tip = random.choice(tips)
    return(tip)