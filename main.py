'''
Confined Timeout
Main entry point.

Copyright (C) 2024  __retr0.init__

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''
import interactions
# Import the os module to get the parent path to the local files
import os
# aiofiles module is recommended for file operation
import aiofiles
import asyncio

from enum import Enum, unique
from dataclasses import dataclass
import datetime
from typing import Union, cast, Callable, Awaitable

import sqlalchemy
from sqlalchemy import select as sqlselect
from sqlalchemy import delete as sqldelete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker

from .model import GlobalAdminDB, ModeratorDB, PrisonerDB, DBBase

engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{os.path.dirname(__file__)}/confined_timeout_db.db")
Session = async_sessionmaker(engine)

@sqlalchemy.event.listens_for(engine.sync_engine, "connect")
def do_connect(dbapi_connection, connection_record):
    dbapi_connection.isolation_level = None

@sqlalchemy.event.listens_for(engine.sync_engine, "begin")
def do_begin(conn):
    conn.exec_driver_sql("BEGIN")

@unique
class MRCTType(int, Enum):
    USER = 1
    ROLE = 2

@dataclass
class GlobalAdmin:
    '''Global Admin Data Class'''
    __slots__ = ('id', 'type')
    id: int
    type: int

@dataclass
class ChannelModerator:
    '''Channel Moderator Data Class'''
    __slots__ = ('id', 'type', 'channel_id')
    id: int
    type: int
    channel_id: int

@dataclass
class Prisoner:
    '''Prinsoner Data Class'''
    __slots__ = ('id', 'release_datatime', 'channel_id')
    id: int
    release_datatime: datetime.datetime
    channel_id: int

GLOBAL_ADMIN_USER_CUSTOM_ID: str = "retr0init_confined_timeout_GlobalAdmin_user"
GLOBAL_ADMIN_ROLE_CUSTOM_ID: str = "retr0init_confined_timeout_GlobalAdmin_role"
CHANNEL_MODERATOR_USER_CUSTOM_ID: str = "retr0init_confined_timeout_ChannelModerator_user"
CHANNEL_MODERATOR_ROLE_CUSTOM_ID: str = "retr0init_confined_timeout_ChannelModerator_role"
TIMEOUT_DIALOG_CUSTOM_ID: str = "retr0init_confined_timeout_TimeoutDialog"

global_admins: list[GlobalAdmin] = []
channel_moderators: list[ChannelModerator] = []
prisoners: list[Prisoner] = []

async def my_admin_check(ctx: interactions.BaseContext) -> bool:
    '''
    Check whether the person has the global admin permission to run the command
    '''
    res: bool = await interactions.is_owner()(ctx)
    gadmin_user: GlobalAdmin = GlobalAdmin(ctx.author.id, MRCTType.USER)
    res_user: bool = gadmin_user in global_admins
    res_role: bool = any(map(lambda x: ctx.author.has_role(x.id) if x.type == MRCTType.ROLE else False, global_admins))

    return res or res_user or res_role

async def my_channel_moderator_check(ctx: interactions.BaseContext) -> bool:
    '''
    Check whether the member has the channel moderator permission to run the command
    '''
    channel_id: int = ctx.channel.id if not hasattr(ctx.channel, "parent_channel") else ctx.channel.parent_channel.id
    cmod_user: ChannelModerator = ChannelModerator(
        ctx.author.id,
        MRCTType.USER,
        channel_id
    )
    res_user: bool = cmod_user in channel_moderators
    res_role: bool = any(map(
        lambda x: ctx.author.has_role(x.id) if x.type == MRCTType.ROLE else False,
        (_ for _ in channel_moderators if _.channel_id == channel_id)
    ))
    return res_user or res_role

async def mycheck_or(*check_funcs: Callable[..., Awaitable[bool]]) -> Callable[..., Awaitable[bool]]:
    async def func(ctx: interactions.BaseContext) -> bool:
        for check_func in check_funcs:
            if await check_func(ctx):
                return True
        return False

    return func

async def mycheck_and(*check_funcs: Callable[..., Awaitable[bool]]) -> Callable[..., Awaitable[bool]]:
    async def func(ctx: interactions.BaseContext) -> bool:
        for check_func in check_funcs:
            if not await check_func(ctx):
                return False
        return True

    return func

'''
Confined Timeout Module
'''
class ModuleRetr0initConfinedTimeout(interactions.Extension):
    module_base: interactions.SlashCommand = interactions.SlashCommand(
        name="confined_timeout",
        description="Confined timeout"
    )
    module_group_setting: interactions.SlashCommand = module_base.group(
        name="setting",
        description="Settings of the Confined Timeout system"
    )

    def __init__(self, bot):
        asyncio.create_task(self.async_init())

    async def async_init(self) -> None:
        '''Read all data into local list'''
        global global_admins
        global channel_moderators
        global prisoners
        async with engine.begin() as conn:
            await conn.run_sync(DBBase.metadata.create_all)
        async with Session() as conn:
            gas = await conn.execute(sqlselect(GlobalAdminDB))
            cms = await conn.execute(sqlselect(ModeratorDB))
            ps  = await conn.execute(sqlselect(PrisonerDB))
        global_admins = [GlobalAdmin(ga[0].id, ga[0].type) for ga in gas]
        channel_moderators = [ChannelModerator(cm[0].id, cm[0].type, cm[0].channel_id) for cm in cms]
        prisoners = [Prisoner(p[0].id, p[0].release_datatime, p[0].channel_id) for p in ps]

    async def async_start(self) -> None:
        await asyncio.sleep(30)
        cdt: datetime.datetime = datetime.datetime.now()
        for p in prisoners:
            if cdt >= p.release_datatime:
                # Release the prinsoner
                await self.release_prinsoner(p)
    
    def drop(self):
        asyncio.create_task(self.async_drop())
        super().drop()
    
    async def async_drop(self):
        '''
        Dispose the Database Engine connection
        '''
        await engine.dispose()

    async def release_prinsoner(self, prisoner: Prisoner) -> None:
        if prisoner not in prisoners:
            return
        channel: interactions.GuildChannel = await self.bot.fetch_channel(prisoner.channel_id)
        user: interactions.User = await self.bot.fetch_user(prisoner.id)
        try:
            await channel.delete_permission(user, f"Member {user.display_name}({user.id}) is released from Channel {channel.name} timeout.")
        except interactions.errors.Forbidden:
            print("The bot needs to have enough permissions!")
            return
        prisoners.remove(prisoner)
        async with Session() as session:
            await session.execute(
                sqldelete(PrisonerDB).
                where(sqlalchemy.and_(
                    PrisonerDB.id == prisoner.id,
                    PrisonerDB.channel_id == prisoner.channel_id
                ))
            )
            await session.commit()

    def check_prisoner(self, prisoner_member: interactions.Member, duration_minutes: int, channel: Union[interactions.GuildChannel, interactions.ThreadChannel]) -> tuple[bool, Prisoner]:
        channel_id: int = channel.id if not hasattr(channel, "parent_channel") else channel.parent_channel.id
        prisoner: Prisoner = Prisoner(prisoner_member.id, datetime.datetime.now() + datetime.timedelta(minutes=duration_minutes), channel_id)
        cp: list[Prisoner] = [p for p in prisoners if p.id == prisoner.id and p.channel_id == prisoner.channel_id]
        return len(cp) > 0, prisoner

    async def jail_prisoner(self, prisoner_member: interactions.Member, duration_minutes: int, channel: Union[interactions.GuildChannel, interactions.ThreadChannel]) -> bool:
        existed, prisoner = self.check_prisoner(prisoner_member, duration_minutes, channel)
        if existed:
            return False
        # Test whether the channel is a ForumPost channel
        try:
            if hasattr(channel, "parent_channel"):
                # ForumPost, get its parent channel
                await channel.parent_channel.add_permission(prisoner_member, deny=[
                    interactions.Permissions.CREATE_POSTS,
                    interactions.Permissions.SEND_MESSAGES,
                    interactions.Permissions.SEND_MESSAGES_IN_THREADS,
                    interactions.Permissions.SEND_TTS_MESSAGES,
                    interactions.Permissions.SEND_VOICE_MESSAGES,
                    interactions.Permissions.ADD_REACTIONS,
                    interactions.Permissions.ATTACH_FILES,
                    interactions.Permissions.CREATE_INSTANT_INVITE,
                    interactions.Permissions.MENTION_EVERYONE,
                    interactions.Permissions.MANAGE_MESSAGES,
                    interactions.Permissions.MANAGE_THREADS,
                    interactions.Permissions.MANAGE_CHANNELS
                ], reason=f"Member {prisoner_member.display_name}({prisoner_member.id}) timeout for {duration_minutes} minutes in Channel {channel.parent_channel.name}")
            else:
                # Normal Text channel
                await channel.parent_channel.add_permission(prisoner_member, deny=[
                    interactions.Permissions.SEND_MESSAGES,
                    interactions.Permissions.SEND_MESSAGES_IN_THREADS,
                    interactions.Permissions.SEND_TTS_MESSAGES,
                    interactions.Permissions.SEND_VOICE_MESSAGES,
                    interactions.Permissions.ADD_REACTIONS,
                    interactions.Permissions.ATTACH_FILES,
                    interactions.Permissions.CREATE_INSTANT_INVITE,
                    interactions.Permissions.MENTION_EVERYONE,
                    interactions.Permissions.MANAGE_MESSAGES,
                    interactions.Permissions.MANAGE_THREADS,
                    interactions.Permissions.MANAGE_CHANNELS
                ], reason=f"Member {prisoner_member.display_name}({prisoner_member.id}) timeout for {duration_minutes} minutes in Channel {channel.name}")
        except interactions.errors.Forbidden:
            print("The bot needs to have enough permissions!")
            return False
        prisoners.append(prisoner)
        async with Session() as session:
            session.add(PrisonerDB(
                id = prisoner.id,
                channel_id = prisoner.channel_id,
                release_datatime = prisoner.release_datatime
            ))
            await session.commit()
        # Wait for a certain number of time and unblock the member
        await asyncio.sleep(duration_minutes * 60.0)
        await self.release_prinsoner(prinsoner=prisoner)
        return True

    

    @module_group_setting.subcommand("set_global_admin", sub_cmd_description="Set the Global Admin")
    @interactions.slash_option(
        name = "set_type",
        description = "Type of the admin",
        required = True,
        opt_type = interactions.OptionType.INTEGER,
        choices = [
            interactions.SlashCommandChoice(name="User", value=MRCTType.USER),
            interactions.SlashCommandChoice(name="Role", value=MRCTType.ROLE)
        ]
    )
    @interactions.check(my_admin_check)
    async def module_group_setting_setGlobalAdmin(self, ctx: interactions.SlashContext, set_type: int) -> None:
        '''
        Pop a User Select Menu ephemeral to choose. It will disappear once selected.
        It will check whether the user or role is capable of the admin
        '''
        component_user: interactions.UserSelectMenu = interactions.UserSelectMenu(
            custom_id=GLOBAL_ADMIN_USER_CUSTOM_ID,
            placeholder="Select the user for global admin",
            max_values=25,
            default_values=[ctx.guild.get_member(_.id) for _ in global_admins if _.type == MRCTType.USER]
        )
        component_role: interactions.RoleSelectMenu = interactions.RoleSelectMenu(
            custom_id=GLOBAL_ADMIN_ROLE_CUSTOM_ID,
            placeholder="Select the role for global admin",
            max_values=25,
            default_values=[ctx.guild.get_role(_.id) for _ in global_admins if _.type == MRCTType.ROLE]
        )
        match set_type:
            case MRCTType.USER:
                await ctx.send("Set the global admin USER:", components=[component_user])
            case MRCTType.ROLE:
                await ctx.send("Set the global admin ROLE:", components=[component_role])

    @interactions.component_callback(GLOBAL_ADMIN_USER_CUSTOM_ID)
    async def callback_component_user(self, ctx: interactions.ComponentContext) -> None:
        if await my_admin_check(ctx):
            message: interactions.Message = ctx.message
            msg_to_send: str = "Added global admin:"
            for user in ctx.values:
                cast(interactions.Member, user)
                if user.bot:
                    continue
                _to_add: GlobalAdmin = GlobalAdmin(user.id, MRCTType.USER)
                if _to_add not in global_admins:
                    global_admins.append(_to_add)
                    async with Session() as conn:
                        conn.add(
                            GlobalAdminDB(id=_to_add.id, type=_to_add.type)
                        )
                        await conn.commit()
                    msg_to_send += f"\n- {user.display_name} {user.mention}"
            await ctx.send(msg_to_send)
            await message.delete()
            return
        await ctx.send("You do not the permission to do so!", ephemeral=True)

    #TODO callback of component role
    #TODO modify the original library code: https://github.com/interactions-py/interactions.py/pull/1654

    @module_base.subcommand("pong", sub_cmd_description="Replace the description of this command")
    @interactions.slash_option(
        name = "option_name",
        description = "Option description",
        required = True,
        opt_type = interactions.OptionType.STRING
    )
    async def module_base_pong(self, ctx: interactions.SlashContext, option_name: str):
        await ctx.send(f"Pong {option_name}!")