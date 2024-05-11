- [中文](#受限的禁言)
- [English](#confined-timeout)

# 受限的禁言
允许特定成员或者身份组可以在特定频道中禁言成员。更进一步说，被禁言的成员只是不能在这个指定的频道中发送消息。

## 实现
简短来说：
- 被指定的成员可以用菜单或者斜杠命令禁言某成员。
- 频道调解员需要在他所管理的频道中设置。
- 人们可以看见被禁言的成员以及其距离释放剩余的时间。
- 人们可以看到频道调解员都有谁。
- 禁言时长有上限。

### 存储数据库的数据结构
- GlobalAdmin: ID (INTEGER), Type (INTEGER)
- Moderator: ID (INTEGER), Type (INTEGER), ChannelID (INTEGER)
- Prisoner: ID (INTEGER), DateTimeRelease (DATETIME), ChannelID (INTEGER)

## 命令
- `/confined_timeout setting set_global_admin`
- `/confined_timeout setting remove_global_admin [<user>] [<role>]`
- `/confined_timeout setting view_global_admin`
- `/confined_timeout setting upper_limit <Minutes> <Hours> <Days>`
- `/confined_timeout setting set_moderator`
- `/confined_timeout setting remove_moderator [<user>] [<role>]`
- `/confined_timeout setting view_moderator`
- `/confined_timeout setting summary`
- `/confined_timeout timeout <Member> <Minutes> [Hours] [Days]`
    - 菜单，弹窗输入信息。
- `/confined_timeout release <Member>`
    - 菜单

# Confined Timeout
It allows certain members or roles able to timeout a member in certain channels. In the other words, the affected members cannot send message only in this channel.

## Implementation
In contrast:
- The appointed members can timeout a certain member by either context menu and a slash command.
- The settings of the channel moderators will be explicitly set in the channel where they manage.
- People can view the timed-out members with time left to be released.
- People can view the channel moderators.
- The timeout duration has an upper limit.

### Persistent Data Structure for Database
- GlobalAdmin: ID (INTEGER), Type (INTEGER)
- Moderator: ID (INTEGER), Type (INTEGER), ChannelID (INTEGER)
- Prisoner: ID (INTEGER), DateTimeRelease (DATETIME), ChannelID (INTEGER)

## Commands
- `/confined_timeout setting set_global_admin`
- `/confined_timeout setting remove_global_admin [<user>] [<role>]`
- `/confined_timeout setting view_global_admin`
- `/confined_timeout setting set_moderator`
- `/confined_timeout setting remove_moderator [<user>] [<role>]`
- `/confined_timeout setting view_moderator`
- `/confined_timeout setting summary`
- `/confined_timeout timeout <Member> <Minutes>`
    - User Context Menu, modal window to enter details
    - Message Context Menu, modal window to enter details. Message as the reason.
- `/confined_timeout release <Member>`
    - User Context Menu