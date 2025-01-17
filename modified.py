import asyncio
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError

class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number, source_chat_ids, destination_chat_id, keywords):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.source_chat_ids = source_chat_ids
        self.destination_chat_id = destination_chat_id
        self.keywords = keywords
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)

    async def forward_messages(self):
        print("Bot started. Forwarding messages...")
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            try:
                await self.client.sign_in(self.phone_number, input('Enter the code: '))
            except SessionPasswordNeededError:
                password = input('Enter your 2-step verification password: ')
                await self.client.sign_in(password=password)

        print("Fetching entities for all source chat IDs...")
        for chat_id in self.source_chat_ids:
            try:
                await self.client.get_entity(chat_id)
                print(f"Successfully fetched entity for chat ID: {chat_id}")
            except Exception as e:
                print(f"Error fetching entity for chat ID {chat_id}: {e}")

        last_message_ids = {}
        for chat_id in self.source_chat_ids:
            try:
                last_message_ids[chat_id] = (await self.client.get_messages(chat_id, limit=1))[0].id
            except Exception as e:
                print(f"Error initializing last message ID for chat ID {chat_id}: {e}")

        while True:
            for chat_id in self.source_chat_ids:
                try:
                    messages = await self.client.get_messages(chat_id, min_id=last_message_ids.get(chat_id, 0), limit=None)
                    for message in reversed(messages):
                        if self.keywords:
                            if message.text and any(keyword in message.text.lower() for keyword in self.keywords):
                                await self._forward_message(message, chat_id)
                            elif message.media and any(keyword in (getattr(message, 'caption', '') or '').lower() for keyword in self.keywords):
                                await self._forward_message(message, chat_id)
                        else:
                            await self._forward_message(message, chat_id)
                        last_message_ids[chat_id] = max(last_message_ids.get(chat_id, 0), message.id)
                except Exception as e:
                    print(f"Error while fetching messages from chat ID {chat_id}: {e}")
            await asyncio.sleep(5)

    async def _forward_message(self, message, source_chat_id):
        try:
            source_chat = await self.client.get_entity(source_chat_id)
            group_name = source_chat.title
            header_message = f"New Post From [{group_name}]"

            if message.text and message.media:
                # Combine media and text into one message
                full_caption = f"{header_message}\n\n{message.text}"
                await self.client.send_file(
                    self.destination_chat_id,
                    file=message.media,
                    caption=full_caption
                )
            elif message.text:
                combined_message = f"{header_message}\n\n{message.text}"
                await self.client.send_message(self.destination_chat_id, combined_message)
            elif message.media:
                caption = getattr(message, 'caption', '') or ''
                full_caption = f"{header_message}\n\n{caption}" if caption else header_message
                await self.client.send_file(
                    self.destination_chat_id,
                    file=message.media,
                    caption=full_caption
                )
            else:
                await self.client.forward_messages(self.destination_chat_id, message.id, source_chat_id)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            await self._forward_message(message, source_chat_id)
        except Exception as e:
            print(f"Error occurred while forwarding message from chat ID {source_chat_id}: {e}")

def read_credentials():
    try:
        with open("credentials.txt", "r") as file:
            lines = file.readlines()
            api_id = lines[0].strip()
            api_hash = lines[1].strip()
            phone_number = lines[2].strip()
            return api_id, api_hash, phone_number
    except FileNotFoundError:
        return None, None, None

def write_credentials(api_id, api_hash, phone_number):
    with open("credentials.txt", "w") as file:
        file.write(api_id + "\n")
        file.write(api_hash + "\n")
        file.write(phone_number + "\n")

async def main():
    

    api_id, api_hash, phone_number = read_credentials()
    if api_id is None or api_hash is None or phone_number is None:
        api_id = input("Enter your API ID: ")
        api_hash = input("Enter your API Hash: ")
        phone_number = input("Enter your Phone Number: ")
        write_credentials(api_id, api_hash, phone_number)

    source_chat_ids = ["group ids or chats id you want message forward from"]
    destination_chat_id = "your source chat id"
    keywords = []

    forwarder = TelegramForwarder(api_id, api_hash, phone_number, source_chat_ids, destination_chat_id, keywords)
    await forwarder.forward_messages()

if __name__ == "__main__":
    asyncio.run(main())
