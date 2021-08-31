import discord
from discord.ext import commands
from discord_slash import SlashCommand
import os

bot = commands.Bot(command_prefix = "/", help_command=None)
slash = SlashCommand(bot, sync_commands=True)

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
    bot.reload_extension(f"cmds.{extension}")
    await ctx.message.delete()
    await ctx.send(f"Reloaded `{extension}`")

for filename in os.listdir("./cmds"):
    if filename.endswith(".py"):
        bot.load_extension(f"cmds.{filename[:-3]}")

if __name__ == "__main__":
	# bot.run("NjIzOTI3ODUxNjYxNjU2MTE0.XYJkFw.8g0kp4JnshGt8kmq7rRoqQ9qarQ")
    bot.run("ODQ0Mzk3MTA5Njk1MzQ4Nzc3.YKR0Fw.CZDJrg-AQAyyLGeDlhRwnDEpFz0")