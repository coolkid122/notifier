import asyncio
import aiohttp
import json
import os
import logging
from urllib.parse import urlparse

logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def monitor_discord_channel(token, channel_id, webhook_url):
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    async with aiohttp.ClientSession() as session:
        if not urlparse(webhook_url).scheme or not webhook_url.startswith('https://discord.com/api/webhooks/'):
            logging.error(f"Invalid webhook URL for channel {channel_id}: {webhook_url}")
            return

        url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=1"
        for attempt in range(3):
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        messages = await response.json()
                        last_message_id = messages[0]['id'] if messages else None
                        logging.info(f"Connected to channel {channel_id}. Last message ID: {last_message_id}")
                        break
                    elif response.status == 429:
                        retry_after = float((await response.json()).get('retry_after', 1))
                        logging.warning(f"Rate limited on channel {channel_id}. Waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                    else:
                        logging.error(f"API error for channel {channel_id}: {response.status}")
                        return
            except Exception as e:
                logging.error(f"Connection error for channel {channel_id}: {e}")
                await asyncio.sleep(2 ** attempt)
        else:
            logging.error(f"Failed to connect to channel {channel_id} after retries")
            return

        while True:
            try:
                url = f"https://discord.com/api/v9/channels/{channel_id}/messages?after={last_message_id}&limit=10"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        messages = await response.json()
                        for message in reversed(messages):
                            await send_to_webhook(session, webhook_url, message, channel_id)
                            last_message_id = message['id']
                    elif response.status == 429:
                        retry_after = float((await response.json()).get('retry_after', 1))
                        logging.warning(f"Rate limited on channel {channel_id}. Waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
            except Exception as e:
                logging.error(f"Polling error for channel {channel_id}: {e}")
            await asyncio.sleep(0.5)

async def send_to_webhook(session, url, message, channel_id):
    for attempt in range(3):
        try:
            async with session.post(url, json=message) as response:
                if response.status in (200, 204):
                    logging.info(f"Message sent to webhook for channel {channel_id}: {url}")
                    return
                elif response.status == 429:
                    retry_after = float((await response.json()).get('retry_after', 1))
                    logging.warning(f"Rate limited on webhook {url}. Waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                else:
                    logging.error(f"Webhook error for channel {channel_id}: {response.status}")
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logging.error(f"Error sending to webhook for channel {channel_id}: {e}")
    logging.error(f"Failed to send to webhook for channel {channel_id} after retries")

async def main():
    token = os.environ.get('TOKEN')
    if not token:
        logging.error("TOKEN environment variable not set")
        return
    
    channels = {
        1430459323716337795: os.environ.get('WEBHOOK'),   # 10-100m
        1430459403034955786: os.environ.get('WEBHOOK2'),  # 100m+
        1429536067803021413: os.environ.get('WEBHOOK3')   # private servers
    }
    
    tasks = []
    for channel_id, webhook_url in channels.items():
        if not webhook_url:
            logging.error(f"Webhook not set for channel {channel_id}")
            continue
        tasks.append(monitor_discord_channel(token, channel_id, webhook_url))
    
    if not tasks:
        logging.error("No valid channels/webhooks configured")
        return
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
