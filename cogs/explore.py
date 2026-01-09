import asyncio
import random
from datetime import datetime

import disnake
import humanize
from disnake.ext import commands
from main import UndertaleBot

from utility.dataIO import fileIO
from utility.utils import ConsoleColors, create_player_info, in_battle
from utility.constants import BLUE, GOLD, EXP


# --- Helper functions --------------------------------------------------------


def calculate_damage(attacker_dmg: int, defender_def: int) -> int:
    """
    Simple damage formula: attacker damage minus defender defence,
    but never less than 1.
    """
    return max(1, attacker_dmg - defender_def)


def apply_mutation(monster_data: dict) -> dict:
    """
    Applies a random mutation to a monster with a small chance.
    Returns a mutated copy of the monster data, without modifying the original.
    """
    mutated = monster_data.copy()

    MUTATIONS = {
        "Armored": {"defence_mult": 1.3, "description": "Has tougher defence."},
        "Fragile": {
            "hp_mult": 0.7,
            "attack_mult": 1.4,
            "description": "Lower HP but stronger attacks.",
        },
        "Chaotic": {
            "chaotic": True,
            "description": "Unpredictable attack patterns.",
        },
        "Regenerator": {
            "regen": 5,
            "description": "Regenerates HP over time.",
        },
        "Lucky": {
            "extra_rewards": True,
            "description": "Drops extra rewards.",
        },
    }

    # 15% chance to mutate
    if random.random() < 0.15:
        mutation_name = random.choice(list(MUTATIONS.keys()))
        mutation = MUTATIONS[mutation_name]

        mutated["mutation"] = mutation_name
        mutated["mutation_description"] = mutation.get("description", "")

        # Apply stat multipliers if present
        if "hp_mult" in mutation:
            mutated["hp"] = int(mutated.get("hp", 1) * mutation["hp_mult"])
        if "attack_mult" in mutation:
            mutated["attack"] = int(mutated.get("attack", 1) * mutation["attack_mult"])
        if "defence_mult" in mutation:
            mutated["defence"] = int(
                mutated.get("defence", 1) * mutation["defence_mult"]
            )

        # Special flags (kept simple; you can expand logic later)
        if "regen" in mutation:
            mutated["regen"] = mutation["regen"]
        if "chaotic" in mutation:
            mutated["chaotic"] = True
        if "extra_rewards" in mutation:
            mutated["extra_rewards"] = True

    return mutated


# --- UI views ----------------------------------------------------------------


class TravelButton(disnake.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @disnake.ui.button(label="Ruins", style=disnake.ButtonStyle.secondary)
    async def ruins(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.value = "ruins"
        self.stop()

    @disnake.ui.button(label="Snowdin", style=disnake.ButtonStyle.secondary)
    async def snowdin(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.value = "snowdin"
        self.stop()

    @disnake.ui.button(label="Waterfall", style=disnake.ButtonStyle.secondary)
    async def waterfall(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.value = "waterfall"
        self.stop()

    @disnake.ui.button(label="Hotland", style=disnake.ButtonStyle.secondary)
    async def hotland(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.value = "hotland"
        self.stop()

    @disnake.ui.button(label="Core", style=disnake.ButtonStyle.secondary)
    async def core(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.value = "core"
        self.stop()

    @disnake.ui.button(label="Barrier", style=disnake.ButtonStyle.secondary)
    async def barrier(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.value = "barrier"
        self.stop()

    @disnake.ui.button(label="Last Corridor", style=disnake.ButtonStyle.secondary)
    async def last_corridor(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.value = "last_corridor"
        self.stop()


class Choice(disnake.ui.View):
    def __init__(self, author: disnake.Member):
        super().__init__()
        self.author = author
        self.choice = None

    @disnake.ui.button(label="Yes", style=disnake.ButtonStyle.green)
    async def yes(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author != self.author:
            return await inter.send("This is not yours kiddo!", ephemeral=True)

        self.choice = True
        await inter.response.defer()
        await inter.edit_original_message(components=[])
        self.stop()

    @disnake.ui.button(label="No", style=disnake.ButtonStyle.red)
    async def no(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author != self.author:
            return await inter.send("This is not yours kiddo!", ephemeral=True)

        self.choice = False
        await inter.response.defer()
        await inter.edit_original_message(components=[])
        self.stop()


class Loading(disnake.ui.View):
    def __init__(self):
        super().__init__()

    @disnake.ui.button(
        emoji="<a:loading:1033856122345508874>",
        style=disnake.ButtonStyle.gray,
        disabled=True,
    )
    async def loading(self):
        return


class BossButton(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    @disnake.ui.button(label="Fight", style=disnake.ButtonStyle.red)
    async def fight(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        data = await inter.bot.players.find_one({"_id": inter.author.id})
        monsters = fileIO("./data/bosses.json", "load")
        monster = data["fight_monster"]
        location = data["location"]

        # Player stats
        user_hp = data["health"]
        user_atk = data["attack"]
        user_def = data["defence"]

        # Monster stats (use current fight_* values, already set when fight started)
        enemy_title = monsters[location][monster]["title"]
        enemy_hp = data["fight_hp"]
        enemy_atk = data["fight_atk"]
        enemy_def = data["fight_def"]

        gold_min = monsters[location][monster]["gold_min"]
        gold_max = monsters[location][monster]["gold_max"]

        await BossBattle(
            self,
            inter,
            monster,
            user_hp,
            user_atk,
            user_def,
            enemy_title,
            enemy_hp,
            enemy_atk,
            enemy_def,
            gold_min,
            gold_max,
        )
        return

    @disnake.ui.button(label="Use", style=disnake.ButtonStyle.gray, disabled=True)
    async def use(self, button: disnake.ui.button, inter: disnake.MessageInteraction):
        await inter.response.defer()

    @disnake.ui.button(label="Mercy", style=disnake.ButtonStyle.green)
    async def mercy(self, button: disnake.ui.button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        data = await inter.bot.players.find_one({"_id": inter.author.id})
        loading = Loading()

        location = data["location"]
        monsters = fileIO("./data/bosses.json", "load")
        monster = data["fight_monster"]

        # Player stats
        user_hp = data["health"]
        user_atk = data["attack"]
        user_def = data["defence"]

        # Monster stats (original, not mutated, for the second phase)
        enemy_title = monsters[location][monster]["title"]
        enemy_hp = monsters[location][monster]["hp"]
        enemy_atk = monsters[location][monster]["attack"]
        enemy_def = monsters[location][monster]["defence"]

        gold_min = monsters[location][monster]["gold_min"]
        gold_max = monsters[location][monster]["gold_max"]

        embed = disnake.Embed(
            title="Mercy", color=BLUE, description=f"You tried to spare {monster}"
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/900274624594575361/1032089003912089770/3abaf892f9a10b66e7341589a9b6d210.jpg"
        )
        await inter.edit_original_message(embed=embed, view=loading)
        await asyncio.sleep(5)

        choice = random.randint(1, 3)
        if choice != 2:
            embed = disnake.Embed(
                title="Mercy",
                color=BLUE,
                description=f"{monster} accepted your mercy!",
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/900274624594575361/1032089003912089770/3abaf892f9a10b66e7341589a9b6d210.jpg"
            )
            await inter.edit_original_message(embed=embed, view=None)
            spares = data["spares"] + 1
            info = {
                "in_fight": False,
                "fight_monster": "",
                "fight_hp": 0,
                "fight_atk": 0,
                "fight_def": 0,
                "spares": spares,
            }
            await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})

            print(
                f"{ConsoleColors.LRED}{inter.author} has stopped a fight(spared){ConsoleColors.ENDC}"
            )
            return

        embed = disnake.Embed(
            title="Mercy",
            color=BLUE,
            description=f"{monster} didn't accept your mercy!",
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/900274624594575361/1032089003912089770/3abaf892f9a10b66e7341589a9b6d210.jpg"
        )
        await inter.edit_original_message(embed=embed)
        await asyncio.sleep(5)

        await BossBattle(
            self,
            inter,
            monster,
            user_hp,
            user_atk,
            user_def,
            enemy_title,
            enemy_hp,
            enemy_atk,
            enemy_def,
            gold_min,
            gold_max,
        )


class ExploreButton(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    @disnake.ui.button(label="Fight", style=disnake.ButtonStyle.red)
    async def fight(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        data = await inter.bot.players.find_one({"_id": inter.author.id})
        monsters = fileIO("./data/monsters.json", "load")
        monster = data["fight_monster"]
        location = data["location"]

        # Player stats
        user_hp = data["health"]
        user_atk = data["attack"]
        user_def = data["defence"]

        # Monster stats (current fight state)
        enemy_title = monsters[location][monster]["title"]
        enemy_hp = data["fight_hp"]
        enemy_atk = data["fight_atk"]
        enemy_def = data["fight_def"]

        gold_min = monsters[location][monster]["gold_min"]
        gold_max = monsters[location][monster]["gold_max"]

        await Battle(
            self,
            inter,
            monster,
            user_hp,
            user_atk,
            user_def,
            enemy_title,
            enemy_hp,
            enemy_atk,
            enemy_def,
            gold_min,
            gold_max,
        )
        return

    @disnake.ui.button(label="Use", style=disnake.ButtonStyle.gray, disabled=True)
    async def use(self, button: disnake.ui.button, inter: disnake.MessageInteraction):
        await inter.response.defer()

    @disnake.ui.button(label="Mercy", style=disnake.ButtonStyle.green)
    async def mercy(self, button: disnake.ui.button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        data = await inter.bot.players.find_one({"_id": inter.author.id})
        loading = Loading()

        location = data["location"]
        monsters = fileIO("./data/monsters.json", "load")
        monster = data["fight_monster"]

        # Player stats
        user_hp = data["health"]
        user_atk = data["attack"]
        user_def = data["defence"]

        # Monster stats (original, not mutated, for restart)
        enemy_title = monsters[location][monster]["title"]
        enemy_hp = monsters[location][monster]["hp"]
        enemy_atk = monsters[location][monster]["attack"]
        enemy_def = monsters[location][monster]["defence"]

        gold_min = monsters[location][monster]["gold_min"]
        gold_max = monsters[location][monster]["gold_max"]

        embed = disnake.Embed(
            title="Mercy", color=BLUE, description=f"You tried to spare {monster}."
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/900274624594575361/1032089003912089770/3abaf892f9a10b66e7341589a9b6d210.jpg"
        )
        await inter.edit_original_message(embed=embed, view=loading)
        await asyncio.sleep(5)

        choice = random.randint(1, 3)
        if choice != 2:
            embed = disnake.Embed(
                title="Mercy",
                color=BLUE,
                description=f"{monster} accepted your mercy!",
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/900274624594575361/1032089003912089770/3abaf892f9a10b66e7341589a9b6d210.jpg"
            )
            await inter.edit_original_message(embed=embed, view=None)
            spares = data["spares"] + 1
            info = {
                "in_fight": False,
                "fight_monster": "",
                "fight_hp": 0,
                "fight_atk": 0,
                "fight_def": 0,
                "spares": spares,
            }
            await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})

            print(
                f"{ConsoleColors.LRED}{inter.author} has stopped a fight(spared){ConsoleColors.ENDC}"
            )
            return

        embed = disnake.Embed(
            title="Mercy",
            color=BLUE,
            description=f"{monster} didn't accept your mercy!",
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/900274624594575361/1032089003912089770/3abaf892f9a10b66e7341589a9b6d210.jpg"
        )
        await inter.edit_original_message(embed=embed)
        await asyncio.sleep(5)

        await Battle(
            self,
            inter,
            monster,
            user_hp,
            user_atk,
            user_def,
            enemy_title,
            enemy_hp,
            enemy_atk,
            enemy_def,
            gold_min,
            gold_max,
        )


# --- Battle logic ------------------------------------------------------------


async def BossBattle(
    self,
    inter: disnake.MessageInteraction,
    monster: str,
    user_hp: int,
    user_atk: int,
    user_def: int,
    enemy_title: str,
    enemy_hp: int,
    enemy_atk: int,
    enemy_def: int,
    gold_min: int,
    gold_max: int,
):
    view = BossButton()
    loading = Loading()
    data = await inter.bot.players.find_one({"_id": inter.author.id})
    weapon = await inter.bot.weapons.find_one({"_id": data["weapon"]})

    # Player attack: base + random weapon range
    custom_user_atk = user_atk + random.randint(weapon["min_dmg"], weapon["max_dmg"])

    # Apply defence to damage calculations
    damage_to_enemy = calculate_damage(custom_user_atk, enemy_def)
    damage_to_user = calculate_damage(enemy_atk, user_def)

    new_user_hp = user_hp - damage_to_user
    new_enemy_hp = enemy_hp - damage_to_enemy

    embed = disnake.Embed(
        title=f"You damaged {monster}",
        color=BLUE,
        description=f"""
        **{monster}'s stats**
        **HP:** {new_enemy_hp}
        **Attack:** {enemy_atk}
        **Defence:** {enemy_def}
        """,
    )
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/900274624594575361/1032250561610907650/download.png"
    )
    await inter.edit_original_message(embed=embed, view=loading)
    await asyncio.sleep(5)

    if new_enemy_hp <= 0:
        location = data["location"]
        monsters = fileIO("./data/bosses.json", "load")
        exp = monsters[location][monster]["exp"] * data["multi_xp"]
        gold = random.randint(gold_min, gold_max) * data["multi_g"]
        embed = disnake.Embed(
            title=f"{monster} died!",
            color=BLUE,
            description=f"You got **{exp}** {EXP}, **{gold}** {GOLD} and **1** soul crate!",
        )
        await inter.edit_original_message(embed=embed, view=None)
        new_gold = data["gold"] + gold
        new_exp = data["exp"] + exp
        new_soul_crate = data["soul-crate"] + 1
        kills = data["kills"] + 1
        info = {
            f"{location}_boss": True,
            "soul-crate": new_soul_crate,
            "in_fight": False,
            "kills": kills,
            "exp": new_exp,
            "gold": new_gold,
            "health": user_hp,
            "fight_monster": "",
            "fight_hp": 0,
            "fight_atk": 0,
            "fight_def": 0,
        }
        await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})
        print(
            f"{ConsoleColors.LRED}{inter.author} has stopped a fight(won){ConsoleColors.ENDC}"
        )

        await levelup_check(self, inter)
        return

    embed = disnake.Embed(
        title=f"{monster} damaged you",
        color=BLUE,
        description=f"""
        **{inter.author.name}'s stats**
        **HP:** {new_user_hp}
        **Attack:** {user_atk} (base damage)
        **Defence:** {user_def}
        """,
    )
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/900274624594575361/1032250561610907650/download.png"
    )
    await inter.edit_original_message(embed=embed)
    await asyncio.sleep(5)

    if new_user_hp <= 0:
        location = data["location"]
        embed = disnake.Embed(
            title="You died!", color=BLUE, description=f"You lost **{gold_min}** {GOLD}"
        )
        await inter.edit_original_message(embed=embed, view=None)
        new_gold = data["gold"] - gold_min
        if new_gold < 0:
            new_gold = 0
        deaths = data["deaths"] + 1
        health = data["level"] * 2 / 0.5 + 20
        info = {
            "in_fight": False,
            "deaths": deaths,
            "gold": new_gold,
            "health": health,
            "fight_monster": "",
            "fight_hp": 0,
            "fight_atk": 0,
            "fight_def": 0,
        }
        await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})
        print(
            f"{ConsoleColors.LRED}{inter.author} has stopped a fight(died){ConsoleColors.ENDC}"
        )
        return

    embed = disnake.Embed(title=enemy_title, color=BLUE)
    embed.set_thumbnail(url=inter.author.avatar)
    embed.add_field(
        name=f"{monster}'s stats",
        value=f"**HP:** {new_enemy_hp}\n**Attack:** {enemy_atk}\n**Defence:** {enemy_def}",
    )
    embed.add_field(
        name=f"{inter.author.name}'s stats",
        value=f"**HP:** {new_user_hp}\n**Attack:** {user_atk} (base damage)\n**Defence:** {user_def}",
    )
    embed.set_footer(
        text="with each hit a random amount of damage is added to your base damage depending on your weapon"
    )
    await inter.edit_original_message(embed=embed, view=view)
    info = {
        "health": new_user_hp,
        "fight_hp": new_enemy_hp,
        "fight_atk": enemy_atk,
        "fight_def": enemy_def,
    }
    await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})


async def Battle(
    self,
    inter: disnake.MessageInteraction,
    monster: str,
    user_hp: int,
    user_atk: int,
    user_def: int,
    enemy_title: str,
    enemy_hp: int,
    enemy_atk: int,
    enemy_def: int,
    gold_min: int,
    gold_max: int,
):
    view = ExploreButton()
    loading = Loading()
    data = await inter.bot.players.find_one({"_id": inter.author.id})
    weapon = await inter.bot.weapons.find_one({"_id": data["weapon"]})

    # Player attack: base + random weapon damage
    custom_user_atk = user_atk + random.randint(weapon["min_dmg"], weapon["max_dmg"])

    # Apply defence to damage calculations
    damage_to_enemy = calculate_damage(custom_user_atk, enemy_def)
    damage_to_user = calculate_damage(enemy_atk, user_def)

    new_user_hp = user_hp - damage_to_user
    new_enemy_hp = enemy_hp - damage_to_enemy

    embed = disnake.Embed(
        title=f"You damaged {monster}",
        color=BLUE,
        description=f"""
        **{monster}'s stats**
        **HP:** {new_enemy_hp}
        **Attack:** {enemy_atk}
        **Defence:** {enemy_def}
        """,
    )
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/900274624594575361/1032250561610907650/download.png"
    )
    await inter.edit_original_message(embed=embed, view=loading)
    await asyncio.sleep(5)

    if new_enemy_hp <= 0:
        location = data["location"]
        monsters = fileIO("./data/monsters.json", "load")
        exp = monsters[location][monster]["exp"] * data["multi_xp"]
        gold = random.randint(gold_min, gold_max) * data["multi_g"]
        embed = disnake.Embed(
            title=f"{monster} died!",
            color=BLUE,
            description=f"You got **{round(exp)}** {EXP} and **{round(gold)}** {GOLD}",
        )
        await inter.edit_original_message(embed=embed, view=None)
        new_gold = data["gold"] + gold
        new_exp = data["exp"] + exp
        kills = data["kills"] + 1
        info = {
            "in_fight": False,
            "kills": kills,
            "exp": new_exp,
            "gold": new_gold,
            "health": user_hp,
            "fight_monster": "",
            "fight_hp": 0,
            "fight_atk": 0,
            "fight_def": 0,
        }
        await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})
        print(
            f"{ConsoleColors.LRED}{inter.author} has stopped a fight(won){ConsoleColors.ENDC}"
        )

        await levelup_check(self, inter)
        return

    embed = disnake.Embed(
        title=f"{monster} damaged you",
        color=BLUE,
        description=f"""
        **{inter.author.name}'s stats**
        **HP:** {new_user_hp}
        **Attack:** {user_atk} (base damage)
        **Defence:** {user_def}
        """,
    )
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/900274624594575361/1032250561610907650/download.png"
    )
    await inter.edit_original_message(embed=embed)
    await asyncio.sleep(5)

    if new_user_hp <= 0:
        location = data["location"]
        embed = disnake.Embed(
            title="You died!", color=BLUE, description=f"You lost **{gold_min}** {GOLD}"
        )
        await inter.edit_original_message(embed=embed, view=None)
        new_gold = data["gold"] - gold_min
        if new_gold < 0:
            new_gold = 0
        deaths = data["deaths"] + 1
        health = data["level"] * 2 / 0.5 + 20
        info = {
            "in_fight": False,
            "deaths": deaths,
            "gold": new_gold,
            "health": health,
            "fight_monster": "",
            "fight_hp": 0,
            "fight_atk": 0,
            "fight_def": 0,
        }
        await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})
        print(
            f"{ConsoleColors.LRED}{inter.author} has stopped a fight(died){ConsoleColors.ENDC}"
        )
        return

    embed = disnake.Embed(title=enemy_title, color=BLUE)
    embed.set_thumbnail(url=inter.author.avatar)
    embed.add_field(
        name=f"{monster}'s stats",
        value=f"**HP:** {new_enemy_hp}\n**Attack:** {enemy_atk}\n**Defence:** {enemy_def}",
    )
    embed.add_field(
        name=f"{inter.author.name}'s stats",
        value=f"**HP:** {new_user_hp}\n**Attack:** {user_atk} (base damage)\n**Defence:** {user_def}",
    )
    embed.set_footer(
        text="with each hit a random amount of damage is added to your base damage depending on your weapon"
    )
    await inter.edit_original_message(embed=embed, view=view)
    info = {
        "health": new_user_hp,
        "fight_hp": new_enemy_hp,
        "fight_atk": enemy_atk,
        "fight_def": enemy_def,
    }
    await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})


# --- Level up & commands -----------------------------------------------------


async def levelup_check(self, inter: disnake.MessageInteraction):
    data = await inter.bot.players.find_one({"_id": inter.author.id})
    author = inter.author
    exp = data["exp"]
    level = data["level"]
    attack = data["attack"]
    defence = data["defence"]
    exp_lvl_up = level * 100 / 0.4

    if exp >= exp_lvl_up:
        new_attack = attack + 2
        new_defence = defence + 2
        new_lvl = level + 1
        new_exp = exp - exp_lvl_up
        new_exp_lvl_up = new_lvl * 100 / 0.4
        embed = disnake.Embed(
            title=f"{author.name} Leveled up!",
            color=BLUE,
            description=f"""
            Your new level is **{new_lvl}!**
            Your new exp is **{round(new_exp)}/{round(new_exp_lvl_up)}**
            """,
        )
        info = {
            "level": new_lvl,
            "exp": new_exp,
            "attack": new_attack,
            "defence": new_defence,
        }
        await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})
        await inter.send(embed=embed)

    return


class Explore(commands.Cog):
    def __init__(self, bot: UndertaleBot):
        self.bot = bot

    @in_battle()
    @commands.slash_command()
    @commands.cooldown(1, 12, commands.BucketType.user)
    async def boss(self, inter: disnake.ApplicationCommandInteraction):
        """Fight bosses!"""
        await create_player_info(inter, inter.author)
        data = await inter.bot.players.find_one({"_id": inter.author.id})
        location = data["location"]
        if data[f"{location}_boss"] is True:
            return await inter.send("You already killed the boss of this location.")

        monsters = fileIO("./data/bosses.json", "load")
        random_monster = [m for m in monsters[location]]
        monster = random.choice(random_monster)

        # Player stats
        user_hp = data["health"]
        user_atk = data["attack"]
        user_def = data["defence"]

        # Monster stats (with mutation)
        base_monster = monsters[location][monster]
        mutated = apply_mutation(base_monster)

        enemy_title = mutated["title"]
        enemy_hp = mutated["hp"]
        enemy_atk = mutated["attack"]
        enemy_def = mutated["defence"]

        embed = disnake.Embed(
            title=enemy_title, description=f"**Location:** {location}", color=BLUE
        )
        embed.set_thumbnail(url=inter.author.avatar)

        mutation = mutated.get("mutation")
        mutation_desc = mutated.get("mutation_description")
        mutation_text = ""
        if mutation:
            mutation_text = f"\n⚠️ Mutation: **{mutation}**"
            if mutation_desc:
                mutation_text += f" – {mutation_desc}"

        embed.add_field(
            name=f"{monster}'s stats",
            value=f"**HP:** {enemy_hp}\n**Attack:** {enemy_atk}\n**Defence:** {enemy_def}{mutation_text}",
        )
        embed.add_field(
            name=f"{inter.author.name}'s stats",
            value=f"**HP:** {user_hp}\n**Attack:** {user_atk} (base damage)\n**Defence:** {user_def}",
        )
        embed.set_footer(
            text="with each hit a random amount of damage is added to your base damage depending on your weapon"
        )
        view = BossButton()
        await inter.send(embed=embed, view=view)
        info = {
            "in_fight": True,
            "fight_monster": monster,
            "fight_hp": enemy_hp,
            "fight_atk": enemy_atk,
            "fight_def": enemy_def,
        }
        await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})

        print(
            f"{ConsoleColors.YELLOW}{inter.author} has entered a fight{ConsoleColors.ENDC}"
        )
        return

    @in_battle()
    @commands.slash_command()
    @commands.cooldown(1, 12, commands.BucketType.user)
    async def explore(self, inter: disnake.ApplicationCommandInteraction):
        """Explore and find all kinds of monsters and treasure!"""
        await create_player_info(inter, inter.author)
        choices = ["fight", "gold", "crate", "puzzle"]
        item = random.choices(choices, weights=(90, 10, 10, 5), k=1)

        data = await inter.bot.players.find_one({"_id": inter.author.id})
        await inter.response.defer()

        if item[0] == "fight":
            location = data["location"]
            monsters = fileIO("./data/monsters.json", "load")

            random_monster = [m for m in monsters[location]]

            if len(random_monster) == 0:
                return await inter.send(
                    "There are no monsters here? You are for sure inside a /boss area only!"
                )

            monster = random.choice(random_monster)

            # Player stats
            user_hp = data["health"]
            user_atk = data["attack"]
            user_def = data["defence"]

            # Monster stats (with mutation)
            base_monster = monsters[location][monster]
            mutated = apply_mutation(base_monster)

            enemy_title = mutated["title"]
            enemy_hp = mutated["hp"]
            enemy_atk = mutated["attack"]
            enemy_def = mutated["defence"]

            embed = disnake.Embed(
                title=enemy_title,
                description=f"**Location:** {location}",
                color=BLUE,
            )
            embed.set_thumbnail(url=inter.author.avatar)

            mutation = mutated.get("mutation")
            mutation_desc = mutated.get("mutation_description")
            mutation_text = ""
            if mutation:
                mutation_text = f"\n⚠️ Mutation: **{mutation}**"
                if mutation_desc:
                    mutation_text += f" – {mutation_desc}"

            embed.add_field(
                name=f"{monster}'s stats",
                value=f"**HP:** {enemy_hp}\n**Attack:** {enemy_atk}\n**Defence:** {enemy_def}{mutation_text}",
            )
            embed.add_field(
                name=f"{inter.author.name}'s stats",
                value=f"**HP:** {user_hp}\n**Attack:** {user_atk} (base damage)\n**Defence:** {user_def}",
            )
            embed.set_footer(
                text="with each hit a random amount of damage is added to your base damage depending on your weapon"
            )
            view = ExploreButton()
            await inter.send(embed=embed, view=view, ephemeral=True)
            info = {
                "in_fight": True,
                "fight_monster": monster,
                "fight_hp": enemy_hp,
                "fight_atk": enemy_atk,
                "fight_def": enemy_def,
            }
            await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})

            print(
                f"{ConsoleColors.YELLOW}{inter.author} has entered a fight{ConsoleColors.ENDC}"
            )
            return

        if item[0] == "gold":
            found_gold = random.randint(150, 250)
            new_gold = data["gold"] + found_gold
            data["gold"] = new_gold
            await self.bot.players.update_one({"_id": inter.author.id}, {"$set": data})
            await inter.send(
                content=f"You found `{found_gold}`**G**! you now have `{round(new_gold)}`**G**",
                ephemeral=True,
            )
            return

        if item[0] == "crate":
            data["determination-crate"] += 1
            await self.bot.players.update_one({"_id": inter.author.id}, {"$set": data})
            await inter.send(
                content="You found `1` Determination crate! you can open it with `/crates`",
                ephemeral=True,
            )
            return

        if item[0] == "puzzle":
            await inter.send(
                content="But nobody came!",
                ephemeral=True,
            )
            return

    @in_battle()
    @commands.slash_command()
    @commands.cooldown(1, 12, commands.BucketType.user)
    async def reset(self, inter: disnake.ApplicationCommandInteraction):
        """Reset your stats for multipliers of gold and exp"""
        await create_player_info(inter, inter.author)
        data = await self.bot.players.find_one({"_id": inter.author.id})

        if data["level"] < 70:
            await inter.send(
                "You can not reset just yet. You will need to be **LOVE 70**."
            )
            return
        if data["resets"] >= 10:
            await inter.send("You are already at the max amount of resets!")
            return

        gold = round(data["multi_g"] + 0.4, 1)
        xp = round(data["multi_xp"] + 0.2, 1)

        file = disnake.File("./images/reset.png", filename="reset.png")

        embed = disnake.Embed(
            title=f"Resetting {inter.author.name}'s world.",
            description=(
                "Are you sure you want to proceed?\nYour progress will vanish, but you will gain multipliers "
                "for gold and xp.\n\n"
                f"Your gold multiplier will be **{gold}x**"
                f"\nYour XP multiplier will be **{xp}x**"
            ),
            color=BLUE,
        )
        embed.set_image("attachment://reset.png")

        view = Choice(inter.author)
        await inter.send(file=file, embed=embed, view=view)
        await view.wait()

        if not view.choice:
            await inter.send("You should come back again!", ephemeral=True)
            return

        await self.bot.players.delete_one({"_id": inter.author.id})
        await create_player_info(inter, inter.author)
        new_data = await self.bot.players.find_one({"_id": inter.author.id})
        new_data["resets"] = data["resets"] + 1
        new_data["multi_g"] = data["multi_g"] + 0.4
        new_data["multi_xp"] = data["multi_xp"] + 0.2
        new_data["kills"] = data["kills"]
        new_data["deaths"] = data["deaths"]
        new_data["registered_on"] = data["registered_on"]
        new_data["badges"] = data["badges"]
        new_data["void-crate"] = data["void-crate"] + 1
        await self.bot.players.update_one({"_id": inter.author.id}, {"$set": new_data})
        await inter.send(
            "You deleted your world, a new world appears in the horizon.",
            ephemeral=True,
        )

    @in_battle()
    @commands.slash_command()
    @commands.cooldown(1, 12, commands.BucketType.user)
    async def travel(self, inter: disnake.ApplicationCommandInteraction):
        """Travel within the world of undertale and fight unique enemies"""
        await create_player_info(inter, inter.author)
        data = await self.bot.players.find_one({"_id": inter.author.id})

        current_location = data["location"]
        level = data["level"]

        embed = disnake.Embed(
            title="Where would you like to go?",
            description=f"**Current location:** {current_location}\n**Current level:** {level}",
            color=BLUE,
        )
        embed.add_field(
            name="Locations",
            value="""
        Ruins
        Snowdin
        Waterfall
        Hotland
        Core
        Barrier
        Last Corridor
        """,
        )
        embed.add_field(
            name="Level Requirements",
            value="""
        lvl **1**
        lvl **5**
        lvl **13**
        lvl **25**
        lvl **50**
        lvl **75**
        lvl **100**
        """,
        )
        view = TravelButton()
        await inter.send(view=view, embeds=[embed], ephemeral=True)

        await view.wait()
        if view.value is None:
            return await inter.edit_original_message("You took to long to reply!")

        locations = fileIO("data/locations.json", "load")

        if locations[view.value]["level"] > level:
            return await inter.edit_original_message(
                content="Your level is too low to travel there!",
                embed=None,
                components=[],
            )

        if current_location == view.value:
            return await inter.edit_original_message(
                content=f"You are already at **{current_location}**",
                embed=None,
                components=[],
            )

        data["location"] = view.value

        info = {"location": data["location"]}
        await inter.bot.players.update_one({"_id": inter.author.id}, {"$set": info})

        await inter.edit_original_message(
            content=f"Traveling to **{view.value}**...", embed=None, components=[]
        )

        await asyncio.sleep(3)
        await inter.edit_original_message(content=f"You arrived at **{view.value}**")

    @commands.slash_command()
    @commands.cooldown(1, 12, commands.BucketType.user)
    async def leaderboard(
        self,
        inter: disnake.ApplicationCommandInteraction,
        leaderboard: str = commands.Param(
            name="leaderboard",
            choices=["gold", "exp", "resets", "kills", "spares", "deaths", "level"],
        ),
    ):
        """View the top 10 players on specifc stats"""
        await inter.response.defer()

        file = disnake.File("./images/trophy.png", filename="trophy.png")
        file_2 = disnake.File("./images/leaderboard.png", filename="leaderboard.png")

        if leaderboard not in [
            "gold",
            "exp",
            "resets",
            "kills",
            "spares",
            "deaths",
            "level",
        ] or None:
            embed = disnake.Embed(
                title=f"There is no such leaderboard as **{leaderboard}**",
                description="""
                You can choose from the following leaderboards:
                **gold, exp, resets, kills, spares, deaths, level**
                """,
                color=BLUE,
            )
            embed.set_thumbnail(url="attachment://trophy.png")
            return await inter.send(file=file, embed=embed)

        data = self.bot.players.find().limit(10).sort(leaderboard, -1)
        users = []
        async for raw in data:
            users.append(raw)

        users.sort(key=lambda user: user[leaderboard], reverse=True)

        output = [""]
        for i, user in enumerate(users, 1):
            player = await self.bot.fetch_user(user["_id"])
            rank_display = i
            if i == 1:
                rank_display = ":medal:"
            elif i == 2:
                rank_display = ":second_place:"
            elif i == 3:
                rank_display = ":third_place:"

            if len(str(player)) >= 24:
                player = str(player)[:-10]
            output.append(
                f"**{rank_display}. {player}:** {user[leaderboard]} {leaderboard}\n"
            )
            if i == 10:
                break
        output.append("")
        result = "".join(output)
        embed = disnake.Embed(
            title=f"{leaderboard} Leaderboard:",
            description=result,
            color=BLUE,
        )
        embed.set_image(url="attachment://leaderboard.png")
        embed.set_thumbnail(url="attachment://trophy.png")
        await inter.send(files=[file, file_2], embed=embed)


def setup(bot: UndertaleBot):
    bot.add_cog(Explore(bot))
