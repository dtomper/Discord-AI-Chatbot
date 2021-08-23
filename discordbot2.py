import discord
import undetected_chromedriver.v2 as uc
from selenium.webdriver.common.keys import Keys
import re
from urllib.parse import unquote

driver = uc.Chrome()
driver.get('https://www.cleverbot.com')
driver.find_element_by_id('noteb').click()

old_cookie_value = ""

def get_response(message):
    global old_cookie_value
    # Send the escaped message to cleverbot using JavaScript
    escaped_message = message.replace("\\", "\\\\").replace("'", "\\'")
    driver.execute_script(f"cleverbot.sendAI('{escaped_message}')")

    # Capture cleverbot's response from browser's cookies
    print("Waiting for cleverbot's response...")
    while True:
        cookies = driver.get_cookies()
        for cookie in cookies:
            cookie_value = cookie["value"]
            cookie_header = re.match("&&[0-9]+&&[0-9]+&[0-9]+&", cookie_value)
            if cookie_header and cookie_value != old_cookie_value:
                old_cookie_value = cookie_value
                return unquote(cookie_value.split("&")[-1])

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as', self.user)

    async def on_message(self, message):
        if message.author != self.user:
            reponse = get_response(message.content)
            await message.channel.send(f"{message.author.mention} {reponse}")

client = MyClient()
client.run('BOT TOKEN HERE')