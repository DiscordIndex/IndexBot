from disco.bot import Plugin
from disco.types.channel import Channel as DiscoChannel

from .config import IndexPluginConfig


@Plugin.with_config(IndexPluginConfig)
class IndexPlugin(Plugin):
    def load(self, ctx):
        super(IndexPlugin, self).load(ctx)
        # assert self.config.addChannelID == "yourAddChannelID"

    @Plugin.command('channels')  # TODO: level
    def command_ping(self, event):
        event.msg.reply('Add Channel: <#' + self.config.addChannelID + '>')

    @Plugin.command('add', '<invite:str> <category:channel|snowflake> <name_and_description:str...>')  # TODO: level
    def command_add(self, event, invite, category, name_and_description):
        if event.msg.channel.id != self.config.addChannelID:
            event.msg.reply('invalid channel')
            return

        if not isinstance(category, DiscoChannel):
            category = self.state.channels.get(category)

        name = name_and_description.strip()
        description = ""
        if "|" in name_and_description:
            parts = name_and_description.split('|', 2)
            name = parts[0].strip()
            description = parts[1].strip()

        event.msg.reply('Add\nInvite: {invite}\nCategory: <#{category}>\nName: {name}\nDescription: {description}'.
                        format(invite=invite, category=category.id, name=name, description=description))

    @Plugin.command('update', '<invite:str> [category:channel|snowflake] [name_and_description:str...]')  # TODO: level
    def command_update(self, event, invite, category=None, name_and_description=""):
        if event.msg.channel.id != self.config.addChannelID:
            event.msg.reply('invalid channel')
            return

        if category is not None:
            if not isinstance(category, DiscoChannel):
                category = self.state.channels.get(category)

        name = name_and_description.strip()
        description = ""
        if "|" in name_and_description:
            parts = name_and_description.split('|', 2)
            name = parts[0].strip()
            description = parts[1].strip()

        event.msg.reply('Update\nInvite: {invite}\nCategory: <#{category}>\nName: {name}\nDescription: {description}'.
                        format(invite=invite, category=category.id, name=name, description=description))
