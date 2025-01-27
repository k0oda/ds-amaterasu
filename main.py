import discord
import json
import sys
import traceback
import logging

from discord import app_commands
from asyncio import sleep
from datetime import datetime
from pathlib import Path

from settings import *

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

_logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.guild_messages = True
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Service Functions
#

async def update_members_counter(member):
    await sleep(60*10)
    channel = client.get_channel(MEMBERS_COUNTER_CHANNEL)
    await channel.edit(name=f'Всего Участников: {member.guild.member_count}')


async def save_view(view_filename: str, views: dict):
    file_path = Path.cwd().absolute() / 'db' / f'{view_filename}.json'
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch(exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(views, f)


async def delete_view(view_filename: str, view_ids: list[int]):
    file_path = Path.cwd().absolute() / 'db' / f'{view_filename}.json'
    with open(file_path, 'r') as f:
        views = json.load(f)
    for view in views:
        if view['message_id'] in view_ids:
            views.remove(view)
            break
    with open(file_path, 'w') as f:
        json.dump(views, f)


def load_view(view_filename: str):
    try:
        file_path = Path.cwd().absolute() / 'db' / f'{view_filename}.json'
        with open(file_path, 'r') as f:
            if f.read(1) == '':
                _logger.info("Файл пуст, возвращаем пустой список")
                return []
            f.seek(0)
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        _logger.info(f"Ошибка чтения JSON: {e}")
        return []

# Views
#

class TicketNotificationView(discord.ui.View):
    def __init__(self, ticket_channel_id: int, *args, **kwargs):
        super().__init__(timeout=None)
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
    def __init__(self, notification_id: discord.Message, *args, **kwargs):
        super().__init__(timeout=None)
        self.close_confirmation_message = None
        self.notification = client.get_channel(NOTIFICATIONS_CHANNEL).get_partial_message(notification_id)
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
            embed = discord.Embed(description=f'🔔 {i.user.mention} вызвал Руководство.', color=WARNING_COLOR)
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
    def __init__(self, label: str, style: str, channel_prefix: str, *args, **kwargs):
        super().__init__(timeout=None)
        self.label = label
        self.style = discord.ButtonStyle[style]
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

            notification_views.append({
                'message_id': notification.id,
                'channel_id': notifications.id,
                'ticket_channel_id': channel.id,
            })
            await save_view(NOTIFICATIONS_FILENAME, notification_views)

            embed = discord.Embed(title=f'キヲツケ {i.user.name}!', description='Спасибо за отправку тикета!\nРуководство скоро свяжется с вами.\nПожалуйста, в подробностях распишите суть вашего обращения.\n\nЕсли вам никто не ответил вы можете нажать кнопку `🔔 Вызвать Руководство`', color=INVISIBLE_COLOR)
            embed.set_thumbnail(url=i.user.avatar)
            ticket_view = TicketView(notification_id=notification.id)
            message = await channel.send(i.user.mention, embed=embed, view=ticket_view)
            ticket_views.append({
                'message_id': message.id,
                'channel_id': channel.id,
                'notification_id': notification.id,
            })
            await save_view(TICKETS_FILENAME, ticket_views)
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


notification_views = load_view(NOTIFICATIONS_FILENAME)
ticket_views = load_view(TICKETS_FILENAME)
ticket_form_views = load_view(TICKET_FORMS_FILENAME)


@client.event
async def on_ready():
    guild = client.get_guild(GUILD)
    if not guild:
        _logger.error(f"Сервер с ID {GUILD} не найден")
        return

    await tree.sync(guild=guild)
    _logger.info(f"Синхронизация команд завершена для сервера {guild.name}")

    async def process_views(view_data_list: list, view_class: discord.ui.View, view_filename: str, **kwargs):
        views_to_delete = []
        for view_data in view_data_list:
            try:
                channel = client.get_channel(view_data['channel_id'])
                if not channel:
                    _logger.warning(f"Канал с ID {view_data['channel_id']} не найден")
                    continue

                message = await channel.fetch_message(view_data['message_id'])
                view = view_class(**view_data, **kwargs)
                await message.edit(view=view)
                _logger.info(f"View восстановлено для сообщения {view_data['message_id']} в канале {channel.name}")
                await sleep(3)
            except discord.NotFound:
                _logger.warning(f'Сообщение с ID {view_data["message_id"]} не найдено.')
                views_to_delete.append(view_data['message_id'])
            except discord.HTTPException as e:
                _logger.error(f'Ошибка при редактировании сообщения: {e}')
        await delete_view(view_filename, views_to_delete)

    await process_views(
        notification_views,
        TicketNotificationView,
        NOTIFICATIONS_FILENAME,
    )

    await process_views(
        ticket_views,
        TicketView,
        TICKETS_FILENAME,
    )

    await process_views(
        ticket_form_views,
        TicketFormView,
        TICKET_FORMS_FILENAME,
    )

    _logger.info(guild.name)


@client.event
async def on_error(event, *args, **kwargs):
    _logger.error(f"Произошла ошибка в событии: {event}")

    _logger.error(f"Аргументы: {args}")
    _logger.error(f"Ключевые аргументы: {kwargs}")

    error_traceback = traceback.format_exc()
    if error_traceback:
        _logger.error(f"Трассировка ошибки:\n{error_traceback}")
    else:
        _logger.error("Трассировка ошибки недоступна.")

    if event == 'on_message':
        message = args[0]
        _logger.error(f"Сообщение: {message.content}, Автор: {message.author}, Канал: {message.channel}")
    elif event == 'on_command_error':
        error = args[0]
        ctx = error.ctx
        _logger.error(f"Ошибка в команде: {ctx.command}, Пользователь: {ctx.author}, Сервер: {ctx.guild}")

    exc_info = kwargs.get('exc_info')
    if exc_info:
        _logger.error(f"Тип ошибки: {exc_info[0].__name__}, Сообщение: {exc_info[1]}")


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
async def post_regulations(i: discord.Interaction):
    if not i.user.guild_permissions.administrator:
        await i.response.send_message('У вас недостаточно прав для использования этой команды.', delete_after=3, ephemeral=True)
        return

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
async def post_army_regulations(i: discord.Interaction):
    if not i.user.guild_permissions.administrator:
        await i.response.send_message('У вас недостаточно прав для использования этой команды.', delete_after=3, ephemeral=True)
        return

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
    if not i.user.guild_permissions.administrator:
        await i.response.send_message('У вас недостаточно прав для использования этой команды.', delete_after=3, ephemeral=True)
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=INVISIBLE_COLOR,
    )
    channel = client.get_channel(TICKET_FORMS_CHANNEL)
    form_label = 'Отправить'
    form_style = discord.ButtonStyle[style.value]
    form_channel_prefix = channel_prefix
    view = TicketFormView(label=form_label, style=form_style, channel_prefix=form_channel_prefix)
    message = await channel.send(embed=embed, view=view)

    ticket_form_views.append({
        'message_id': message.id,
        'channel_id': channel.id,
        'label': form_label,
        'style': form_style.name,
        'channel_prefix': form_channel_prefix,
    })
    await save_view(TICKET_FORMS_FILENAME, ticket_form_views)

    await i.response.send_message(f'Форма [{title}]({message.jump_url}) была создана.', delete_after=3, ephemeral=True)


@tree.command(name='post_order', description='Отправляет новый указ', guild=discord.Object(id=GUILD))
async def post_order(
    i: discord.Interaction,
    image_url: str = None,
):
    if not i.user.guild_permissions.administrator:
        await i.response.send_message('У вас недостаточно прав для использования этой команды.', delete_after=3, ephemeral=True)
        return

    modal = OrderModal(image_url)
    await i.response.send_modal(modal)


@tree.command(name='post_news', description='Отправляет новость', guild=discord.Object(id=GUILD))
async def post_news(
    i: discord.Interaction,
    image_url: str = None,
):
    if not i.user.guild_permissions.administrator:
        await i.response.send_message('У вас недостаточно прав для использования этой команды.', delete_after=3, ephemeral=True)
        return

    modal = NewsModal(image_url)
    await i.response.send_modal(modal)


@tree.command(name='post_symbolics', description='Добавляет новую символику', guild=discord.Object(id=GUILD))
async def post_symbolics(
    i: discord.Interaction,
    image_url: str = None,
):
    if not i.user.guild_permissions.administrator:
        await i.response.send_message('У вас недостаточно прав для использования этой команды.', delete_after=3, ephemeral=True)
        return    

    modal = SymbolicsModal(image_url)
    await i.response.send_modal(modal)

client.run(TOKEN)
