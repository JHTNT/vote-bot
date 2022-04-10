import discord
from discord.ext import commands
from discord_slash import SlashCommand, ComponentContext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import (create_actionrow, create_button)
import os
import keep_alive

bot = commands.Bot(command_prefix = "/", help_command=None)
slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.idle)
    for cog in bot.cogs:        # 讓 Cog 初始化
        _c = bot.get_cog(cog)
        if hasattr(_c, "setup"):
            await _c.setup()
    print("BOT 已啟動")

@bot.command()
async def load(ctx, extension):
    bot.load_extension(f"cmds.{extension}")
    await ctx.message.delete()
    await ctx.send(f"Loaded `{extension}`")

@bot.command()
async def unload(ctx, extension):
    bot.unload_extension(f"cmds.{extension}")
    await ctx.message.delete()
    await ctx.send(f"Unloaded `{extension}`")

@bot.command()
async def reload(ctx, extension):
    try:
        bot.reload_extension(f"cmds.{extension}")
        await ctx.message.delete()
        await ctx.send(f"Reloaded `{extension}`")
    except discord.ext.commands.errors.ExtensionNotLoaded:
        await ctx.send(f"`{extension}` not loaded")

for filename in os.listdir("./cmds"):
    if filename.endswith(".py"):
        bot.load_extension(f"cmds.{filename[:-3]}")

@slash.slash(name="fx", description="召喚橘鍵", guild_ids=[696300626686246945, 798194124066521099])
async def sdvx(ctx):
    # msg = await get_msg(696300627222855732, 884508969643671602)
    buttons = []
    # buttons.append(create_button(style=ButtonStyle.gray, custom_id="white1",emoji="⬜"))
    # buttons.append(create_button(style=ButtonStyle.gray, custom_id="white2",emoji="⬜"))
    # buttons.append(create_button(style=ButtonStyle.gray, custom_id="white3",emoji="⬜"))
    # buttons.append(create_button(style=ButtonStyle.gray, custom_id="white4",emoji="⬜"))
    buttons.append(create_button(style=ButtonStyle.gray, custom_id="orange1", emoji="🟧"))
    buttons.append(create_button(style=ButtonStyle.gray, custom_id="orange2", emoji="🟧", disabled=True))
    action_row_buttons = []
    components = []
    for button in buttons:
        action_row_buttons.append(button)
    components.append(create_actionrow(*action_row_buttons))
    await ctx.send(content="橘鍵", components=components)

@slash.component_callback(components="orange1")
async def on_component(ctx: ComponentContext):
    await ctx.send("<a:rick_roll:890283417613250581>", hidden=True)

if __name__ == "__main__":
    keep_alive.keep_alive()
    bot.run(os.environ['TOKEN'])