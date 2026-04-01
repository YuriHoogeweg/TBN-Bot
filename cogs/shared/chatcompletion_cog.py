import asyncio
from datetime import datetime
from itertools import product
import logging
import time
from types import SimpleNamespace
from typing import List
from disnake.ext import commands
from openai import OpenAI
import copy

from retry import retry

from config import Configuration


class ChatCompletionCog(commands.Cog):
    def __init__(self, name: str, bot: commands.Bot):
        self.bot = bot
        self.name = name

        config = Configuration.instance()
        self.configs = {
            "openai": SimpleNamespace(
                client=OpenAI(api_key=config.OPENAI_KEY),
                default_model="gpt-5.4-mini"
            ),
            "grok": SimpleNamespace(
                client=OpenAI(api_key=config.GROK_KEY, base_url="https://api.x.ai/v1"),
                default_model="grok-4-1-fast-non-reasoning"
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
            response = await asyncio.to_thread(self.__call_grok, messages)
        else:
            response = await asyncio.to_thread(self.__call_openai, messages)

        logging.info(f"Input: {message}\n\tResponse: {response}\n")        
        
        return response    
    
    @retry(tries=3, delay=5, backoff=5, logger=logging.getLogger(__name__))
    def __call_openai(self, messages) -> str:
        completion = self.configs["openai"].client.chat.completions.create(
            model=self.configs["openai"].default_model,
            messages=messages
        )
        return completion.choices[0].message.content

    def __call_grok(self, messages) -> str:
        model = self.configs["grok"].default_model
        logging.info(f"Calling Grok API (model={model})")
        completion = self.configs["grok"].client.chat.completions.create(
            model=model,
            messages=messages
        )
        logging.info("Grok API call succeeded")
        return completion.choices[0].message.content