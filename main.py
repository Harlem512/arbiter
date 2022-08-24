import discord
import json
import asyncio
import os
import sys

with open(os.path.join(sys.path[0], 'data.json'), 'r') as read:
    data = json.load(read)

if not data['token']:
    print('Error: token invalid or missing')
    exit()


join_lock = asyncio.Lock()
# Set of users that will be kicked after 5 seconds for joining deaf-mute
join_set = set()

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as', self.user)

    # async def on_message(self, message):
    #     # don't respond to ourselves
    #     if message.author == self.user:
    #         return

    #     if message.content == 'ping':
    #         await message.channel.send('pong')

    async def on_voice_state_update(self, member, before, after):
        if after.channel == None:
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

        async with join_lock:
            if member.id in join_set:
                join_set.remove(member.id)


intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)
client.run(data['token'])
