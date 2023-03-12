import math
import os
from queue import Empty
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
import typing

from PIL import Image, ImageDraw, ImageFont
from .imagetools import *
from utils.drawing.table import (ColorCell, ImageCell, Table)

discord_color0 = "#6f7377" # much lighter, mostly unused color
discord_color1 = "#2C2F33"
discord_color2 = "#23272A"
discord_color3 = "#202225"
discord_color4 = "#131416" # darker, mostly unused color
faded_yellow_color = "#c6b37c" # similar to the color of the text for displaying level info

# mostly from https://www.dota2.com/public/css/heropedia.css
item_quality_colors = {
	"rare": "#1A87F9",
	"artifact": "#E29B01",
	"secret_shop": "#31d0d0", # this one wasn't updated, so grabbed from in-game screenshot
	"consumable": "#1D80E7",
	"common": "#2BAB01",
	"epic": "#B812F9",
	"component": "#FEFEFE"
}

# from vpk/panorama/styles/dotastyles.css
neutral_tier_text_colors = {
	"1": "#BEBEBE",
	"2": "#92E47E",
	"3": "#7F93FC",
	"4": "#D57BFF",
	"5": "#FFE195",
}

# from in-game screenshot
neutral_tier_colors = {
	"1": "#958a97",
	"2": "#0ea243",
	"3": "#4c6ee8",
	"4": "#9b2bf6",
	"5": "#e47b17",
}

# from in-game times
neutral_timings = {
	"1": "7:00+",
	"2": "17:00+",
	"3": "27:00+",
	"4": "37:00+",
	"5": "60:00+",
}
hero_infos = {}
item_infos = {}
ability_infos = {}

def get_item_color(item, default=None):
	if item is None:
		return default
	if item.quality in item_quality_colors:
		return item_quality_colors[item.quality]
	elif item.neutral_tier is not None:
		return neutral_tier_colors[item.neutral_tier]
	else:
		return default

def init_dota_info(hero_info, item_info):
	global hero_infos, item_infos
	hero_infos = hero_info
	item_infos = item_info

def get_hero_name(hero_id):
	return hero_infos[hero_id]["name"]

async def get_hero_image(hero_id):
	try:
		return Image.open(hero_infos[hero_id]["image"][1:])
	except KeyError:
		return Image.new('RGBA', (10, 10), (0, 0, 0, 0))

async def get_hero_icon(hero_id):
	try:
		return Image.open(hero_infos[hero_id]["icon"][1:])
	except KeyError:
		return Image.new('RGBA', (10, 10), (0, 0, 0, 0))

async def get_hero_portrait(hero_id):
	try:
		return Image.open(hero_infos[hero_id]["portrait"][1:])
	except KeyError:
		return Image.new('RGBA', (10, 10), (0, 0, 0, 0))

async def get_item_image(item_id):
	try:
		return Image.open(item_infos[item_id]["icon"][1:])
	except KeyError:
		return Image.new('RGBA', (10, 10), (0, 0, 0, 0))

async def draw_courage(hero_id, icon_ids):
	# scaled to 128 height
	hero_image = await get_hero_portrait(hero_id)
	hero_image = hero_image.resize((97, 128), Image.ANTIALIAS)

	table = Table(background="#000000")
	table.add_row([
		ColorCell(color="white", width=97, height=64),
		ImageCell(img=await get_item_image(icon_ids[0])),
		ImageCell(img=await get_item_image(icon_ids[1])),
		ImageCell(img=await get_item_image(icon_ids[2]))
	])
	table.add_row([
		ColorCell(color="white", width=97, height=64),
		ImageCell(img=await get_item_image(icon_ids[3])),
		ImageCell(img=await get_item_image(icon_ids[4])),
		ImageCell(img=await get_item_image(icon_ids[5]))
	])
	image = table.render()
	image = paste_image(image, hero_image, 0, 0)

	fp = BytesIO()
	image.save(fp, format="PNG")
	fp.seek(0)

	return fp