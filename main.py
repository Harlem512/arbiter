import discord
import json
import asyncio
import os
import sys
import re
from datetime import datetime

from bs4 import BeautifulSoup
import requests

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
URL_REGEX = r'(https?://www\.youtube\.com/watch\?v=[^\s]+)'
invisible = True
enabled = True
deafMuteOverride = True


def time_print(s: str):
    print(f'{datetime.now()} | {s}')


def name(member):
    return member.nick if member.nick else member.name


with open(os.path.join(sys.path[0], 'data.json'), 'r') as read:
    data = json.load(read)

ALLOW_MITCHPOSTING = 'channel_blacklist' in data

if not data['token']:
    print('Error: token invalid or missing')
    exit()


join_lock = asyncio.Lock()
# Set of users that will be kicked after 5 seconds for joining deaf-mute
join_set = set()


class Arbiter(discord.Client):
    async def on_ready(self):
        global invisible

        time_print(f'Logged on as {self.user}')

        if enabled:
            time_print('Enabled')

        if invisible:
            time_print('Going incognito')
            await self.change_presence(status=discord.Status.offline)

    async def on_message(self, message):
        global invisible
        global enabled

        if message.content == 'hey arbiter':
            return await message.channel.send('hello')

        if message.content == '!!!invis':
            invisible = not invisible
            await self.change_presence(
                status=discord.Status.offline if invisible else discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name='for villains',
                ),
            )
            time_print(f'Invisible: {invisible} by {name(message.author)}')
            return

        if message.content == '!!!enable':
            enabled = not enabled
            time_print(f'Enable: {enabled} by {name(message.author)}')
            return

        if not enabled or not ALLOW_MITCHPOSTING or message.author == self.user:
            return

        urls = re.findall(URL_REGEX, message.content)

        if len(urls) > 0:
            return

        mitchpost = False

        for url in urls:
            # Check for mitch-posting
            response = requests.get(url, headers={'User-Agent': USER_AGENT})
            soup = BeautifulSoup(response.text, 'lxml')

            for link in soup.find_all('link', {'itemprop': 'url'}):
                # if 'channel' in link
                if 'channel' in link['href']:
                    if link['href'] in data['channel_blacklist']:
                        mitchpost = True
                        break

            if mitchpost:
                break

        if mitchpost:
            await message.delete()
            await message.channel.send(
                f'{message.author.mention} Mitchposting is not allowed'
            )
            time_print(
                f'Deleted mitchpost `{message.content}` by {name(message.author)}'
            )

    async def on_voice_state_update(self, member, before, after):
        global enabled
        global deafMuteOverride

        if deafMuteOverride or not enabled or after.channel == None:
            return

        if after.self_mute and after.self_deaf:
            if before.channel == None:
                async with join_lock:
                    join_set.add(member.id)

                await asyncio.sleep(5)

                async with join_lock:
                    if member.id not in join_set:
                        return
                    else:
                        join_set.remove(member.id)

            await member.edit(voice_channel=None, reason='deaf-mute is not allowed')
            time_print(f'Kicked user {name(member)}')

        async with join_lock:
            if member.id in join_set:
                join_set.remove(member.id)


intents = discord.Intents.default()
intents.message_content = True
client = Arbiter(
    intents=intents,
    activity=discord.Activity(
        type=discord.ActivityType.watching,
        name='for villains',
    ),
)

client.run(data['token'])
