import asyncio
import aiohttp
import json
import os

async def monitor_discord_channel(token, channel_id, webhook_url):
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    async with aiohttp.ClientSession() as session:
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=1"
        
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                messages = await response.json()
                last_message_id = messages[0]['id'] if messages else None
            else:
                return
        
        while True:
            url = f"https://discord.com/api/v9/channels/{channel_id}/messages?after={last_message_id}&limit=10"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    messages = await response.json()
                    for message in reversed(messages):
                        await process_message(session, message, webhook_url)
                        last_message_id = message['id']

async def process_message(session, message, webhook_url):
    if 'embeds' in message and message['embeds']:
        for embed in message['embeds']:
            if 'fields' in embed and embed['fields']:
                jobId, moneyPerSec, petName = None, 0, 'Unknown'
                
                for field in embed['fields']:
                    fval = field.get('value', '')
                    if 'Job ID' in field.get('name', ''):
                        jobId = fval.replace('`', '')
                    if 'Name' in field.get('name', ''):
                        petName = fval
                    if '$' in fval and 'M/s' in fval:
                        dollar = fval.split('$')[1].split('M/s')[0]
                        if dollar:
                            moneyPerSec = float(dollar) * 1000000
                    elif '$' in fval and 'K/s' in fval:
                        k = fval.split('$')[1].split('K/s')[0]
                        if k:
                            moneyPerSec = float(k) * 1000
                
                if jobId and moneyPerSec > 0 and petName:
                    data = {"jobid": jobId, "money": str(moneyPerSec), "name": petName}
                    await send_to_webhook(session, webhook_url, data)

async def send_to_webhook(session, url, data):
    async with session.post(url, json=data):
        pass

async def main():
    token = os.environ.get('TOKEN')
    if not token:
        return
    
    channels = {
        1430459323716337795: os.environ.get('WEBHOOK'),
        1430459403034955786: os.environ.get('WEBHOOK2'),
        1429536067803021413: os.environ.get('WEBHOOK3')
    }
    
    tasks = []
    for channel_id, webhook_url in channels.items():
        if webhook_url:
            tasks.append(monitor_discord_channel(token, channel_id, webhook_url))
    
    if tasks:
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
