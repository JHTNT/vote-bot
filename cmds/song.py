import json

from classes import CogExtension
from discord_slash import SlashContext, cog_ext
from replit import db

with open("data/song_decorator.json", mode="r", encoding="utf8") as jfile:
    decorator = json.load(jfile)["song"]

class Song(CogExtension):
    @cog_ext.cog_subcommand(**decorator[0])
    async def add(self, ctx: SlashContext, name: str):
        l = db["song"]["songs"]
        l.append(name)
        db["song"] = {"songs": l}
        await ctx.send(f"已添加歌曲 `{name}`")

    @cog_ext.cog_subcommand(**decorator[1])
    async def remove(self, ctx: SlashContext, index: int):
        if index > len(db["song"]["songs"]) or index <= 0:
            await ctx.send("索引值超出範圍", hidden=True)
        else:
            l = db["song"]["songs"]
            name = db["song"]["songs"][index - 1]
            del l[index - 1]
            db["song"] = {"songs": l}
            await ctx.send(f"已移除歌曲 `{name}`")

    @cog_ext.cog_subcommand(**decorator[2])
    async def queue(self, ctx: SlashContext, hide: str = None):
        text = "```\n"
        for i, name in enumerate(db["song"]["songs"]):
            text += f"{i + 1: 02d}. " + name + "\n"
        text += "```"
        if hide == "False":
            await ctx.send(text)
        else:
            await ctx.send(text, hidden=True)

    @cog_ext.cog_subcommand(**decorator[3])
    async def clear(self, ctx: SlashContext):
        db["song"] = {"songs": []}
        await ctx.send(f"已清除所有歌曲")

def setup(bot):
    bot.add_cog(Song(bot))