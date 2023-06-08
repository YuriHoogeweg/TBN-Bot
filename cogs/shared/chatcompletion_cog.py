from datetime import datetime
from itertools import product
import time
from typing import List
from disnake.ext import commands
import openai
import copy


class ChatCompletionCog(commands.Cog):
    async def __init__(self,
                       bot: commands.Bot):
        self.bot = bot

    def set_message_context(self, sys_prompt: str, usr_msg: List[str], ast_msg: List[str]):
        messages = [{"role": "system", "content": sys_prompt}]

        for i in range(max(len(usr_msg), len(ast_msg))):
            if i < len(usr_msg):
                messages.append({"role": "user", "content": usr_msg[i]})

            if i < len(ast_msg):
                messages.append({"role": "assistant", "content": ast_msg[i]})

        self.messagecontext = messages

    async def get_response(self, message: str, placeholder_strings: dict[str, str] = []):  
        messages = copy.deepcopy(self.messagecontext)

        if placeholder_strings is not None and len(placeholder_strings) > 0:
            for msg, (placeholder, replacement) in product(messages, placeholder_strings.items()):
                msg['content'] = msg['content'].replace(placeholder, replacement)

        response = ""        
        messages.append({"role": "user", "content": message})

        for attempt in range(1, 3):
            try:
                self.log(log_message)
                completion = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )

                response = completion.choices[0].message.content
                break
            except:
                response = "OpenAI API call failed."                
                time.sleep(10)
                continue

        log_message = f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\tInput: {message}\n\tResponse: {response}\n"
        self.log(log_message)
        
        return response
    
    def log(str: str):
        print(str)

        with open(f"log.txt", "a", encoding="UTF-8") as f:
            f.write(str)
