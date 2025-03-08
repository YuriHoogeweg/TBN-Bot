from datetime import datetime
from itertools import product
import logging
import time
from types import SimpleNamespace
from typing import List
from disnake.ext import commands
import openai
import copy

from retry import retry

from config import Configuration


class ChatCompletionCog(commands.Cog):
    def __init__(self, name: str, bot: commands.Bot):
        self.bot = bot    
        self.name = name
        
        self.configs = {
            "openai": SimpleNamespace(
                api_key=Configuration.instance().OPENAI_KEY,
                base_url=openai.api_base,
                default_model="gpt-4o-mini"
            ),
            "grok": SimpleNamespace(
                api_key=Configuration.instance().GROK_KEY,
                base_url="https://api.x.ai/v1",
                default_model="grok-beta"
            )
        }

    def set_message_context(self, sys_prompt: str, usr_msg: List[str], ast_msg: List[str]):
        messages = [{"role": "system", "content": sys_prompt}]

        for i in range(max(len(usr_msg), len(ast_msg))):
            if i < len(usr_msg):
                messages.append({"role": "user", "content": usr_msg[i]})

            if i < len(ast_msg):
                messages.append({"role": "assistant", "content": ast_msg[i]})

        self.messagecontext = messages

    async def get_response(self, message: str, placeholder_strings: dict[str, str] = [], llm: str = "openai") -> str:                  
        messages = copy.deepcopy(self.messagecontext)

        if placeholder_strings is not None and len(placeholder_strings) > 0:
            for msg, (placeholder, replacement) in product(messages, placeholder_strings.items()):
                msg['content'] = msg['content'].replace(placeholder, replacement)

        response = ""        
        messages.append({"role": "user", "content": message})

        if (llm == "grok"):
            response = self.__call_grok(messages)
        else:
            response = self.__call_openai(messages)

        logging.info(f"Input: {message}\n\tResponse: {response}\n")        
        
        return response    
    
    @retry(tries=3, delay=5, backoff=5, logger=logging.getLogger(__name__))
    def __call_openai(self, messages) -> str:
        openai.api_key = self.configs["openai"].api_key
        openai.api_base = self.configs["openai"].base_url
        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages
        )

        return completion.choices[0].message.content
    
    def __call_grok(self, messages) -> str:
        openai.api_key = self.configs["grok"].api_key
        openai.api_base = self.configs["grok"].base_url

        completion = openai.ChatCompletion.create(
            model=self.configs["grok"].default_model,
            messages=messages
        )
        return completion.choices[0].message.content