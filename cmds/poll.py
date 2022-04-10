import asyncio
import json
import time
from typing import List, Optional
from replit import db

import discord
import jsonpickle
from classes import CogExtension
from discord.ext import tasks
from discord_slash import ComponentContext, SlashContext, cog_ext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import (create_actionrow,
                                                   create_button)

# guild_ids = [696300626686246945]
# progress bar 設定
block_step = 0.5
whole = "█"
blocks = ["", "▌", "█"]
lsep = "▏"
rsep = "▏"
with open("data/poll_decorator.json", mode="r", encoding="utf8") as jfile:
    decoractor = json.load(jfile)
jsonpickle.set_preferred_backend('json')
jsonpickle.set_encoder_options('json', ensure_ascii=False)
# loop = asyncio.get_running_loop()
button_components = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "close"]

class PollData:
    """投票資料"""
    def __init__(self, author_id, title="", poll_option=None,
                 expiry_time=None, multi_vote=False):
        if poll_option == None:
            poll_option = []
        self.title = title
        self.options: List[Option] = poll_option
        self.expiry_time = expiry_time
        self.multi_vote: bool = multi_vote
        # 投票 message 的資料
        self.channel_id: int = 0
        self.author_id: int = author_id
        self.message_id: int = 0
        self.head = ""
        self.foot = ""

class Option:
    """投票選項"""
    def __init__(self, option_text="", opt_button=""):
        super().__init__()          # TODO 作用未知
        self.text = option_text
        self.opt_button = opt_button
        self.voters: List[int] = []

class Poll(CogExtension):
    def __init__(self, bot):
        self.bot = bot
        self.opt_button = ["01.", "02.", "03.", "04.", "05.",
                           "06.", "07.", "08.", "09.", "10."]
        # 代替裝飾器版本的 listener
        # self.bot.add_listener(self.on_component, "on_component")
        # with open("data/poll.json", mode="r", encoding="utf8") as jfile:
        #     self.poll_data = json.load(jfile)
        self.poll_data = db["poll"]
        # self.polls = {}

    async def setup(self):
        self.closePollsTask.start()

    def get_json_data(self, id):
        self.poll_data = db["poll"]
        return jsonpickle.decode(self.poll_data[str(id)])

    def delete_json_data(self, id):
        del self.poll_data[str(id)]
        # del db["poll"][str(id)]
        db["poll"] = self.poll_data

    def dump_json_data(self, message_id, data):
        # with open("data/poll.json", "w", encoding="utf8") as jfile:
        #     json.dump(data, jfile, indent=4, ensure_ascii=False)
        self.poll_data[message_id] = data
        db["poll"] = self.poll_data

    async def get_msg(self, channel: discord.TextChannel, message_id):
        """按照給定的 id 搜尋訊息"""
        for msg in self.bot.cached_messages:
            if msg.id == message_id:
                return msg
        # 若暫存訊息找不到，則在頻道中搜尋
        # try:        # TODO 需要釐清使用方法
        o = discord.Object(id=message_id + 1)
        msg = await channel.history(limit=1, before=o).next()
        if message_id == msg.id:
            return msg
        return None
        # 找不到訊息
        # except discord.NoMoreItems:
        #     return None

    @cog_ext.cog_component(components=button_components)
    async def on_component(self, ctx: ComponentContext):
        loop = asyncio.get_running_loop()
        poll: Optional[PollData] = await self.get_poll(ctx.origin_message_id)
        if poll:
            if ctx.custom_id == "close":
                if (ctx.author_id == poll.author_id or
                   (ctx.author.guild_permissions.administrator or
                    ctx.author.guild_permissions.manage_guild)):
                    await self.close_poll(poll)
                else:
                    await ctx.send(":no_entry_sign: **你不是發起人或權限不足**", hidden=True)
            else:
                await ctx.defer(edit_origin=True)
                option_id = int(ctx.custom_id)
                # 偵測使用者是否投過該選項
                author_id = ctx.author_id
                option: Option = poll.options[option_id]
                if author_id not in option.voters:
                    option.voters.append(author_id)
                else:
                    option.voters.remove(author_id)
                # 計算票數
                total_votes = 0
                for _option in poll.options:
                    # 不允許複選時，清除該使用者其他選項的票
                    if poll.multi_vote == False:
                        if _option != option:
                            if author_id in _option.voters:
                                _option.voters.remove(author_id)
                    total_votes += len(_option.voters)
                # 編輯投票資訊
                temp_option = []
                temp_bar = ["\n```"]
                for _option in poll.options:
                    temp_option.append(f"{_option.opt_button} {_option.text}")
                    temp_bar.append(f"{_option.opt_button} " +
                        f"{self.create_bar(len(_option.voters), total_votes)}")
                temp_bar.append(f"```總票數：`{total_votes}`")
                new_content = (poll.head + "\n".join(temp_option) +
                               "\n".join(temp_bar) + poll.foot)
                # 更新 json 票數資料
                # self.poll_data[str(ctx.origin_message_id)] = jsonpickle.encode(poll.__dict__)
                # await loop.run_in_executor(None, self.dump_json_data, self.poll_data)
                await loop.run_in_executor(None, self.dump_json_data, str(ctx.origin_message_id), jsonpickle.encode(poll.__dict__))

                await ctx.edit_origin(content=new_content)

    def create_bar(self, count, total):
        progress_length = 20
        percentage = 0
        if total != 0:
            percentage = count / total
            length = progress_length * percentage
            whole_tiles_count = int(length)
            frac_part = length - whole_tiles_count
            frac_index = int(frac_part / block_step)
            filled_bar = whole * whole_tiles_count + blocks[frac_index]
            missing = progress_length - len(filled_bar)
            empty_bar = " " * missing
            progress_str = f"▏{filled_bar}{empty_bar}▕　({percentage:0.2%})"
        else:
            progress_str = "▏                    ▕　(0.00%)"
        return progress_str

    async def get_poll(self, message_id) -> PollData:
        loop = asyncio.get_running_loop()
        # try:
        data = await loop.run_in_executor(None, self.get_json_data, message_id)
        if isinstance(data, PollData):
            return data
        poll = PollData(0)
        for key in data.keys():
            # 初始化投票
            if hasattr(poll, key):
                poll.__setattr__(key, data[key])
        return poll
        # except Exception as e:
        #     print(e)
        #     return None

    @tasks.loop(seconds=30)
    async def closePollsTask(self):
        # loop = asyncio.get_running_loop()
        """檢查投票是否需要關閉"""
        # keys = await loop.run_in_executor(None, self.poll_data.keys)
        keys = db["poll"].keys()
        for key in list(keys):
            poll = await self.get_poll(key)
            if poll.expiry_time is not None:
                if poll.expiry_time < time.time():
                    await self.close_poll(poll)

    async def close_poll(self, poll: PollData):
        loop = asyncio.get_running_loop()
        channel = self.bot.get_channel(poll.channel_id)
        message = await self.get_msg(channel, poll.message_id)
        if message:
            origin_content = message.content.replace(
                poll.foot, f"\n發起人：<@{poll.author_id}>")
            origin_content += f"\n投票已在 <t:{int(time.time())}:R> 關閉"
            await message.edit(content=origin_content, components=[])
            # 移除投票
            await loop.run_in_executor(None, self.delete_json_data, poll.message_id)

    async def create_poll(self, ctx: SlashContext, title, options: list, **kwargs):
        loop = asyncio.get_running_loop()
        # try:
        temp_time = None
        poll_data = PollData(ctx.author_id)     # 初始化投票
        # 檢測選項數量
        options_len = len(options)
        if options_len >= 10:
            return await ctx.send(":no_entry_sign: **最多只能輸入 10 個選項**")
        elif options_len < 2:
            return await ctx.send(":no_entry_sign: **至少輸入 2 個選項**")
        # 檢測結束時間
        if "time" in kwargs and kwargs["time"] is not None:
            temp_time = kwargs.get("time")
        if temp_time is not None and temp_time <= 0:
            return await ctx.send(":no_entry_sign: **秒數請輸入正整數**")

        if "multivote" in kwargs and kwargs["multivote"] is not None:
            poll_data.multi_vote = False if kwargs.get("multivote") == "False" else True
        multi_text = "多選" if poll_data.multi_vote is True else "單選"
        poll_data.channel_id = ctx.channel_id
        if temp_time is not None:
            poll_data.expiry_time = temp_time + int(time.time())
            close_time = f"，預計於 <t:{poll_data.expiry_time}:R> 結束"
        else:
            close_time = ""
        poll_data.head = f"**[投票] {title}** （{multi_text}）\n"
        poll_data.foot = f"\n發起人：<@{ctx.author_id}>{close_time}"
        # 新增按鈕
        buttons = []
        temp_option = []
        temp_bar = ["\n```"]
        opt_list = self.opt_button
        for i in range(options_len):
            _option = Option(option_text=options[i], opt_button=opt_list[i])
            options[i] = f"{_option.opt_button} - {_option.text}"
            temp_option.append(f"{_option.opt_button} {_option.text}")
            temp_bar.append(f"{_option.opt_button}"
                            " ▏                    ▕　(0.00%)")
            poll_data.options.append(_option)
            buttons.append(
                create_button(
                    style=ButtonStyle.gray, custom_id=f"{i}",
                    label=f"{opt_list[i]}"))
        temp_bar.append(f"\n```")
        new_content = (poll_data.head + "\n".join(temp_option) +
                       "\n".join(temp_bar) + poll_data.foot)
        # 按鈕排版
        action_row_buttons = []
        components = []
        for button in buttons:
            action_row_buttons.append(button)
            if len(action_row_buttons) == 5:
                components.append(create_actionrow(*action_row_buttons))
                action_row_buttons = []
        if len(action_row_buttons) != 0:
            components.append(create_actionrow(*action_row_buttons))
        components.append(create_actionrow(
            create_button(style=ButtonStyle.red,
            custom_id="close", label="結束投票")))
        # 建立投票及儲存資料
        msg = await ctx.send(content=new_content, components=components)
        poll_data.message_id = msg.id
        # self.poll_data[str(msg.id)] = jsonpickle.encode(poll_data.__dict__)
        # await loop.run_in_executor(None, self.dump_json_data, self.poll_data)
        await loop.run_in_executor(None, self.dump_json_data, str(msg.id), jsonpickle.encode(poll_data.__dict__))
        # except Exception as e:
        #     error_class = e.__class__.__name__ #取得錯誤類型
        #     detail = e.args[0] #取得詳細內容
        #     cl, exc, tb = sys.exc_info() #取得Call Stack
        #     lastCallStack = traceback.extract_tb(tb)[-1] #取得Call Stack的最後一筆資料
        #     fileName = lastCallStack[0] #取得發生的檔案名稱
        #     lineNum = lastCallStack[1] #取得發生的行號
        #     funcName = lastCallStack[2] #取得發生的函數名稱
        #     errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(fileName, lineNum, funcName, error_class, detail)
        #     print(errMsg)

    # 需要 bot 權限檢查
    @cog_ext.cog_slash(**decoractor)
    async def poll(self, ctx: SlashContext, title: str, options: str,
                   multivote: str="False", time=None):
        await ctx.defer()
        options = options.split(", ")
        await self.create_poll(ctx, title, options, multivote=multivote, time=time)

def setup(bot):
    bot.add_cog(Poll(bot))