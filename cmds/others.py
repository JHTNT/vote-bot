from discord.ext import commands
from classes import CogExtension

class time(CogExtension):
    @commands.command()
    async def ping(self, ctx):
        await ctx.message.delete()
        await ctx.send(f"目前延遲為 {round(self.bot.latency * 1000)} ms")

    @commands.command()
    async def react(self, ctx, channel, message, emotion):
        text_channel = self.bot.get_channel(int(channel))
        msg = await text_channel.fetch_message(int(message))
        await msg.add_reaction(emotion)
        await ctx.message.delete()

    @commands.command()
    async def remove_react(self, ctx, channel, message, emotion):
        text_channel = self.bot.get_channel(int(channel))
        msg = await text_channel.fetch_message(int(message))
        await msg.remove_reaction(emotion, self.bot.user)
        await ctx.message.delete()

    @commands.command()
    async def say(self, ctx,channel_id: int, *message):
        messages = ""
        for i in message:
            messages = messages + str(i)  + " "
        if channel_id != 0:
            channel = self.bot.get_channel(channel_id)
            await ctx.message.delete()
            await channel.send(messages)
        else:
            await ctx.send(messages)

    @commands.command()
    async def repeat(self, ctx,channel_id: int, message_id: int, send_channel: int = 0):
        channel = self.bot.get_channel(channel_id)
        msg = await channel.fetch_message(int(message_id))
        if send_channel != 0:
            send = self.bot.get_channel(send_channel)
            await ctx.message.delete()
            await send.send(msg.content)
        else:
            await channel.send(msg.content)

def setup(bot):
    bot.add_cog(time(bot))