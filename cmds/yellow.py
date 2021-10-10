import asyncio
import gc
import json
import random
from replit import db

import discord
from classes import CogExtension
from discord_slash import cog_ext
from discord_slash.context import ComponentContext, SlashContext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import (create_actionrow,
                                                   create_button,
                                                   create_select,
                                                   create_select_option,
                                                   wait_for_component)

with open("data/yellow_decorator.json", mode="r", encoding="utf8") as jfile:
    decoractor = json.load(jfile)["yellow"]

db = db["yellow"]

class Player:
    def __init__(self, member, game):
        self.member = member
        self.score = 0
        self.cards = []         # 手牌

        # 擔任裁判次數
        self.judge_count = 0

        # 當前回合選擇的卡是第幾張
        self.first_card = 0
        self.second_card = 0
        self.third_card = 0

        # 若牌庫不足則重新洗牌
        if len(game.answer_cards) < 12:
            game.answer_cards += game.used_answer_cards.copy()
            game.used_answer_cards = []

        # 抽選初始手牌並記錄
        self.cards += random.sample(game.answer_cards, 12)
        for card in self.cards:
            game.answer_cards.remove(card)
            game.used_answer_cards.append(card)

class Game:
    def __init__(self, ctx: SlashContext, score: int, packs: str,
                 all_packs , players, min_players):
        self.active = False         # 遊戲是否進行中
        self.round_count = 0
        self.min = min_players
        self.ctx = ctx
        self.score_to_win = score       # 獲勝分數

        self.question_cards = []
        self.answer_cards = []
        self.used_question_cards = []
        self.used_answer_cards = []

        # 讀入啟用的卡牌
        if packs == "all":
            for pack_name, questions, answers in all_packs:
                self.question_cards += questions
                self.answer_cards += answers
        else:
            packs = packs.split()
            for pack_name, questions, answers in all_packs:
                if pack_name in packs:
                    self.question_cards += questions
                    self.answer_cards += answers

        # 初始化玩家資料
        self.players = [Player(member, self) for member in players]
        random.shuffle(self.players)

    async def start(self):
        self.active = True
        # 遊戲進行條件判斷
        while self.active and \
            not any([user.score >= self.score_to_win for user in self.players]):
            self.round_count += 1
            await self.begin_round()
        final_scores = "\n".join([
            f'{user.member}：{user.score}' for user in sorted(
                self.players, key=lambda user: user.score, reverse=True)])
        await self.ctx.channel.send(embed=discord.Embed(
            title=f"遊戲已結束！ 以下是成績：", description=final_scores,
            color=discord.Color(0x3f51b5)))

    def make_select(self, user: Player, selected=[]):
        # 將玩家的手牌做成選單
        options = []
        for position, card in enumerate(user.cards):
            if position not in selected:
                options.append(create_select_option(
                    label=card, value=str(position)))
        return options

    async def begin_round(self):
        if len(self.question_cards) == 0:
            self.question_cards = self.used_question_cards.copy()
            self.used_question_cards = []
        question = self.question_cards.pop(random.randint(0, len(self.question_cards) - 1))
        self.used_question_cards.append(question)

        # 抽取一位玩家當裁判，若 judge_count 相等則隨機選擇
        judge = sorted(self.players,
            key=lambda player: (player.judge_count, random.random))[0]
        judge.judge_count += 1

        # 計算分數並顯示
        scores = "\n".join([
            f"{user.member}：{user.score}" for user in sorted(
                self.players, key=lambda user: user.score, reverse=True)])
        await self.ctx.channel.send(
            embed=discord.Embed(
                title=f"記分板（第 {self.round_count} 回合前，" +
                f"{self.score_to_win} 分獲勝）：",
                description=scores, color=discord.Color(0x3f51b5)))
        await asyncio.sleep(2)

        button = create_actionrow(create_button(
            style=ButtonStyle.green, label="選擇答案卡（裁判不用）", custom_id="start_select"))
        question_message =  await self.ctx.channel.send(embed=discord.Embed(
            title=f"裁判是 {judge.member}",
            description=f"{question}\n\n其他玩家請點擊按鈕後選擇手牌",
            color=discord.Color(0x212121)), components=[button])

        coroutines = []
        for user in self.players:
            if user != judge:
                async def wait_for_select(player_waiting: Player):
                    wait_check = lambda x: x.author == player_waiting.member
                    content = (f"{question}：\n\n請選擇一張答案卡" +
                            ("**（1 / 2）**" if question.count(r"\_\_\_") == 2 else "") +
                            ("**（1 / 3）**" if question.count(r"\_\_\_") == 3 else ""))
                    ar = create_actionrow(create_select(
                        self.make_select(player_waiting), custom_id="first_card",
                        placeholder="選擇第一張答案卡", max_values=1))
                    try:
                        await wait_for_component(self.ctx.bot, components="start_select",
                            check=wait_check, timeout=120)
                        await player_waiting.member.send(content=content, components=[ar])
                        msg = await wait_for_component(self.ctx.bot, components="first_card",
                                                       check=wait_check, timeout=90)
                        player_waiting.first_card = int(msg.selected_options[0])
                    except asyncio.TimeoutError:
                        await self.quit(player_waiting)
                        return await player_waiting.member.send("你因為掛機被踢出遊戲")
                    
                    if question.count(r"\_\_\_") == 2:
                        await msg.defer(edit_origin=True)
                        content = f"{question}：\n\n請選擇一張答案卡（2 / 2）"
                        ar = create_actionrow(create_select(
                            self.make_select(player_waiting,selected=[player_waiting.first_card]),
                            custom_id="second_card", placeholder="選擇第二張答案卡", max_values=1))
                        await msg.edit_origin(content=content, components=[ar])
                        try:
                            msg = await wait_for_component(self.ctx.bot, components="second_card",
                                                           check=wait_check, timeout=90)
                            player_waiting.second_card = int(msg.selected_options[0])
                        except asyncio.TimeoutError:
                            await self.quit(player_waiting)
                            return await player_waiting.member.send("你因為掛機被踢出遊戲")

                    if question.count(r"\_\_\_") == 3:
                        await msg.defer(edit_origin=True)
                        content = f"{question}：\n\n請選擇一張答案卡（2 / 3）"
                        ar = create_actionrow(create_select(
                            self.make_select(player_waiting, selected=[player_waiting.first_card]),
                            custom_id="second_card", placeholder="選擇第二張答案卡", max_values=1))
                        await msg.edit_origin(content=content, components=[ar])
                        try:
                            msg = await wait_for_component(self.ctx.bot, components="second_card",
                                                           check=wait_check, timeout=90)
                            player_waiting.second_card = int(msg.selected_options[0])
                        except asyncio.TimeoutError:
                            await self.quit(player_waiting)
                            return await player_waiting.member.send("你因為掛機被踢出遊戲")

                        await msg.defer(edit_origin=True)
                        content = f"{question}：\n\n請選擇一張答案卡（3 / 3）"
                        ar = create_actionrow(create_select(
                            self.make_select(player_waiting,
                            selected=[player_waiting.first_card, player_waiting.second_card]),
                            custom_id="third_card", placeholder="選擇第三張答案卡", max_values=1))
                        await msg.edit_origin(content=content, components=[ar])
                        try:
                            msg = await wait_for_component(self.ctx.bot, components="third_card",
                                                           check=wait_check, timeout=90)
                            player_waiting.second_card = int(msg.selected_options[0])
                        except asyncio.TimeoutError:
                            await self.quit(player_waiting)
                            return await player_waiting.member.send("你因為掛機被踢出遊戲")

                    await msg.edit_origin(content="請等待其他玩家選擇完畢", components=[])
                    return None

                coroutines.append(wait_for_select(user))
        await asyncio.gather(*coroutines)
        await question_message.edit(components=[])

        playing_users = self.players.copy()
        playing_users.remove(judge)
        playing_users.sort(key=lambda user: random.random())

        responses = ""
        if question.count(r"\_\_\_") == 1:
            for position, user in enumerate(playing_users):
                responses += f"{position + 1:02}：{user.cards[user.first_card]}\n"
        elif question.count(r"\_\_\_") == 2:
            for position, user in enumerate(playing_users):
                responses += f"{position + 1:02}：{user.cards[user.first_card]} " \
                            f"| {user.cards[user.second_card]}\n"
        elif question.count(r"\_\_\_") == 3:
            for position, user in enumerate(playing_users):
                responses += f"{position + 1:02}：{user.cards[user.first_card]} " \
                            f"| {user.cards[user.second_card]} " \
                            f"| {user.cards[user.third_card]}\n"

        selection_buttons = []
        for i in range(len(playing_users)):
            selection_buttons.append(create_button(
                style=ButtonStyle.gray, custom_id=f"{i:02}", label=f"{i + 1:02}"))
        action_row_buttons = []
        components = []
        for button in selection_buttons:
            action_row_buttons.append(button)
            if len(action_row_buttons) == 5:
                components.append(create_actionrow(*action_row_buttons))
                action_row_buttons = []
        if len(action_row_buttons) != 0:
            components.append(create_actionrow(*action_row_buttons))
        
        choose_winner = await self.ctx.channel.send(embed=discord.Embed(
            title=f'{judge.member} 請選擇贏家',
            description=f'{question}\n{responses}',
            color=discord.Color(0x212121)), components=components)
        try:
            winner = int((await wait_for_component(
                self.ctx.bot, check=lambda x: x.author == judge.member,
                messages=choose_winner, timeout=120)).custom_id)
        except asyncio.TimeoutError:
            # 若裁判離開遊戲則隨機選擇贏家
            winner = random.randint(1, len(playing_users))
            await self.quit(judge)
            await judge.member.send("你因為掛機而被踢出遊戲")
        await choose_winner.edit(components=None)

        winner = playing_users[int(winner)]
        winner.score += 1

        await self.ctx.channel.send(embed=discord.Embed(
            title=f"得分者是 {winner.member.name}！:tada:",
            description=f'回答：\n{winner.cards[winner.first_card]}' +
                (f" | {winner.cards[winner.second_card]}" if
                question.count(r"\_\_\_") == 2 else "") +
                (f" | {winner.cards[winner.second_card]}" if
                question.count(r"\_\_\_") == 3 else "") +
                (f" | {winner.cards[winner.third_card]}" if
                question.count(r"\_\_\_") == 3 else ""), color=discord.Color(0x8bc34a)))

        if question.count(r"\_\_\_") == 1:
            for player in self.players:
                if player != judge:
                    player.cards.pop(player.first_card)
                    if len(self.answer_cards) == 0:
                        self.answer_cards = self.used_answer_cards.copy()
                        self.used_answer_cards = []
                    new_card = self.answer_cards.pop(
                        random.randint(0, len(self.answer_cards) - 1))
                    player.cards.append(new_card)
                    self.used_answer_cards.append(new_card)
        elif question.count(r"\_\_\_") == 2:
            for player in self.players:
                if player != judge:
                    self.used_answer_cards.append(
                        player.cards.pop(player.first_card))
                    # 若第一張牌在前面則需左移
                    if int(player.first_card) < int(player.second_card):
                        player.cards.pop(player.second_card - 1)
                    else:
                        self.used_answer_cards.append(
                            player.cards.pop(player.second_card))
                    for _ in range(2):
                        if len(self.answer_cards) == 0:
                            self.answer_cards = self.used_answer_cards.copy()
                            self.used_answer_cards = []
                        new_card = self.answer_cards.pop(
                            random.randint(0, len(self.answer_cards) - 1))
                        player.cards.append(new_card)
        elif question.count(r"\_\_\_") == 3:
            for player in self.players:
                if player != judge:
                    self.used_answer_cards.append(
                        player.cards.pop(player.first_card))
                    if player.first_card < player.second_card:
                        player.cards.pop(player.second_card - 1)
                    else:
                        self.used_answer_cards.append(
                            player.cards.pop(player.second_card))
                    if int(player.second_card) < int(player.third_card):
                        player.cards.pop(player.third_card - 2)
                    else:
                        self.used_answer_cards.append(
                            player.cards.pop(player.third_card))
                    for _ in range(3):
                        if len(self.answer_cards) == 0:
                            self.answer_cards = self.used_answer_cards.copy()
                            self.used_answer_cards = []
                        new_card = self.answer_cards.pop(
                            random.randint(0, len(self.answer_cards) - 1))
                        player.cards.append(new_card)

        await asyncio.sleep(3)

    async def quit(self, player):
        self.players.remove(player)
        await self.ctx.channel.send(f'**{player.member} 離開了遊戲**')
        if len(self.players) < self.min:
            await self.ctx.channel.send(f'**剩餘玩家過少，無法繼續進行遊戲**')
            await self.end(True)

    async def end(self):
        self.active = False
        await self.ctx.channel.send('**遊戲將會在下個回合結束**')

class YelloCard(CogExtension):
    def __init__(self, bot):
        self.bot = bot
        self.games = db         # 紀錄當前進行中的遊戲 type: typing.Dict[str, Game]
        self.max_players = 10
        self.min_players = 3
        self.available_packs = {
            "basic": "基礎卡包",
            "basic2": "基礎卡包二",
            "ex1": "新年擴充包",
            "ex2": "石虎擴充包",
            "ex3": "政治擴充包",
            "ex4": "水逆擴充包",
            "ex5": "開山里擴充包"
        }
        self.packs = [] # 啟用的卡包
        for pack_data in self.available_packs.keys():
            question_cards_in_pack = open(
                f"data/packs/{pack_data}q.txt", "r", encoding="utf-8")
            answer_cards_in_pack = open(
                f"data/packs/{pack_data}a.txt", "r", encoding="utf-8")
            self.packs.append((
                pack_data,
                [card.strip() for card in question_cards_in_pack.readlines()],
                [card.strip() for card in answer_cards_in_pack.readlines()]))
            question_cards_in_pack.close()
            answer_cards_in_pack.close()

    @cog_ext.cog_component(components=["join", "leave"])
    async def prepare(self, ctx: ComponentContext):
        players = db[str(ctx.channel_id)]["players"]
        if ctx.custom_id == "join":
            if ctx.author in players:
                await ctx.send(content=":no_entry_sign: **你已在遊戲中**", hidden=True)
            else:
                players.append(ctx.author)
                content = ctx.origin_message.content
                content = ("目前玩家：" +
                    "、".join(str(plr) for plr in players)) # TODO 檢查
                await ctx.edit_origin(content=content)
                await ctx.send(content=":white_check_mark: **成功加入遊戲**", hidden=True)
        elif ctx.custom_id == "leave":
            if ctx.author in players:
                players.remove(ctx.author)
                content = ctx.origin_message.content
                content = ("目前玩家：" +
                    "、".join(str(plr) for plr in players)) # TODO 檢查
                await ctx.edit_origin(content=content)
                await ctx.send(content=":white_check_mark: **成功離開遊戲**", hidden=True)
            else:
                await ctx.send(content=":no_entry_sign: **你不在遊戲中**", hidden=True)

    @cog_ext.cog_subcommand(**decoractor[0])
    async def start(self, ctx: SlashContext, score: int, packs: str):
        # 添加參與者
        if str(ctx.channel_id) in db:
            await ctx.send(content=":no_entry_sign: **此頻道已有進行中的遊戲**", hidden=True)
            return
        else:
            db[str(ctx.channel_id)] = {}
            players = db[str(ctx.channel_id)]["players"] = [ctx.author]
            components = [create_actionrow(
                create_button(style=ButtonStyle.gray,
                                custom_id="join", label="參加"),
                create_button(style=ButtonStyle.gray,
                                custom_id="leave", label="退出"),
                create_button(style=ButtonStyle.green,
                                custom_id="start", label="開始遊戲"))]
            join_message = await ctx.send(content=f"目前玩家：{ctx.author}", components=components)
        players = db[str(ctx.channel_id)]["players"]
        while True:
            try:
                button_ctx = await wait_for_component(
                    self.bot, components="start", timeout=90)
                if len(players) > 10:
                    await button_ctx.send(":no_entry_sign: **人數不能超過 10 人**", hidden=True)
                elif len(players) < 3:
                    await button_ctx.send(":no_entry_sign: **人數須大於 3 人**", hidden=True)
                else:
                    players = set(players)
                    await button_ctx.edit_origin(components=None)
                    break
            except asyncio.TimeoutError:
                await join_message.edit(components=None)
                del db[str(ctx.channel_id)]
                await ctx.send("**超時。**")
                gc.collect()
                return

        self.games[str(ctx.channel_id)] = Game(ctx, score, packs, self.packs,
                                               players, self.min_players)
        await self.games[str(ctx.channel_id)].start()
        del self.games[str(ctx.channel_id)]
        gc.collect()

    @cog_ext.cog_subcommand(**decoractor[1])
    async def yellow_packs(self, ctx: SlashContext):
        await ctx.send(embed=discord.Embed(
            title=f"可用卡包（{len(self.packs)}）",
            description="\n".join(f"{pack_id}：{pack_name}"
            for pack_id, pack_name in self.available_packs.items())), hidden=True)

    @cog_ext.cog_subcommand(**decoractor[2])
    async def yellow_end(self, ctx: SlashContext):
        channel_game = self.games.get(str(ctx.channel_id), None)
        if not channel_game:
            return await ctx.send("沒有遊戲在這個頻道進行", hidden=True)
        await channel_game.end()

def setup(bot):
    bot.add_cog(YelloCard(bot))
