import disnake
import typing
import random

from utility.constants import CColors, EmbedColors, Links, Emotes
from disnake.ui import Button
from functions.tips import send_tip


class CratesBTN(disnake.ui.View):
    def __init__(self, inter, crates: typing.List[str]) -> None:
        super().__init__(timeout=None)

        async def shared_callback(inter: disnake.MessageInteraction) -> None:
            await inter.response.defer()

            if inter.author.id != int(inter.data["custom_id"].split("-")[0]):
                embed = disnake.Embed(
                    title=f"{Emotes.ERROR} You can't do this.",
                    description="Want to open your own crates?\nCheck out `/crates`",
                    color=EmbedColors.RED,
                )
                return await inter.send(embed=embed, ephemeral=True)
            await open_crate(inter, inter.author, inter.data["custom_id"].split("-")[1])

        for crate in crates:
            crate_name = crate.split("_")[0].capitalize()
            if crates[crate] <= 0:
                button = Button(label=f"{crate_name}: {crates[crate]}", style=disnake.ButtonStyle.gray, disabled=True)
            else:
                button = Button(label=f"{crate_name}: {crates[crate]}", style=disnake.ButtonStyle.gray, custom_id=f"{inter.author.id}-{crate}")
            button.callback = shared_callback
            self.add_item(button)


async def get_crates(inter, player):
    """
    Gets the crates of the player.

    Parameters:
    - inter (disnake.ApplicationCommandInteraction): The interaction.
    - player (typing.Union[disnake.Member, disnake.User]): The player for whom to get crates.

    Returns:
    - dict: The crates of the player.
    """
    data = await inter.bot.players.find_one({"_id": player.id})
    if not data:
        return None

    tip = await send_tip(inter)
    file = disnake.File("./images/crates/ordinary_crate.png", filename="ordinary_crate.png")
    crates = data["crates"]
    embed = disnake.Embed(
        title=f"{player.name}'s crates",
        description=f"""
        You can earn crates in a number of different ways. Explore our different commands and features to find out how!

        **Ordinary:** `{crates["ordinary_crate"]}`
        **Unusual:** `{crates["unusual_crate"]}`
        **Strange:** `{crates["strange_crate"]}`
        **Mysterious:** `{crates["mysterious_crate"]}`
        **Legendary:** `{crates["legendary_crate"]}`
    """,
        color=EmbedColors.YELLOW,
    )
    embed.set_footer(text=f"{tip}")
    embed.set_thumbnail(url="attachment://ordinary_crate.png")

    view = CratesBTN(inter, crates)
    await inter.send(file=file, embed=embed, view=view)
    return data["crates"]


async def open_crate(inter, player, crate: str):
    """
    Opens a crate for the player.

    Parameters:
    - inter (disnake.ApplicationCommandInteraction): The interaction.
    - player (typing.Union[disnake.Member, disnnake.User]): The player for whom to open the crate.
    - crate (str): The crate to open.

    Returns:
    - dict: The updated player data.
    """
    crates_data = await inter.bot.data.find_one({"_id": "crates"})
    player_data = await inter.bot.players.find_one({"_id": player.id})
    if not player_data:
        return None

    if player_data["crates"][crate] <= 0:
        return None

    crate_name = crate.split("_")[0].capitalize()
    crate_data = crates_data[crate]

    gold_gained = random.randint(crate_data["gold_min"], crate_data["gold_max"])
    item_gained = random.choice(crate_data["loot"])

    updated_crate = player_data["crates"][crate] - 1
    updated_gold = player_data["gold"] + gold_gained
    updated_inventory = []
    for i in player_data["inventory"]:
        updated_inventory.append(i)
    updated_inventory.append(item_gained)

    updated_crates = player_data["crates"]
    updated_crates[crate] = updated_crate
    info = {"gold": updated_gold, "inventory": updated_inventory, "crates": updated_crates}
    await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})

    embed = disnake.Embed(
        title=f"{player.name} opened an {crate_name} crate!",
        description=f"""
        *{crate_data["message"]}*

        **Gold:** `{gold_gained}`
        **Items:** `{item_gained}`
        """,
        color=EmbedColors.GREEN,
    )
    embed.set_thumbnail(url="attachment://ordinary_crate.png")
    await inter.message.edit(embed=embed, view=None)

    await get_crates(inter, player)
    return