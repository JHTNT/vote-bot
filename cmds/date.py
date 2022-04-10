from discord.ext import commands
from classes import CogExtension
import json, asyncio, datetime

with open("data/date.json", "r", encoding="utf8") as jfile:
    jdata = json.load(jfile)

class time(CogExtension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.counter = 0

        async def date_count():
            await self.bot.wait_until_ready()
            self.channel = self.bot.get_channel(931440069305315341)
            while not self.bot.is_closed():
                now_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%H%M")
                now_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%Y/%m/%d")
                if now_time == "0000" and self.counter == 0:
                    msg = await self.channel.send(f"今天是 **`{now_date}`**\n還是不揪。")
                    await msg.add_reaction("😡")
                    for i in jdata["Time"]:
                        event = i
                        date = datetime.datetime.strptime(jdata["Time"][i], "%Y-%m-%d")
                        days = date - datetime.datetime.now()
                        if days.days == 0:
                            await self.channel.send(f"今天是 **`{event}`**。")
                            self.counter = 1
                        elif days.days > 0:
                            await self.channel.send(f"距離 **`{event}`** 還有 **`{days.days}`** 天。")
                            self.counter = 1
                        else:
                            self.counter = 1
                    await asyncio.sleep(60)
                    self.counter = 0
                else:
                    await asyncio.sleep(60)
                    self.counter = 0
                    pass

        self.bg_task = self.bot.loop.create_task(date_count())

    @commands.command()
    async def date_print(self, ctx):
        self.channel = self.bot.get_channel(696300627222855732)
        now_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%Y/%m/%d")
        msg = await self.channel.send(f"今天是 **`{now_date}`**\n還是不揪。")
        await msg.add_reaction("😡")
        for i in jdata["Time"]:
            event = i
            date = datetime.datetime.strptime(jdata["Time"][i], "%Y-%m-%d")
            days = date - datetime.datetime.now()
            if days.days == 0:
                await self.channel.send(f"今天是 **`{event}`**。")
                self.counter = 1
            elif days.days > 0:
                await self.channel.send(f"距離 **`{event}`** 還有 **`{days.days}`** 天。")

def setup(bot):
    bot.add_cog(time(bot))