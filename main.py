'''
Confined Timeout

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

from enum import Enum, unique

import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{os.path.dirname(__file__)}/confined_timeout_db.db")

@sqlalchemy.event.listens_for(engine.sync_engine, "connect")
def do_connect(dbapi_connection, connection_record):
    dbapi_connection.isolation_level = None

@sqlalchemy.event.listens_for(engine.sync_engine, "begin")
def do_begin(conn):
    conn.exec_driver_sql("BEGIN")

metaObj: sqlalchemy.MetaData = sqlalchemy.MetaData()
metaObj.reflect(engine)
GlobalAdminDB: sqlalchemy.Table = sqlalchemy.Table(
    "GlobalAdminDB", metaObj,
    sqlalchemy.Column("UID", sqlalchemy.BigInteger, autoincrement=True, primary_key=True),
    sqlalchemy.Column("id", sqlalchemy.BigInteger, nullable=False),
    sqlalchemy.Column("type", sqlalchemy.Integer, nullable=False)
)
ModeratorDB: sqlalchemy.Table = sqlalchemy.Table(
    "ModeratorDB", metaObj,
    sqlalchemy.Column("UID", sqlalchemy.BigInteger, autoincrement=True, primary_key=True),
    sqlalchemy.Column("id", sqlalchemy.BigInteger, nullable=False),
    sqlalchemy.Column("type", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("channel_id", sqlalchemy.BigInteger, nullable=False)
)
PrisonerDB: sqlalchemy.Table = sqlalchemy.Table(
    "PrinsonerDB", metaObj,
    sqlalchemy.Column("UID", sqlalchemy.BigInteger, autoincrement=True, primary_key=True),
    sqlalchemy.Column("id", sqlalchemy.BigInteger, nullable=False),
    sqlalchemy.Column("release_datetime", sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column("channel_id", sqlalchemy.BigInteger, nullable=False)
)
metaObj.create_all(engine)

@unique
class MRCTType(int, Enum):
    USER = 1
    ROLE = 2

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

    '''
    Check whether the person has the global admin permission to run the command
    '''
    async def my_admin_check(ctx: interactions.BaseContext):
        res: bool = await interactions.is_owner()(ctx)

        return res

    '''
    Check whether the member has the channel moderator permission to run the command
    '''
    async def my_admin_check(ctx: interactions.BaseContext):
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
    async def module_group_setting_setGlobalAdmin(self, ctx: interactions.SlashContext, set_type: int):
        '''
        Pop a User Select Menu ephemeral to choose. It will disappear once selected.
        It will check whether the user or role is capable of the admin
        '''
        await ctx.send(f"Pong {set_type}!")

    @module_base.subcommand("pong", sub_cmd_description="Replace the description of this command")
    @interactions.slash_option(
        name = "option_name",
        description = "Option description",
        required = True,
        opt_type = interactions.OptionType.STRING
    )
    async def module_base_pong(self, ctx: interactions.SlashContext, option_name: str):
        await ctx.send(f"Pong {option_name}!")
