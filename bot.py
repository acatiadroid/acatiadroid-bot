import discord
import typing
import io
import os
import re
import textwrap
import traceback
import datetime
import motor.motor_asyncio
import base64
from decouple import config
from discord.ext import commands
from contextlib import redirect_stdout
from aiohttp import ClientSession

import utils.util as util
from utils.db import Document

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=['uwu ', '?', 'owo '],
                        help_command=commands.MinimalHelpCommand(),
                        allowed_mentions=discord.AllowedMentions(users=True,
                                                                everyone=False,
                                                                roles=False,
                                                                replied_user=False),
                        intents=discord.Intents.all(),
                        description='A small utilitarian bot for doing cool things. Made by acatia#0001',
                        owner_id=600056626749112322,
                        case_insensitive=True)

    async def on_ready(self):
        print('sup dude')


bot = Bot()

# Secrets:
API_KEY = config('API_KEY')
BOT_TOKEN = config('TOKEN')
DB_URI = config('DB_URI')
TOKEN_REGEX = re.compile(r'([a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\- ]{27}|mfa\.[a-zA-Z0-9_\- ]{84})')


async def r(ctx, content: str):
    await ctx.message.reply(content)

async def em(ctx, embed):
    embed.set_footer(
        text=f'Requested by {ctx.author}', icon_url=ctx.author.avatar.url)
    await ctx.message.reply(embed=embed)

async def make_request(url: str, bot_id: int):
    header = {
        "key": API_KEY,
        "Content-Type": "application/json"
    }
    async with ClientSession(headers=header) as session:
        async with session.get(f"{url}{bot_id}") as r:
            try:
                return await r.json(content_type="application/json")
            except:
                return r

async def is_plonked(id: int):
    data = await bot.plonk.find(id)
    if not data:
        return False
    else:
        return True

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    plonked = await is_plonked(message.author.id)
    if plonked:
        return
    
    tokens = [token for token in TOKEN_REGEX.findall(message.content) if util.validate_token(token)]
    
    class ConfirmTokenInvalidation(discord.ui.View):
        def __init__(self):
            super().__init__()
            self.value = None
            self.message = message

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if self.message.author.id != interaction.user.id:
                return False
            else:
                return True

        @discord.ui.button(label='Yes', style=discord.ButtonStyle.red)
        async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = True
            for item in self.children:
                item.disabled = True
            self.stop()

        @discord.ui.button(label='No', style=discord.ButtonStyle.grey)
        async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = False
            for item in self.children:
                item.disabled = True
            self.stop()
        
        @discord.ui.button(emoji='❓', style=discord.ButtonStyle.blurple)
        async def _info(self, button: discord.ui.Button, interaction: discord.Interaction):
            content = """
            **How does this work?**
            Token invalidation works by posting your token on a public Gist on GitHub. **This is not bad!**
            Discord will see your token on GitHub and immidiately make that token no longer work. You
            will get an official Discord message saying that a token has been found and that Discord has 
            reset it.

            Please note that by not invalidating your token, anyone who sees your token can essentially now use your bot.
            """
            await interaction.response.send_message(content, ephemeral=True)
    
    if tokens:
        if "parsetoken" in message.content:
            pass
        else:
            view = ConfirmTokenInvalidation()
            try:
                msg = await message.reply(f'{message.author.mention} **Token found in your message.**\n\n> **Do you want me to invalidate it?**\nIt\'s highly recommended you invalidate it, otherwise anyone can control your bot.', view=view)
            except Exception as e:
                print(e)
            await view.wait()
            if view.value is None:
                gist = await util.create_gist(message, content="\n".join(tokens), reason='Automatic token invalidation')
                await msg.delete()
            elif view.value:
                gist = await util.create_gist(message, content="\n".join(tokens), reason='Automatic token invalidation (requested by user)')
                await message.channel.send(f'{message.author.mention}, I have invalidated your token. See it here: <{gist}>')
            else:
                await msg.delete()
        

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    # I just copied this from https://github.com/acatiadroid/util-bot lol
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'You are missing a required argument: {error}\nCommand usage: `uwu {ctx.command.qualified_name} {ctx.command.signature}`')
    if isinstance(error, commands.BadArgument):
        await ctx.send(f'You have provided an argument that is invalid: `{error}`\nCommand usage: `uwu {ctx.command.qualified_name} {ctx.command.signature}`')

@bot.command()
async def hello(ctx):
    """Idk why this exists"""
    await r(ctx, "Hey.")


@bot.command()
async def source(ctx):
    """My source code."""
    await r(ctx, "<https://github.com/acatiadroid/acatiadroid-bot>")


@bot.command(aliases=['wo'])
async def whoowns(ctx, bot: typing.Union[discord.Member, discord.User]):
    """Shows who owns a bot listed on motiondevelopment.top"""
    if not bot.bot:
        # pyright: reportUndefinedVariable=false
        return await r(ctx, "Not a bot.")

    data = await make_request("https://www.motiondevelopment.top/api/v1.2/bots/", bot.id)

    e = discord.Embed(color=0xfecdea)
    e.description = f'**{data["owner_name"]}** owns **{bot}**'

    await em(ctx, embed=e)


@bot.command(aliases=['desc'])
async def description(ctx, bot: typing.Union[discord.Member, discord.User]):
    """Shows the bot description of a certain bot on motiondevelopment.top"""
    data = await make_request("https://www.motiondevelopment.top/api/v1.2/bots/", bot.id)
    if not bot.bot:
        return await r(ctx, "Not a bot.")

    if len(data["Big_desc"]) > 2000:
        desc = data["Big_desc"][:2000] + \
            f"...\n[View original page for full description](https://www.motiondevelopment.top/bots/{bot.id})"
    else:
        desc = data["Big_desc"]
    await em(ctx, embed=discord.Embed(color=0xfecdea, description=desc))


@bot.command()
async def link(ctx, bot: typing.Union[discord.Member, discord.User]):
    """Gives the link to a bot that is listed on motiondevelopment.top"""
    if not bot.bot:
        return await r(ctx, "Not a bot.")
    await r(ctx, f'<https://www.motiondevelopment.top/bots/{bot.id}>')


@bot.command(aliases=['bo'])
async def botinfo(ctx, bot: typing.Union[discord.Member, discord.User]):
    """Shows all available information on a bot listed on motiondevelopment.top"""
    if not bot.bot:
        return await r(ctx, 'Not a bot.')

    data = await make_request("https://www.motiondevelopment.top/api/v1.2/bots/", bot.id)
    
    e = discord.Embed(
        title=f'Available bot info for {bot}',
        color=0xfecdea,
        description=f"**Short Bot Description:** (do `uwu desc [bot]` for big description)\n\n*{data['Small_desc']}*"
    )

    if data["bot_status"] == "online":
        status = '<:online:805576670353948702> Online'
    elif data["bot_status"] == "idle":
        status = '<:idle:805855470778056725> Idle'
    elif data["bot_status"] == "offline":
        status = '<:offline:805576352450871346> Offline'
    elif data["bot_status"] == "dnd":
        status = '<:dnd:819964146317393990> Do Not Disturb'

    listed_at = datetime.datetime.strptime(data["list_date"], '%Y-%m-%d')

    e.add_field(
        name='Owner:', value=f'**{data["owner_name"]}**\n({data["owner_id"]})', inline=False)
    e.add_field(name='Tags:', value=', '.join(data["tops"]))
    e.add_field(name='Vanity URL:', value=data["vanity_url"]
                if data["vanity_url"] != '' else 'No vanity URL set.', inline=False)
    e.add_field(name='Bot Status:', value=status)
    e.add_field(name='Invites:',
                value=f'[Bot Invite]({data["invite"]})\n[Bot Support Server](https://discord.gg/{data["discord"]})', inline=False)
    e.add_field(name='Other Bot Info:', value=f'''
    **Prefix:** `{data["prefix"]}`
    **Site:** {data["site"] if data["site"] != '' else "No sites."}
    **Library:** {data["lib"]}
    **Listed at:** {listed_at}
    **Server Count:** {data["servers"] if data["servers"] != 'None' else '*Not set up!*'}''', inline=False)
    e.set_thumbnail(url=f'https://cdn.discordapp.com/avatars/{data["id"]}/{data["avatar"]}')
    await em(ctx, embed=e)


@bot.command()
async def raw(ctx, message_id: int = None):
    """Gets the raw, unformatted content of a message."""
    if ctx.message.reference:
        msg = await ctx.channel.fetch_message(ctx.message.reference.resolved.id)
        await r(ctx, f"**{msg.author}:**```{msg.content}```")
    else:
        if message_id is None:
            return await r(ctx, "Please either pass the message ID or quote the message.")
        try: 
            msg = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await r(ctx, "Message not found. Make sure the message is in **this** channel.")
        await r(ctx, f'**{msg.author}: ```{msg.content}```')


@bot.command()
async def pin(ctx):
    """Pins a replied message in the channel."""
    if ctx.guild.id == 856613891227910194:
        if ctx.message.reference:
            message = await ctx.channel.fetch_message(ctx.message.reference.resolved.id)
            await message.pin(reason=f'Requested by {ctx.author}')
        else:
            await r(ctx, "Please reply to a message to do that. Example: https://acatia.needs.rest/kqh6kwe1h9a")
    else:
        await r(ctx, "Cannot do that in this server. Sorry.")

@bot.command(hidden=True, name='eval', aliases=['e'])
@commands.is_owner()
async def _eval(ctx, *, body: str):
    # Code taken from R. Danny.
    env = {
        'bot': bot,
        'ctx': ctx,
        'channel': ctx.channel,
        'author': ctx.author,
        'guild': ctx.guild,
        'message': ctx.message,
        '_': None
    }

    env.update(globals())

    body = util.cleanup_code(body)
    
    stdout = io.StringIO()

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    try:
        exec(to_compile, env)
    except Exception as e:
        return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

    func = env['func']
    try:
        with redirect_stdout(stdout):
            ret = await func()
    except Exception as e:
        value = stdout.getvalue()
        await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
    else:
        value = stdout.getvalue()
        try:
            await ctx.message.add_reaction('\u2705')
        except:
            pass

        if ret is None:
            if value:
                await ctx.send(f'```py\n{value}\n```')
        else:
            await ctx.send(f'```py\n{value}{ret}\n```')
    
@bot.command()
async def announcement(ctx, bot: typing.Union[discord.Member, discord.User]):
    """Gets a bot announcement (if it has one)"""
    plonked = await is_plonked(ctx.author.id)
    if plonked:
        return
        
    data = await make_request("https://www.motiondevelopment.top/api/v1.2/bots/", bot.id)
    print(data)
    announcement = data["annoucements"]
    print(bool(announcement))
    e = discord.Embed(color=0xfecdea, title=f'Announcement ID: {announcement["post_id"]}')
    if announcement != False:
        e.add_field(
            name=f'{announcement["post_title"]}',
            value=announcement["post_body"]
        )
        e.description = f"Post created by {data['owner_name']} ({data['owner_id']})"
    else: 
        e.description = 'This bot doesn\'t have an announcement. :cry:'

    await em(ctx, embed=e)

@bot.event
async def on_message_delete(message):
    if message.guild.id != 856613891227910194:
        return
    channel = message.guild.get_channel(877941140823891999)
    await channel.send(f'{message.author} deleted: ```{message.content}```')
    
@bot.command()
@commands.cooldown(1, 60, commands.BucketType.guild)
async def cleanup(ctx, search=100):
    """Cleans up the bot's message from the channel.
    
    If the invoker has Manage Messages, you can search up to 1000 messages whereas regular members can only clean up to 25.
    
    Credit to R. Danny."""
    
    try:
        plonked = await is_plonked(ctx.author.id)
        if plonked:
            return

        is_mod = ctx.channel.permissions_for(ctx.author).manage_messages

        strategy = util._basic_cleanup_strategy

        if is_mod:
            search = min(max(2, search), 150)
            strategy = util._user_cleanup_strategy
        else:
            search = min(max(2, search), 25)
            strategy = util._user_cleanup_strategy

        spammers = await strategy(ctx, search)

        deleted = sum(spammers.values())
        f'{deleted} message{" was" if deleted==1 else "s were"} removed.'

        await r(ctx, f'{deleted} message{" was" if deleted==1 else "s were"} removed.')
    except Exception as e:
        print(e)

@bot.command()
async def parsetoken(ctx, token: str):
    try:
        plonked = await is_plonked(ctx.author.id)
        if plonked:
            return
        
        token_part = token.split(".")
        if len(token_part) != 3:
            return await r(ctx, 'Invalid token.')

        def decode_user(user: str) -> str:
            user_bytes = user.encode()
            user_id_decoded = base64.b64decode(user_bytes)
            return user_id_decoded.decode("ascii")
        
        def parse_date(token: str) -> datetime.datetime:
            bytes_int = base64.standard_b64decode(token + "==")
            decoded = int.from_bytes(bytes_int, "big")
            timestamp = datetime.datetime.utcfromtimestamp(decoded)

            return timestamp

        str_id = util.call(decode_user, token_part[0])

        timestamp = parse_date(token_part[1]) or "Invalid date"

        user_id = int(str_id)

        member = await bot.fetch_user(user_id) 

        if not str_id or not str_id.isdigit():
            return await r(ctx, f"Invalid user.")

        e = discord.Embed(
            title=f"{member}'s token info",
            color=0xfecdea
        )
        e.description=f"""
        User: {member} ({member.id})
        Bot: {member.bot}
        Created: {util.format_longdatetime(member.created_at)}
        Token created: {timestamp}
        Please ensure this token has been invalidated.
        """
        e.set_thumbnail(url=member.avatar.url)

        class InvalidateToken(discord.ui.View):
            def __init__(self):
                super().__init__()
                self.value = None
                self.ctx = ctx

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if interaction.user.id != self.ctx.author.id:
                    return False
                else:
                    return True

            @discord.ui.button(label='Invalidate token', style=discord.ButtonStyle.blurple)
            async def invalidate(self, button: discord.ui.Button, interaction: discord.Interaction):
                self.value = True
                button.disabled = True
                self.stop()
            
        view = InvalidateToken()
        
        msg = await ctx.send(embed=e, view=view)
        
        await view.wait()
        if view.value:
            gist = await util.create_gist(ctx.message, content=token, reason='Automatic token invalidation (requested by user)')
            await msg.edit(content=f'ℹ️ **Token has been sent to <{gist}> for invalidation**')
        else:
            pass
    except Exception as e:
        print(e)

@bot.command(hidden=True)
@commands.is_owner()
async def plonk(ctx, user: typing.Union[discord.Member, discord.User], *, reason=None):
    """Bans someone from using the bot."""
    await bot.plonk.upsert({"_id": user.id, "reason": str(reason) if reason else str("No reason given")})
    await r(ctx, f'Plonked **{user}**')

@bot.command(hidden=True)
@commands.is_owner()
async def unplonk(ctx, user: typing.Union[discord.Member, discord.User]):
    """Unbans someone from using the bot."""
    await bot.plonk.delete(user.id)
    await r(ctx, f'Unplonked **{user}**')

@bot.command(hidden=True)
@commands.is_owner()
async def whyplonked(ctx, user: typing.Union[discord.Member, discord.User]):
    """Checks why someone was plonked"""
    data = await bot.plonk.find(user.id)
    if not data:
        return await r(ctx, f"{user} is not plonked.")
    
    await r(ctx, f"**{user} was plonked for:**\n{data['reason']}")
        
@bot.command(aliases=['init'])
async def initialize(ctx):
    class InteractiveCalculatorView(discord.ui.View):
        def __init__(self):
            super().__init__()
            self.timeout = 300
            self.to_calc = []
            self.answer = None
            self.ctx = ctx
            self.msg = None
            self.disable_toggle = False

        async def on_timeout(self) -> None:
            for item in self.children:
                item.disabled = True

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if self.ctx.author.id != interaction.user.id:
                await interaction.response.send_message("This isn't yours to control.", ephemeral=True)
                return False
            else:
                return True

        @discord.ui.button(style=discord.ButtonStyle.grey, label='7', row=1)
        async def btn_seven(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(7)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.grey, label='8', row=1)
        async def btn_eight(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(8)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.grey, label='9', row=1)
        async def btn_nine(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(9)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.blurple, label=' + ', row=1)
        async def btn_add(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append("+")
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.red, label='Clear', row=1)
        async def btn_clear(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.clear()
            await self.msg.edit(embed=self.consistent_embed(self.ctx, f"Output shown here"))

        @discord.ui.button(style=discord.ButtonStyle.grey, label='4', row=2)
        async def btn_four(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(4)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.grey, label='5', row=2)
        async def btn_five(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(5)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.grey, label='6', row=2)
        async def btn_six(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(6)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.blurple, label=' - ', row=2)
        async def btn_minus(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append("-")
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.red, label='Kill', row=2)
        async def btn_kill(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.clear()
            await self.msg.edit(content='This calculator has been disabled.', embed=None)
            for item in self.children:
                item.disabled = True
            self.stop()
            self.disable_toggle = True

        @discord.ui.button(style=discord.ButtonStyle.grey, label='1', row=3)
        async def btn_one(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(1)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.grey, label='2', row=3)
        async def btn_two(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(2)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.grey, label='3', row=3)
        async def btn_three(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(3)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.blurple, label=' ÷ ', row=3)
        async def btn_divide(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append("/")
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.blurple, label=' . ', row=3)
        async def btn_decimal(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(".")
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.grey, label=' 0 ', row=4)
        async def btn_zero(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(0)
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.blurple, label=' ( ', row=4)
        async def btn_openbracket(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append("(")
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.blurple, label=' ) ', row=4)
        async def btn_closedbracket(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append(")")
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.blurple, label=' × ', row=4)
        async def btn_multiply(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.to_calc.append("*")
            await self.update_content()

        @discord.ui.button(style=discord.ButtonStyle.green, label=' = ', row=4)
        async def btn_enter(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self.enter()

        def consistent_embed(self, context: commands.Context, content: str):
            embed = discord.Embed(
                description=f"```yaml\n{content}```",
                color=discord.Colour.blurple()
            )
            embed.set_author(name=context.author, icon_url=context.author.avatar.url)

            return embed

        async def enter(self):
            to_calc = "".join(str(x) for x in self.to_calc)
            if "**" in to_calc:
                self.answer = "Disallowed operator: **"
            else:
                try:
                    ans = eval(to_calc)
                    self.answer = "{:,}".format(ans)
                except ZeroDivisionError:
                    self.answer = "❎ Cannot divide by zero"
                except SyntaxError:
                    self.answer = "❎ Syntax Error"
                except Exception:
                    self.answer = "❎ Error"
                except SyntaxWarning:
                    self.answer = "❎ Error"

            await self.msg.edit(embed=self.consistent_embed(self.ctx, f"{to_calc} = {self.answer}"))

        async def update_content(self):
            to_calc = "".join(str(x) for x in self.to_calc)
            return await self.msg.edit(embed=self.consistent_embed(self.ctx, to_calc))

    msg = await ctx.send("Loading calculator...")
    view = InteractiveCalculatorView()
    view.msg = msg
    embed = discord.Embed(
        description=f"```yaml\nOutput shown here```",
        color=discord.Colour.blurple()
    )
    embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)

    await msg.edit(embed=embed, view=view, content=None)

    await view.wait()
    if view.disable_toggle:
        await msg.edit(view=view)

@cleanup.error
async def on_cleanup_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        return await r(ctx, "This command can only be used once a minute.")


if __name__ == "__main__":
    bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(DB_URI))
    bot.db = bot.mongo["RockBot"]
    bot.reminders = Document(bot.db, "reminders")
    bot.highlight = Document(bot.db, "highlight")
    bot.plonk = Document(bot.db, "plonk")
    
    bot.run(BOT_TOKEN)
