import discord
from discord_slash import cog_ext
from classes import CogExtension

guild_ids = [696300626686246945, 798194124066521099, 662271535674949632, 851494406791888946]
options = [
    {
        "name" : "name",
        "description" : "打屁屁的對象",
        "required" : True,
        "type" : 6
    },
    {
        "name" : "reason",
        "description" : "打屁屁的原因",
        "required" : True,
        "type" : 3
    }
]

class Dapigu(CogExtension):
    @cog_ext.cog_slash(name="dapigu",
             description="全新推出打屁屁功能！",
             guild_ids=guild_ids, options=options)
    async def dapigu(self, ctx, name, reason):
        embed=discord.Embed(color=0xfaa51b)
        embed.set_author(name="[DAPIGU]", icon_url=name.avatar_url)
        embed.add_field(name="受害者", value=name.mention, inline=True)
        embed.add_field(name="加害者", value=ctx.author.mention, inline=True)
        embed.add_field(name="原因", value=f"{reason}", inline=True)
        embed.set_footer(text="by 七公里打屁屁大隊")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Dapigu(bot))