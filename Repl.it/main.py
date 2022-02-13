import discord
import undetected_chromedriver as uc
import re
import os
from urllib.parse import unquote
from webserver import keep_alive

chrome_options = uc.ChromeOptions()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
driver = uc.Chrome(options=chrome_options)
driver.get('https://www.cleverbot.com')
driver.find_element_by_id('noteb').click()


old_cookie_value = ""


def get_response(message):
    global old_cookie_value
    print(f"\n[->] Sending: {message}")

    # Send the escaped message to cleverbot using JavaScript
    escaped_message = message.replace("\\", "\\\\").replace("'", "\\'")
    driver.execute_script(f"cleverbot.sendAI('{escaped_message}')")

    # Capture cleverbot's response from browser's cookies
    print("[+] Waiting for cleverbot's response...")
    while True:
        cookies = driver.get_cookies()
        for cookie in cookies:
            cookie_value = cookie["value"]
            cookie_header = re.match("&&[0-9]+&&[0-9]+&[0-9]+&", cookie_value)
            if cookie_header and cookie_value != old_cookie_value:
                old_cookie_value = cookie_value
                clever_response = unquote(cookie_value.split("&")[-1])
                print(f"[<-] Got: {clever_response}")
                return clever_response


class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        if message.author != self.user:
            reponse = get_response(message.content)
            await message.channel.send(f"{message.author.mention} {reponse}")


client = MyClient()

keep_alive()
token = os.getenv('Bot_Token')
client.run(token)