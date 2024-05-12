'''
Confined Timeout
Database Model definition

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
import sqlalchemy
from sqlalchemy import DateTime, BigInteger, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from datetime import datetime

# class DBBase(DeclarativeBase):
class DBBase(AsyncAttrs, DeclarativeBase):
    pass

class GlobalAdminDB(DBBase):
    __tablename__ = "GlobalAdminDB"

    uid:    Mapped[int] = mapped_column(primary_key=True)
    id:     Mapped[int] = mapped_column(BigInteger, nullable=False)
    type:   Mapped[int] = mapped_column(nullable=False)

    def __repr__(self) -> str:
        return f"GlobalAdminDB(uid={self.uid!r}, id={self.id!r}, type={self.type!r})"

class ModeratorDB(DBBase):
    __tablename__ = "ModeratorDB"

    uid:        Mapped[int] = mapped_column(primary_key=True)
    id:         Mapped[int] = mapped_column(BigInteger, nullable=False)
    type:       Mapped[int] = mapped_column(nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    def __repr__(self) -> str:
        return f"ModeratorDB(uid={self.uid!r}, id={self.id!r}, type={self.type!r}, channel_id={self.channel_id!r})"

class PrisonerDB(DBBase):
    __tablename__ = "PrisonerDB"

    uid:                Mapped[int] = mapped_column(primary_key=True)
    id:                 Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel_id:         Mapped[int] = mapped_column(BigInteger, nullable=False)
    release_datetime:   Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"PrisonerDB(uid={self.uid!r}, id={self.id!r}, channel_id={self.channel_id!r}, release_datetime={self.release_datetime!r})"

class SettingDB(DBBase):
    __tablename__ = "SettingDB"

    type:           Mapped[int] = mapped_column(nullable=False, primary_key=True, unique=True)
    setting:        Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Reserved setting for future
    setting1:       Mapped[str] = mapped_column(String(100), nullable=True)