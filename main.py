'''
Confined Timeout
Main entry point.
[WARNING] Modify the original library code: https://github.com/interactions-py/interactions.py/pull/1654

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
#WARNING Modify the original library code: https://github.com/interactions-py/interactions.py/pull/1654
import interactions
from interactions.ext.paginators import Paginator
# Import the os module to get the parent path to the local files
import os
# aiofiles module is recommended for file operation
import aiofiles
import asyncio

from enum import Enum, unique
from dataclasses import dataclass
import datetime
from typing import Union, cast, Callable, Awaitable, Optional

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
    res_role: bool = any(map(lambda x: ctx.author.has_role(x.id) and isinstance(x, GlobalAdmin) if x.type == MRCTType.ROLE else False, global_admins))

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
        lambda x: ctx.author.has_role(x.id) and isinstance(x, ChannelModerator) if x.type == MRCTType.ROLE else False,
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

    ################ Initial functions STARTS ################

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

    ################ Initial functions FINISH ################
    ##########################################################
    ################ Utility functions STARTS ################

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
        # Do not double jail existing prisoners
        existed, prisoner = self.check_prisoner(prisoner_member, duration_minutes, channel)
        if existed:
            return False

        # Do not jail channel moderators themselves
        channel_id: int = channel.id if not hasattr(channel, "parent_channel") else channel.parent_channel.id
        cmod_user: ChannelModerator = ChannelModerator(
            prisoner_member.id,
            MRCTType.USER,
            channel_id
        )
        res_user: bool = cmod_user in channel_moderators
        res_role: bool = any(map(
            lambda x: prisoner_member.has_role(x.id) if x.type == MRCTType.ROLE else False,
            (_ for _ in channel_moderators if _.channel_id == channel_id)
        ))
        if res_user or res_role:
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

    ################ Utility functions FINISH ################
    ##########################################################
    ################ Command functions STARTS ################

    @module_group_setting.subcommand("set_global_admin", sub_cmd_description="Set the Global Admin")
    @interactions.slash_option(
        name = "set_type",
        description = "Type of the admin. Select one of the options.",
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
        Pop a User/Role Select Menu ephemeral to choose. It will disappear once selected.
        It will check whether the user or role is capable of the admin
        '''
        match set_type:
            case MRCTType.USER:
                component_user: interactions.UserSelectMenu = interactions.UserSelectMenu(
                    custom_id=GLOBAL_ADMIN_USER_CUSTOM_ID,
                    placeholder="Select the user for global admin",
                    max_values=25,
                    default_values=[ctx.guild.get_member(_.id) for _ in global_admins if _.type == MRCTType.USER]
                )
                await ctx.send("Set the global admin USER:", components=[component_user], ephemeral=True)
            case MRCTType.ROLE:
                component_role: interactions.RoleSelectMenu = interactions.RoleSelectMenu(
                    custom_id=GLOBAL_ADMIN_ROLE_CUSTOM_ID,
                    placeholder="Select the role for global admin",
                    max_values=25,
                    default_values=[ctx.guild.get_role(_.id) for _ in global_admins if _.type == MRCTType.ROLE]
                )
                await ctx.send("Set the global admin ROLE:", components=[component_role], ephemeral=True)

    @interactions.component_callback(GLOBAL_ADMIN_USER_CUSTOM_ID)
    async def callback_setGA_component_user(self, ctx: interactions.ComponentContext) -> None:
        if await my_admin_check(ctx):
            message: interactions.Message = ctx.message
            msg_to_send: str = "Added global admin as a member:"
            for user in ctx.values:
                user = cast(interactions.Member, user)
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
            # Edit the original ephemeral message to hide the select menu
            await ctx.edit_origin(content="Global admin user set!", components=[])
            # The edit above already acknowledged the context so has to send message to channel directly
            await ctx.channel.send(msg_to_send)
            return
        await ctx.send("You do not have the permission to do so!", ephemeral=True)

    @interactions.component_callback(GLOBAL_ADMIN_ROLE_CUSTOM_ID)
    async def callback_setGA_component_role(self, ctx: interactions.ComponentContext) -> None:
        if await my_admin_check(ctx):
            message: interactions.Message = ctx.message
            msg_to_send: str = "Added global admin as a role:"
            for role in ctx.values:
                role = cast(interactions.Role, role)
                _to_add: GlobalAdmin = GlobalAdmin(role.id, MRCTType.ROLE)
                if _to_add not in global_admins:
                    global_admins.append(_to_add)
                    async with Session() as conn:
                        conn.add(
                            GlobalAdminDB(id=_to_add.id, type=_to_add.type)
                        )
                        await conn.commit()
                    msg_to_send += f"\n- {role.name} {role.mention}"
            # Edit the original ephemeral message to hide the select menu
            await ctx.edit_origin(content="Global admin role set!", components=[])
            # The edit above already acknowledged the context so has to send message to channel directly
            await ctx.channel.send(msg_to_send)
            return
        await ctx.send("You do not have the permission to do so!", ephemeral=True)


    @module_group_setting.subcommand("set_moderator", sub_cmd_description="Set the moderator in this channel")
    @interactions.slash_option(
        name = "set_type",
        description = "Type of the moderator. Select one of the options.",
        required = True,
        opt_type = interactions.OptionType.INTEGER,
        choices=[
            interactions.SlashCommandChoice(name="User", value=MRCTType.USER),
            interactions.SlashCommandChoice(name="Role", value=MRCTType.ROLE)
        ]
    )
    @interactions.check(my_admin_check)
    async def module_group_setting_setChannelModerator(self, ctx: interactions.SlashContext, set_type: int) -> None:
        '''
        Pop a User/Role Select Menu ephemeral to choose. It will disappear once selected.
        It will check whether the user or role is capable of the channel moderator
        '''
        channel: interactions.GuildChannel = ctx.channel if not hasattr(ctx.channel, "parent_channel") else ctx.channel.parent_channel
        match set_type:
            case MRCTType.USER:
                component_user: interactions.UserSelectMenu = interactions.UserSelectMenu(
                    custom_id=CHANNEL_MODERATOR_USER_CUSTOM_ID,
                    placeholder=f"Select the user moderator for {channel.name}",
                    max_values=25,
                    default_values=[ctx.guild.get_member(_.id) for _ in channel_moderators if _.type == MRCTType.USER and _.channel_id == channel.id]
                )
                await ctx.send(f"Set the `{ctx.channel.name}` moderator USER:", components=[component_user], ephemeral=True)
            case MRCTType.ROLE:
                component_role: interactions.RoleSelectMenu = interactions.RoleSelectMenu(
                    custom_id=CHANNEL_MODERATOR_ROLE_CUSTOM_ID,
                    placeholder=f"Select the role moderator for {channel.name}",
                    max_values=25,
                    default_values=[ctx.guild.get_role(_.id) for _ in channel_moderators if _.type == MRCTType.ROLE and _.channel_id == channel.id]
                )
                await ctx.send(f"Set the `{ctx.channel.name}` moderator ROLE:", components=[component_role], ephemeral=True)

    @interactions.component_callback(CHANNEL_MODERATOR_USER_CUSTOM_ID)
    async def callback_setCM_component_user(self, ctx: interactions.ComponentContext) -> None:
        if await my_admin_check(ctx):
            message: interactions.Message = ctx.message
            channel: interactions.GuildChannel = ctx.channel if not hasattr(ctx.channel, "parent_channel") else ctx.channel.parent_channel
            msg_to_send: str = f"Added channel {ctx.channel.name} moderator as a member:"
            for user in ctx.values:
                user = cast(interactions.Member, user)
                if user.bot:
                    continue
                _to_add: ChannelModerator = ChannelModerator(user.id, MRCTType.USER, channel.id)
                if _to_add not in global_admins:
                    channel_moderators.append(_to_add)
                    async with Session() as conn:
                        conn.add(
                            ModeratorDB(id=_to_add.id, type=_to_add.type, channel_id=_to_add.channel_id)
                        )
                        await conn.commit()
                    msg_to_send += f"\n- {user.display_name} {user.mention}"
            # Edit the original ephemeral message to hide the select menu
            await ctx.edit_origin(content="Channel Moderator user set!", components=[])
            # The edit above already acknowledged the context so has to send message to channel directly
            await ctx.channel.send(msg_to_send)
            return
        await ctx.send("You do not have the permission to do so!", ephemeral=True)

    @interactions.component_callback(CHANNEL_MODERATOR_ROLE_CUSTOM_ID)
    async def callback_setCM_component_role(self, ctx: interactions.ComponentContext) -> None:
        if await my_admin_check(ctx):
            message: interactions.Message = ctx.message
            channel: interactions.GuildChannel = ctx.channel if not hasattr(ctx.channel, "parent_channel") else ctx.channel.parent_channel
            msg_to_send: str = "Added channel moderator as a role:"
            for role in ctx.values:
                role = cast(interactions.Role, role)
                _to_add: ChannelModerator = ChannelModerator(role.id, MRCTType.ROLE, channel.id)
                if _to_add not in channel_moderators:
                    channel_moderators.append(_to_add)
                    async with Session() as conn:
                        conn.add(
                            ModeratorDB(id=_to_add.id, type=_to_add.type, channel_id=_to_add.channel_id)
                        )
                        await conn.commit()
                    msg_to_send += f"\n- {role.name} {role.mention}"
            # Edit the original ephemeral message to hide the select menu
            await ctx.edit_origin(content="Channel Moderator role set!", components=[])
            # The edit above already acknowledged the context so has to send message to channel directly
            await ctx.channel.send(msg_to_send)
            return
        await ctx.send("You do not have the permission to do so!", ephemeral=True)

    @module_group_setting.subcommand("remove_global_admin", sub_cmd_description="Remove the Global Admin")
    @interactions.slash_option(
        "user",
        description="The global admin user to be removed",
        required=False,
        opt_type=interactions.OptionType.STRING,
        autocomplete=True
    )
    @interactions.slash_option(
        "role",
        description="The global admin role to be removed.",
        required=False,
        opt_type=interactions.OptionType.STRING,
        autocomplete=True
    )
    @interactions.check(my_admin_check)
    async def module_group_setting_removeGlobalAdmin(
        self, ctx: interactions.SlashContext,
        user: Optional[str] = None,
        role: Optional[str] = None) -> None:
        """
        Remove the global admin user or role
        """
        # If there is no parameter provided
        if user is None and role is None:
            await ctx.send("Please select either a user or a role to be removed!", ephemeral=True)
            return
        try:
            # Discord cannot transfer big integer so using string and convert to integer instead
            user = int(user) if user is not None else None
            role = int(role) if role is not None else None
        except ValueError:
            await ctx.send("Input value error! Please contact technical support.", ephemeral=True)
            return
        async with Session() as session:
            msg: str = ""
            if user is not None:
                ga: GlobalAdmin = GlobalAdmin(user, MRCTType.USER)
                ga_mention: str = ctx.guild.get_member(ga.id).mention
                if ga not in global_admins:
                    await ctx.send(f"{ga_mention} is not a global admin user!", silent=True)
                    return
                msg += f"\n- {ga_mention}"
                global_admins.remove(ga)
                await session.execute(
                    sqldelete(GlobalAdminDB).
                    where(sqlalchemy.and_(
                        GlobalAdminDB.id == ga.id,
                        GlobalAdminDB.type == ga.type
                    ))
                )
            if role is not None:
                ga: GlobalAdmin = GlobalAdmin(role, MRCTType.ROLE)
                ga_mention: str = ctx.guild.get_role(ga.id).mention
                if ga not in global_admins:
                    await ctx.send(f"{ga_mention} is not a global admin role!", silent=True)
                    return
                msg += f"\n- {ga_mention}"
                global_admins.remove(ga)
                await session.execute(
                    sqldelete(GlobalAdminDB).
                    where(sqlalchemy.and_(
                        GlobalAdminDB.id == ga.id,
                        GlobalAdminDB.type == ga.type
                    ))
                )
            await session.commit()
        # Get user and role objects to get name and mention
        user: Optional[interactions.User] = ctx.guild.get_member(user) if user is not None else None
        role: Optional[interactions.Role] = ctx.guild.get_role(role) if role is not None else None
        await ctx.send(f"Removed global admins:\n{'- '+user.mention if user is not None else ''}\n{'- '+role.mention if role is not None else ''}")
    
    @module_group_setting_removeGlobalAdmin.autocomplete("user")
    async def autocomplete_removeGlobalAdmin_user(self, ctx: interactions.AutocompleteContext) -> None:
        option_input: str = ctx.input_text
        options_user: list[interactions.Member] = [ctx.guild.get_member(i.id) for i in global_admins if i.type == MRCTType.USER]
        options_auto: list[interactions.Member] = [
            i for i in options_user if option_input in i.display_name or option_input in i.username
        ]
        await ctx.send(
            choices=[
                {
                    "name": i.display_name,
                    "value": str(i.id)
                } for i in options_auto
            ]
        )

    @module_group_setting_removeGlobalAdmin.autocomplete("role")
    async def autocomplete_removeGlobalAdmin_role(self, ctx: interactions.AutocompleteContext) -> None:
        option_input: str = ctx.input_text
        options_role: list[interactions.Role] = [ctx.guild.get_role(i.id) for i in global_admins if i.type == MRCTType.ROLE]
        options_auto: list[interactions.Role] = [
            i for i in options_role if option_input in i.name
        ]
        await ctx.send(
            choices=[
                {
                    "name": i.name,
                    "value": str(i.id)
                } for i in options_auto
            ]
        )
    
    @module_group_setting.subcommand("remove_channel_mod", sub_cmd_description="Remove the Channel Moderator")
    @interactions.slash_option(
        "user",
        description="The channel moderator user to be removed",
        required=False,
        opt_type=interactions.OptionType.STRING,
        autocomplete=True
    )
    @interactions.slash_option(
        "role",
        description="The channel moderator role to be removed.",
        required=False,
        opt_type=interactions.OptionType.STRING,
        autocomplete=True
    )
    @interactions.check(my_admin_check)
    async def module_group_setting_removeChannelModerator(
        self, ctx: interactions.SlashContext,
        user: Optional[str] = None,
        role: Optional[str] = None) -> None:
        """
        Remove the moderator of current channel
        """
        # If there is no parameter provided
        if user is None and role is None:
            await ctx.send("Please select either a user or a role to be removed!", ephemeral=True)
            return
        try:
            # Discord cannot transfer big integer so using string and convert to integer instead
            user = int(user) if user is not None else None
            role = int(role) if role is not None else None
        except ValueError:
            await ctx.send("Input value error! Please contact technical support.", ephemeral=True)
            return
        channel: interactions.GuildChannel = ctx.channel if not hasattr(ctx.channel, "parent_channel") else ctx.channel.parent_channel
        async with Session() as session:
            msg: str = ""
            if user is not None:
                cm: ChannelModerator = ChannelModerator(user, MRCTType.USER, channel.id)
                cm_mention: str = ctx.guild.get_member(cm.id).mention
                if cm not in channel_moderators:
                    await ctx.send(f"{cm_mention} is not the moderator user of this channel {channel.mention}!", silent=True)
                    return
                msg += f"\n- {cm_mention}"
                channel_moderators.remove(cm)
                await session.execute(
                    sqldelete(ModeratorDB).
                    where(sqlalchemy.and_(
                        ModeratorDB.id == cm.id,
                        ModeratorDB.type == cm.type,
                        ModeratorDB.channel_id == cm.channel_id
                    ))
                )
            if role is not None:
                cm: ChannelModerator = ChannelModerator(role, MRCTType.ROLE, channel.id)
                cm_mention: str = ctx.guild.get_role(cm.id).mention
                if cm not in channel_moderators:
                    await ctx.send(f"{cm_mention} is not the moderator role of this channel {channel.mention}!", silent=True)
                    return
                msg += f"\n- {cm_mention}"
                channel_moderators.remove(cm)
                await session.execute(
                    sqldelete(ModeratorDB).
                    where(sqlalchemy.and_(
                        ModeratorDB.id == cm.id,
                        ModeratorDB.type == cm.type,
                        ModeratorDB.channel_id == cm.channel_id
                    ))
                )
            await session.commit()
        # Get user and role objects to get name and mention
        user: Optional[interactions.User] = ctx.guild.get_member(user) if user is not None else None
        role: Optional[interactions.Role] = ctx.guild.get_role(role) if role is not None else None
        await ctx.send(f"Removed channel moderator in {channel.mention}:\n{'- '+user.mention if user is not None else ''}\n{'- '+role.mention if role is not None else ''}")

    @module_group_setting_removeChannelModerator.autocomplete("user")
    async def autocomplete_removeChannelModerator_user(self, ctx: interactions.AutocompleteContext) -> None:
        channel: interactions.GuildChannel = ctx.channel if not hasattr(ctx.channel, "parent_channel") else ctx.channel.parent_channel
        option_input: str = ctx.input_text
        options_user: list[interactions.Member] = [ctx.guild.get_member(i.id) for i in channel_moderators if i.type == MRCTType.USER and i.channel_id == channel.id]
        options_auto: list[interactions.Member] = [
            i for i in options_user if option_input in i.display_name or option_input in i.username
        ]
        await ctx.send(
            choices=[
                {
                    "name": i.display_name,
                    "value": str(i.id)
                } for i in options_auto
            ]
        )

    @module_group_setting_removeChannelModerator.autocomplete("role")
    async def autocomplete_removeChannelModerator_role(self, ctx: interactions.AutocompleteContext) -> None:
        channel: interactions.GuildChannel = ctx.channel if not hasattr(ctx.channel, "parent_channel") else ctx.channel.parent_channel
        option_input: str = ctx.input_text
        options_role: list[interactions.Role] = [ctx.guild.get_role(i.id) for i in channel_moderators if i.type == MRCTType.ROLE and i.channel_id == channel.id]
        options_auto: list[interactions.Role] = [
            i for i in options_role if option_input in i.name
        ]
        await ctx.send(
            choices=[
                {
                    "name": i.name,
                    "value": str(i.id)
                } for i in options_auto
            ]
        )
    
    @module_group_setting.subcommand("view_global_admin", sub_cmd_description="View all Global Admins")
    async def module_group_setting_viewGlobalAdmin(self, ctx: interactions.SlashContext) -> None:
        msg: str = ""
        for i in global_admins:
            if i.type == MRCTType.USER:
                msg += f"- User: {ctx.guild.get_member(i.id).mention}\n"
            elif i.type == MRCTType.ROLE:
                role: interactions.Role = await ctx.guild.fetch_role(i.id)
                msg += f"- Role: {role.mention}\n"
                for u in role.members:
                    msg += f"\t- User: {u.mention}\n"
        pag: Paginator = Paginator.create_from_string(self.bot, f"Global Admin for Confined Timeout:\n{msg}", page_size=1000)
        await pag.send(ctx)
    
    @module_group_setting.subcommand("view_channel_mod", sub_cmd_description="View Moderators of this channel")
    async def module_group_setting_viewChannelModerator(self, ctx: interactions.SlashContext) -> None:
        channel: interactions.GuildChannel = ctx.channel if not hasattr(ctx.channel, "parent_channel") else ctx.channel.parent_channel
        msg: str = ""
        for i in channel_moderators:
            if i.channel_id != channel.id:
                continue
            if i.type == MRCTType.USER:
                msg += f"- User: {ctx.guild.get_member(i.id).mention}\n"
            elif i.type == MRCTType.ROLE:
                role: interactions.Role = await ctx.guild.fetch_role(i.id)
                msg += f"- Role: {role.mention}\n"
                for u in role.members:
                    msg += f"\t- User: {u.mention}\n"
        pag: Paginator = Paginator.create_from_string(self.bot, f"Moderators in {channel.mention} for Confined Timeout:\n{msg}", page_size=1000)
        await pag.send(ctx)

    #TODO TEST view summary (All global admins, channel moderators, prisoners with time remaining)
    @module_group_setting.subcommand("summary", sub_cmd_description="View summary")
    async def module_group_setting_viewSummary(self, ctx: interactions.SlashContext) -> None:
        msg: str = "Global Admins:"
        for i in global_admins:
            if i.type == MRCTType.USER:
                msg += f"- User: {ctx.guild.get_member(i.id).mention}\n"
            elif i.type == MRCTType.ROLE:
                role: interactions.Role = await ctx.guild.fetch_role(i.id)
                msg += f"- Role: {role.mention}\n"
                for u in role.members:
                    msg += f"\t- User: {u.mention}\n"
        cms: dict[int, list[ChannelModerator]] = {i.channel_id: [] for i in channel_moderators}
        for i in channel_moderators:
            cms[i.channel_id].append(i)
        for cid, cmls in cms.items():
            msg += f"\nModerator in {ctx.guild.get_channel(cid).mention}:\n"
            for i in cmls:
                if i.type == MRCTType.USER:
                    msg += f"- User: {ctx.guild.get_member(i.id).mention}\n"
                elif i.type == MRCTType.ROLE:
                    role: interactions.Role = await ctx.guild.fetch_role(i.id)
                    msg += f"- Role: {role.mention}\n"
                    for u in role.members:
                        msg += f"\t- User: {u.mention}\n"
        ps: dict[int, list[Prisoner]] = {i.channel_id: [] for i in prisoners}
        for i in prisoners:
            ps[i.channel_id].append(i)
        for cid, pls in ps.items():
            msg += f"\nPrisoners in {ctx.guild.get_channel(cid).mention}:\n"
            for i in pls:
                timeleft: datetime.timedelta = interactions.Timestamp.now() - i.release_datatime
                timestring: str = f"{timeleft.seconds / 60 if hasattr(timeleft, 'seconds') else timeleft.microseconds} "
                timestring += "minutes" if hasattr(timeleft, "seconds") else "microseconds"
                msg += f"- {ctx.guild.get_member(i.id).mention} `{timestring} left`"
        pag: Paginator = Paginator.create_from_string(self.bot, f"Summary for Confined Timeout:\n\n{msg}", page_size=1000)
        await pag.send(ctx)
    
    #TODO (command) timeout member in a channel
    @module_base.subcommand("timeout", sub_cmd_description="Timeout a member in this channel")
    @interactions.slash_option(
        "user",
        description="The user to timeout",
        required=True,
        opt_type=interactions.OptionType.USER
    )
    @interactions.check(my_channel_moderator_check)
    async def module_base_timeout(self, ctx: interactions.SlashContext, user: interactions.User) -> None:
        raise NotImplementedError()
    
    #TODO (user context menu) timeout member in a channel
    @interactions.user_context_menu("Confined Timeout User")
    async def contextmenu_usr_timeout(self, ctx: interactions.ContextMenuContext) -> None:
        raise NotImplementedError()

    #TODO (message context menu) timeout member in a channel
    @interactions.message_context_menu("Confined Timeout Msg")
    async def contextmenu_msg_timeout(self, ctx: interactions.ContextMenuContext) -> None:
        raise NotImplementedError()
    
    #TODO (command) release member in a channel
    @module_base.subcommand("release", sub_cmd_description="Revoke a member timeout in this channel")
    @interactions.slash_option(
        "user",
        description="The user to release",
        required=True,
        opt_type=interactions.OptionType.INTEGER,
        autocomplete=True
    )
    @interactions.check(my_channel_moderator_check)
    async def module_base_release(self, ctx: interactions.SlashContext, user: int) -> None:
        raise NotImplementedError()

    @module_base_release.autocomplete("user")
    async def autocomplete_release_user(self, ctx: interactions.AutocompleteContext) -> None:
        raise NotImplementedError()
    
    #TODO (context menu) release member in a channel
    @interactions.user_context_menu("Confined Release")
    async def contextmenu_usr_release(self, ctx: interactions.ContextMenuContext) -> None:
        raise NotImplementedError()