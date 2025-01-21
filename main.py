import discord
import json
import os

from discord import app_commands
from discord.ext import commands
from asyncio import sleep
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.guild_messages = True
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

REGULATIONS_PATH = 'regulations.json'
ARMY_REGULATIONS_PATH = 'army_regulations.json'

TOKEN = os.getenv("TOKEN")
GUILD = 730393851524808764

# Colors
#

WARNING_COLOR = 0xf3ae19
INVISIBLE_COLOR = 0x2e2b2b

# Roles
#

ADMIN_ROLES = (849987497400467466, 892335197410951179)
TICKETS_RESPONDER_ROLES = (849987497400467466, 892335197410951179, 1077221347970777140, 1076958728399618098)

COLOR_OVERRIDE_ROLE = 877250538134175774
STATUS_ROLE = 877240157542170684
ACHIEVEMENTS_ROLE = 877238290871373855
TECH_ROLE = 877242944103530547

# Channels
#

MEMBERS_COUNTER_CHANNEL = 1331361549046255737
CLAN_MEBMERS_COUNTER_CHANNEL = 1331361710824751244

TICKETS_CATEGORY = 1331362077616377957
TICKET_FORMS_CHANNEL = 1331362350497792123

NOTIFICATIONS_CHANNEL = 1331362764584783945
ORDERS_CHANNEL = 1331355614386978947
NEWS_CHANNEL = 1331353827017752688
SYMBOLICS_CHANNEL = 1331353039868788776
REGULATIONS_CHANNEL = 1331355456605650964
ARMY_REGULATIONS_CHANNEL = 1076969784182325410

# Service Functions
#

async def update_members_counter(member):
    await sleep(60*10)
    channel = client.get_channel(MEMBERS_COUNTER_CHANNEL)
    await channel.edit(name=f'Всего Участников: {member.guild.member_count}')

# Views
#

class TicketNotificationView(discord.ui.View):
    def __init__(self, ticket_channel_id: int):
        super().__init__()
        self.ticket_channel_id = ticket_channel_id
        self.add_buttons()

    def add_buttons(self):
        guild = client.get_guild(GUILD)

        async def confirm_close(i: discord.Interaction):
            await guild.get_channel(self.ticket_channel_id).delete()
            await self.close_confirmation_message.delete()
            embed = discord.Embed(description=f'🔐 {i.user.mention} закрыл тикет', color=INVISIBLE_COLOR)
            await i.response.send_message(embed=embed)

        async def cancel_close(i: discord.Interaction):
            self.remove_item(confirm_button)
            self.remove_item(cancel_button)
            self.add_item(see_button)
            self.add_item(close_button)
            await i.message.edit(embeds=i.message.embeds, view=self)
            await self.close_confirmation_message.delete()
            await i.response.defer()

        async def close_ticket(i: discord.Interaction):
            self.remove_item(see_button)
            self.remove_item(close_button)
            self.add_item(confirm_button)
            self.add_item(cancel_button)
            await i.message.edit(embeds=i.message.embeds, view=self)
            await i.response.send_message('Вы уверены что хотите закрыть этот тикет?', ephemeral=True)
            self.close_confirmation_message = await i.original_response()

        see_button = discord.ui.Button(label='Посмотреть', emoji='🔍', url=f'https://discord.com/channels/{guild.id}/{self.ticket_channel_id}')

        close_button = discord.ui.Button(label='Закрыть', emoji='🔐', style=discord.ButtonStyle.danger)
        close_button.callback = close_ticket

        confirm_button = discord.ui.Button(label='Подтвердить', style=discord.ButtonStyle.success)
        confirm_button.callback = confirm_close

        cancel_button = discord.ui.Button(label='Отменить', style=discord.ButtonStyle.danger)
        cancel_button.callback = cancel_close

        self.add_item(see_button)
        self.add_item(close_button)

class TicketView(discord.ui.View):
    def __init__(self, notification: discord.Message):
        super().__init__()
        self.close_confirmation_message = None
        self.notification = notification
        self.add_buttons()

    def add_buttons(self):
        async def confirm_close(i: discord.Interaction):
            await i.channel.delete()
            embed = discord.Embed(description='🔐 Пользователь закрыл этот тикет', color=INVISIBLE_COLOR)
            await self.notification.reply(embed=embed)
            view = discord.ui.View.from_message(self.notification)
            view.clear_items()
            await self.notification.edit(embeds=self.notification.embeds, view=view)

        async def cancel_close(i: discord.Interaction):
            self.remove_item(confirm_button)
            self.remove_item(cancel_button)
            self.add_item(close_button)
            self.add_item(call_button)
            await i.message.edit(embeds=i.message.embeds, view=self)
            await self.close_confirmation_message.delete()
            await i.response.defer()

        async def close_ticket(i: discord.Interaction):
            self.remove_item(close_button)
            self.remove_item(call_button)
            self.add_item(confirm_button)
            self.add_item(cancel_button)
            await i.message.edit(embeds=i.message.embeds, view=self)
            await i.response.send_message('Вы уверены что хотите закрыть этот тикет?', ephemeral=True)
            self.close_confirmation_message = await i.original_response()

        async def call_team(i: discord.Interaction):
            embed = discord.Embed(description=f'🔔 {i.user.mention} has called the team', color=WARNING_COLOR)
            roles_mention = ' '.join(f'<@&{role}>' for role in TICKETS_RESPONDER_ROLES)
            await i.channel.send(roles_mention, embed=embed, delete_after=20)
            await i.response.defer()

        close_button = discord.ui.Button(label='Закрыть Тикет', emoji='🔐', style=discord.ButtonStyle.danger)
        close_button.callback = close_ticket

        call_button = discord.ui.Button(label='Вызвать Руководство', emoji='🔔', style=discord.ButtonStyle.primary)
        call_button.callback = call_team

        confirm_button = discord.ui.Button(label='Подтвердить', style=discord.ButtonStyle.success)
        confirm_button.callback = confirm_close

        cancel_button = discord.ui.Button(label='Отменить', style=discord.ButtonStyle.danger)
        cancel_button.callback = cancel_close

        self.add_item(close_button)
        self.add_item(call_button)

class TicketFormView(discord.ui.View):
    def __init__(self, label: str, style: discord.ButtonStyle, channel_prefix: str):
        super().__init__()
        self.label = label
        self.style = style
        self.channel_prefix = channel_prefix
        self.add_buttons()

    def add_buttons(self):
        async def create_channel(i: discord.Interaction):
            guild = client.get_guild(GUILD)
            category = discord.utils.get(guild.categories, id=TICKETS_CATEGORY)
            allow_overwrite = discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                send_messages=True,
            )
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel = False,
                    read_messages = False,
                    send_messages = False,
                ),
                i.user: allow_overwrite,
            }
            for role_id in TICKETS_RESPONDER_ROLES:
                role = guild.get_role(role_id)
                overwrites[role] = allow_overwrite
            channel = await guild.create_text_channel(name=f'└┃ {self.channel_prefix}-{i.user.name}', category=category, overwrites=overwrites)

            notifications = guild.get_channel(NOTIFICATIONS_CHANNEL)
            notification_view = TicketNotificationView(channel.id)
            notification_embed = discord.Embed(title='Новый Тикет', description=f'{i.user.mention} создал новый Тикет с префиксом {self.channel_prefix}\n\n<#{channel.id}>', color=INVISIBLE_COLOR)
            notification_embed.set_thumbnail(url=i.user.avatar)
            notification = await notifications.send(embed=notification_embed, view=notification_view)

            embed = discord.Embed(title=f'Hi {i.user.name}!', description='Спасибо за отправку тикета!\nРуководство скоро свяжется с вами.\nПожалуйста, в подробностях распишите суть вашего обращения.\n\nЕсли вам никто не ответил вы можете нажать кнопку `🔔 Вызвать Руководство`', color=INVISIBLE_COLOR)
            embed.set_thumbnail(url=i.user.avatar)
            ticket_view = TicketView(notification=notification)
            message = await channel.send(i.user.mention, embed=embed, view=ticket_view)
            await message.pin()
            await i.response.send_message(f'Канал {channel.mention} создан.', delete_after=15, ephemeral=True)

        button = discord.ui.Button(label=self.label, style=self.style)
        button.callback = create_channel
        self.add_item(button)

# Modals
#

class OrderModal(discord.ui.Modal):
    def __init__(self, image_url=None):
        super().__init__(title='Новый Указ')

        self.name = discord.ui.TextInput(
            label='Заголовок',
            min_length=3,
            max_length=100,
        )
        self.add_item(self.name)

        self.description = discord.ui.TextInput(
            label='Описание',
            style=discord.TextStyle.paragraph,
            placeholder='Описание',
            required=True,
        )
        self.add_item(self.description)

        self.image_url = image_url

    async def on_submit(self, i: discord.Interaction):
        embed = discord.Embed(
            title=f'Указ {self.name}',
            description=f'{self.description}',
            timestamp=datetime.utcnow(),
            color=INVISIBLE_COLOR,
        )
        if self.url.value != '':
            embed.url = self.url.value
        embed.set_image(url=self.image_url)
        channel = client.get_channel(ORDERS_CHANNEL)
        await channel.send(embed=embed)
        await i.response.send_message(f'Указ {self.name.value} был успешно создан.', delete_after=3, ephemeral=True)


class NewsModal(discord.ui.Modal):
    def __init__(self, image_url=None):
        super().__init__(title='Создание Новости')

        self.name = discord.ui.TextInput(
            label='Заголовок',
            min_length=3,
            max_length=100,
        )
        self.add_item(self.name)

        self.url = discord.ui.TextInput(
            label='URL для заголовка',
            placeholder='https://',
            required=False,
        )
        self.add_item(self.url)

        self.description = discord.ui.TextInput(
            label='Описание',
            style=discord.TextStyle.paragraph,
            placeholder='Описание',
            required=True,
        )
        self.add_item(self.description)

        self.image_url = image_url

    async def on_submit(self, i: discord.Interaction):
        embed = discord.Embed(
            title=f'{self.name}',
            description=f'{self.description}',
            timestamp=datetime.utcnow(),
            color=INVISIBLE_COLOR,
        )
        if self.url.value != '':
            embed.url = self.url.value
        embed.set_image(url=self.image_url)
        channel = client.get_channel(NEWS_CHANNEL)
        message = await channel.send(embed=embed)
        await i.response.send_message(f'Новость [{self.name.value}]({message.jump_url}) была успешно создана.', delete_after=3, ephemeral=True)


class SymbolicsModal(discord.ui.Modal):
    def __init__(self, image_url=None):
        super().__init__(title='Добавление Символики')

        self.name = discord.ui.TextInput(
            label='Заголовок',
            min_length=3,
            max_length=100,
        )
        self.add_item(self.name)

        self.description = discord.ui.TextInput(
            label='Описание',
            style=discord.TextStyle.paragraph,
            placeholder='Описание',
            required=True,
        )
        self.add_item(self.description)

        self.image_url = image_url

    async def on_submit(self, i: discord.Interaction):
        embed = discord.Embed(
            title=f'{self.name}',
            description=f'{self.description}',
            color=INVISIBLE_COLOR,
        )
        embed.set_image(url=self.image_url)
        channel = client.get_channel(SYMBOLICS_CHANNEL)
        await channel.send(embed=embed)
        await i.response.send_message(f'Символика {self.name.value} была успешно добавлена.', delete_after=3, ephemeral=True)


# Events
#

@client.event
async def on_ready():
    guild = client.get_guild(GUILD)
    await tree.sync(guild=guild)
    print(guild.name)

@client.event
async def on_member_join(member):
    guild = client.get_guild(GUILD)
    await update_members_counter(member)
    await member.add_roles(guild.get_role(COLOR_OVERRIDE_ROLE)) # Color Override Role
    await member.add_roles(guild.get_role(STATUS_ROLE)) # Status Category
    await member.add_roles(guild.get_role(ACHIEVEMENTS_ROLE)) # Achievements Category
    await member.add_roles(guild.get_role(TECH_ROLE)) # Tech Category

@client.event
async def on_member_remove(member):
    await update_members_counter(member)

# Commands
#

@tree.command(name='hello', description='Показывает что бот живой', guild=discord.Object(id=GUILD))
async def hello(i: discord.Interaction):
    await i.response.send_message(content=f'Hello, {i.user.name}!')


@tree.command(name='post_regulations', description='Удаляет предыдущий устав, форматирует и отправляет новый', guild=discord.Object(id=GUILD))
@commands.has_any_role(*ADMIN_ROLES)
async def post_regulations(i: discord.Interaction):
    rules_file = open(REGULATIONS_PATH, 'r')
    rules = json.load(rules_file)
    rules_file.close()
    embed = discord.Embed(
        title="Устав клана Асакура [ 朝倉家憲章 ]",
        color=INVISIBLE_COLOR,
    )
    for k, v in rules.items():
        embed.add_field(name=f"[{k}]", value=f"{v['title']}", inline=True)
        embed.add_field(name='━━━━', value=f"{v['description']}", inline=True)
        embed.add_field(name='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', value='\u200B', inline=False)
    embed.set_footer(
        text='Ваше членство в клане подразумевает принятие этого устава, включая все дальнейшие его изменения. Устав может быть изменен в любое время без уведомления, ваша ответственность — знать о них.'
    )
    channel = client.get_channel(REGULATIONS_CHANNEL)
    await channel.purge()
    message = await channel.send(embed=embed)
    await i.response.send_message(f'[Устав]({message.jump_url}) был отправлен.', delete_after=3, ephemeral=True)


@tree.command(name='post_army_regulations', description='Удаляет предыдущий армейский устав, форматирует и отправляет новый', guild=discord.Object(id=GUILD))
@commands.has_any_role(*ADMIN_ROLES)
async def post_army_regulations(i: discord.Interaction):
    rules_file = open(ARMY_REGULATIONS_PATH, 'r')
    rules = json.load(rules_file)
    rules_file.close()
    embed = discord.Embed(
        title="Устав Национального Полка клана Асакура [ 国立朝倉連隊憲章 ]",
        color=INVISIBLE_COLOR,
    )
    for k, v in rules.items():
        embed.add_field(name=f"[{k}]", value=f"{v['title']}", inline=True)
        embed.add_field(name='━━━━', value=f"{v['description']}", inline=True)
        embed.add_field(name='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', value='\u200B', inline=False)
    embed.set_footer(
        text='Данный устав относится исключительно к военному положению и не применяется в мирное время.'
    )
    channel = client.get_channel(ARMY_REGULATIONS_CHANNEL)
    await channel.purge()
    message = await channel.send(embed=embed)
    await i.response.send_message(f'[Устав]({message.jump_url}) был отправлен.', delete_after=3, ephemeral=True)


@tree.command(name='post_ticket_form', description='Отправляет новую форму для тикетов', guild=discord.Object(id=GUILD))
@commands.has_any_role(*ADMIN_ROLES)
@app_commands.choices(style=[
    app_commands.Choice(name='Primary', value='primary'),
    app_commands.Choice(name='Secondary', value='secondary'),
    app_commands.Choice(name='Success', value='success'),
    app_commands.Choice(name='Danger', value='danger'),
])
async def post_ticket_form(
        i: discord.Interaction,
        title: str, description: str,
        style: app_commands.Choice[str],
        channel_prefix: str
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=INVISIBLE_COLOR,
    )
    channel = client.get_channel(TICKET_FORMS_CHANNEL)
    view = TicketFormView(label='Отправить', style=discord.ButtonStyle[style.value], channel_prefix=channel_prefix)
    message = await channel.send(embed=embed, view=view)
    await i.response.send_message(f'Форма [{title}]({message.jump_url}) была создана.', delete_after=3, ephemeral=True)


@tree.command(name='post_order', description='Отправляет новый указ', guild=discord.Object(id=GUILD))
@commands.has_any_role(*ADMIN_ROLES)
async def post_order(
    i: discord.Interaction,
    image_url: str = None,
):
    modal = OrderModal(image_url)
    await i.response.send_modal(modal)


@tree.command(name='post_news', description='Отправляет новость', guild=discord.Object(id=GUILD))
@commands.has_any_role(*ADMIN_ROLES)
async def post_news(
    i: discord.Interaction,
    image_url: str = None,
):
    modal = NewsModal(image_url)
    await i.response.send_modal(modal)


@tree.command(name='post_symbolics', description='Добавляет новую символику', guild=discord.Object(id=GUILD))
@commands.has_any_role(*ADMIN_ROLES)
async def post_symbolics(
    i: discord.Interaction,
    image_url: str = None,
):
    modal = SymbolicsModal(image_url)
    await i.response.send_modal(modal)

client.run(TOKEN)
