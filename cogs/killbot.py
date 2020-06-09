import discord
import json
from requests import get
from urllib.request import urlopen
from urllib.error import HTTPError
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from os import path, pardir
from pathlib import Path
from random import choice
from pprint import pprint

class KillBot(commands.Cog):
    """Cog que se encarga de revisar las kills en la API de Albion
    """

    def __init__(self, client):
        self.client = client

        print("Initializing KillBot Cog")
        
        self.URL = "https://gameinfo.albiononline.com/api/gameinfo/events?limit=50&offset=0"
        self.last_kills = []

        with open("config.json", "r") as json_data_file:
        #with open(path.join(pardir, "config.json"), "r") as json_data_file:
            config = json.load(json_data_file)

        self.guild = config["killbot"]["guild"]
        self.players = config["killbot"]["players"]
        self.killer_offsets = config["killer_offsets"]
        self.victim_offsets = config["victim_offsets"]

        self.phrases = config["phrases"]

        self.font50 = ImageFont.truetype("monospace/MonospaceBold.ttf", 50)
        self.font45 = ImageFont.truetype("monospace/MonospaceBold.ttf", 45)
        self.font40 = ImageFont.truetype("monospace/MonospaceBold.ttf", 40)
        self.font8 = ImageFont.truetype("monospace/MonospaceBold.ttf", 8)

        self.admin_users = config["admin_users"]
        self.rules = config["rules"]
        self.debug_channel = client.get_channel(config["channel"]["debug"])

        self.killbot_channel = client.get_channel(config["channel"]["killbot"])

        self.killbot.start()

    @commands.command(aliases=["rules"])
    async def reglas(self, ctx):
        """Muestra las reglas de Barbarian Kingdom.
        """
        rules_str = ""
        for rule in self.rules:
            rules_str += f"{self.rules.index(rule) + 1}. {rule}\n"
        await ctx.send(rules_str)

    @commands.command()
    async def ping(self, ctx):
        """Muestra el ping del bot.
        """

        if str(ctx.author) not in self.admin_users:
            await ctx.send("No tienes permisos para usar esto!\n\t Si piensas que es un error contacta con LaExtrano.")
            return
        await ctx.send(f"Pong! {round(self.client.latency * 1000)}ms")

    @commands.command(aliases=["limpiar"])
    async def clear(self, ctx, amount=0):
        if str(ctx.author) not in self.admin_users:
            await ctx.send("No tienes permisos para usar esto!\n\t Si piensas que es un error contacta con LaExtrano.")
            return
        await ctx.channel.purge(limit=amount + 1)

    @tasks.loop(seconds=1.0)
    async def killbot(self):
        try:
            with urlopen(self.URL) as url:
                data = json.loads(url.read().decode())
        except HTTPError:
            print("Error al solicitar la api")
            return
        except e:
            print(f"Error inesperado: {e}")
            return

        for kill_info in data:

            event_id = kill_info["EventId"]

            
            # Ley de Morgan aplicada a lo anterior
            if ( 
                kill_info["Killer"]["GuildName"] != self.guild
                and kill_info["Victim"]["GuildName"] != self.guild
                and kill_info["Killer"]["Name"] not in self.players
                and kill_info["Victim"]["Name"] not in self.players 
            ):
                continue

            print(f"\nViewing kill {event_id}")

            if event_id in self.last_kills:
                # Kill ya mostrada
                continue
            
            self.last_kills.append(event_id)

            if len(self.last_kills) >= 20:
                self.last_kills.pop(0)
            
            time_stamp = kill_info["TimeStamp"].split("T")[0]
            kill_fame = kill_info["TotalVictimKillFame"]
            group_member_count = kill_info["groupMemberCount"]
            participants_count = len(kill_info["Participants"])

            # Killer Info
            killer_guild_name = kill_info["Killer"]["GuildName"]
            killer_alliance_tag = kill_info["Killer"]["AllianceName"]

            if killer_alliance_tag != "":
                killer_alliance_tag = f"[{killer_alliance_tag}]"
            
            killer_item_power = round(kill_info["Killer"]["AverageItemPower"])
            killer_name = kill_info["Killer"]["Name"]

            # Victim Info
            victim_guild_name = kill_info["Victim"]["GuildName"]
            victim_alliance_tag = kill_info["Victim"]["AllianceName"]

            if victim_alliance_tag != "":
                victim_alliance_tag = f"[{victim_alliance_tag}]"

            victim_item_power = round(kill_info["Victim"]["AverageItemPower"])
            victim_name = kill_info["Victim"]["Name"]

            # Inventory
            victim_inventory_info = kill_info["Victim"]["Inventory"]
            victim_inventory = []

            for item_info in kill_info["Victim"]["Inventory"]:
                if item_info == None:
                    continue
                victim_inventory.append((item_info['Type'], item_info['Quality'], item_info['Count']))
            
            inventory_len = len(victim_inventory)

            if inventory_len < 9: template_n = 1
            elif inventory_len < 17: template_n = 2
            elif inventory_len < 25: template_n = 3
            elif inventory_len < 33: template_n = 4
            elif inventory_len < 41: template_n = 5
            else: template_n = 6

            # Damage and Healing data

            participants_healings = []
            participants_damages = []

            d_full = h_full = False
            for participant in kill_info["Participants"]:

                if not d_full:
                    if len(participants_damages) < 5:
                        participant_damage = participant["DamageDone"]
                        if participant_damage > 0:
                            participant_name = participant["Name"]
                            participants_damages.append((participant_name, round(participant_damage)))
                    else:
                        d_full = True

                if not h_full:
                    if len(participants_healings) < 5:
                        participant_healing = participant["SupportHealingDone"]
                        if participant_healing > 0:
                            participant_name = participant["Name"]
                            participants_healings.append((participant_name, round(participant_healing)))
                    else:
                        h_full = True


            """ Empieza el rellenado de datos en la imagen """

            # LLenado de Items en el inventario
            
            inv_template = Image.open(f"Templates/body_{template_n}.png", "r")

            j = -64
            for i in range(len(victim_inventory)):
                if i % 8 == 0:
                    j += 64
                offset = (2 + 63 * (i % 8), 2 + j)
                
                url = f"https://gameinfo.albiononline.com/api/gameinfo/items/{victim_inventory[i][0]}.png?count=0&quality={victim_inventory[i][1]}"

                img = Image.open(BytesIO(get(url).content)).resize((67, 67))
                inv_template.paste(img, offset, img.convert("RGBA"))

                draw = ImageDraw.Draw(inv_template)
                count = victim_inventory[i][2]

                if count <= 9:
                    draw.text((offset[0] + 48, offset[1] + 45), str(count), (255, 255, 255), font=self.font8)
                elif count <= 99:
                    draw.text((offset[0] + 45, offset[1] + 45), str(count), (255, 255, 255), font=self.font8)
                else:
                    draw.text((offset[0] + 43, offset[1] + 45), str(count), (255, 255, 255), font=self.font8)
            inv_template.save(f"{event_id}_inventory.png")
            inv_template.close()

            # LLenado de Items Equipados


            template = Image.open("Templates/template10.jpg", "r")

            for key in kill_info["Killer"]["Equipment"]:
                if kill_info["Killer"]["Equipment"][key] == None:
                    continue
                
                # Crea el url para la imagen
                item = kill_info["Killer"]["Equipment"][key]["Type"]
                item_quality = kill_info["Killer"]["Equipment"][key]["Quality"]
                
                url = f"https://gameinfo.albiononline.com/api/gameinfo/items/{item}.png?count=0&quality={item_quality}"
                # Crea la imagen a partir del url y adjunta la imagen al template
                img = Image.open(BytesIO(get(url).content)).resize((267, 267))
                
                # Todo Bug Fix at line 219
                #offset = killer_offsets[key]
                offset = self.killer_offsets[key]
                template.paste(img, offset, img.convert("RGBA"))

            
            for key in kill_info["Victim"]["Equipment"]:
                if kill_info["Victim"]["Equipment"][key] == None:
                    continue
                # Crea el url para la image
                item = kill_info["Victim"]["Equipment"][key]["Type"]
                item_quality = kill_info["Victim"]["Equipment"][key]["Quality"]

                url = f"https://gameinfo.albiononline.com/api/gameinfo/items/{item}.png?count=0&quality={item_quality}"

                # Crea la imagen a partir del url y adjunta la imagen al template
                response = get(url)
                img = Image.open(BytesIO(response.content)).resize((267, 267))
                #offset = victim_offsets[key]
                offset = self.victim_offsets[key]
                template.paste(img, offset, img.convert("RGBA"))

            # Escribir texto en el template
            draw = ImageDraw.Draw(template)

            # Killer
            draw.text((73, 40), killer_name, (255, 255, 255), font=self.font50) # Name
            draw.text((753, 1024), str(killer_item_power), (255, 255, 255), font=self.font45) # Ip
            draw.text((73, 135), f'{killer_alliance_tag}{killer_guild_name}', (0, 0, 0), font=self.font45)  # Guild

            # Victim 
            draw.text((1546, 40), victim_name,(255, 255, 255),font=self.font50) # Name
            draw.text((1604, 1024), str(victim_item_power), (255, 255, 255), font=self.font45) # Ip
            draw.text((1546, 135), f'{victim_alliance_tag}{victim_guild_name}', (0, 0, 0), font=self.font45) # Guild
            
            # Fame
            draw.text((1171, 1071), str(kill_fame), (0, 0, 0), font=self.font50) # Fame
            # Date
            draw.text((1100, 1160), time_stamp, (0, 0, 0), font=self.font40) # Date
            # Members count
            draw.text((1020, 300), f"GroupMembers: {group_member_count}", ( 0, 0, 0), font=self.font40)
            # Participants count
            draw.text((1020, 350), f"Participants: {participants_count}", (0, 0, 0), font=self.font40)

            pos = 0
            for data in participants_damages:
                draw.text((1020, 500 + pos * 50), f"{data[0]}: {str(data[1])}", (255, 0, 0), font=self.font40)
                pos += 1

            for data in participants_healings:
                draw.text((1020, 500 + pos * 50), f"{data[0]}: {str(data[1])}", (0, 220, 0), font=self.font40)
                pos += 1

            template.save(f"{event_id}.png")
            template.close()
           
            await self.killbot_channel.send(f"{killer_name} {choice(self.phrases['kill'])} {victim_name}")
            
            await self.killbot_channel.send(file=discord.File(f'{event_id}.png'))
            await self.killbot_channel.send(f"Inventario de {victim_name}")
            await self.killbot_channel.send(file=discord.File(f'{event_id}_inventory.png'))


            file_to_rm = Path(f'{self.last_kills[0]}.png')
            if path.isfile(file_to_rm):
                file_to_rm.unlink()
            else:
                print(f"{file_to_rm} doesn't exist")

            file_to_rm = Path(f'{event_id}_inventory.png')
            if path.isfile(file_to_rm):
                file_to_rm.unlink()
            else:
                print(f"{file_to_rm} doesn't exist")

     

    @commands.command(aliases=["prueba"])
    async def test(self, ctx):
        await self.debug_channel.trigger_typing()
        try:
            with urlopen(self.URL) as url:
                data = json.loads(url.read().decode())
        except HTTPError:
            print("Error al solicitar la api")
            print("Intentando otra vez...")
            await KillBot.test(ctx)
            return
        except e:
            print(f"Error inesperado: {e}")
            return

        kill_info = data[0]
        #pprint(kill_info)

        event_id = kill_info["EventId"]

        print(f"\nViewing kill {event_id}")

        print("Filling data into variables")
        if event_id in self.last_kills:
            # Kill ya mostrada
            return
        
        self.last_kills.append(event_id)

        if len(self.last_kills) >= 20:
            self.last_kills.pop(0)
        
        time_stamp = kill_info["TimeStamp"].split("T")[0]
        kill_fame = kill_info["TotalVictimKillFame"]
        group_member_count = kill_info["groupMemberCount"]
        participants_count = len(kill_info["Participants"])

        # Killer Info
        killer_guild_name = kill_info["Killer"]["GuildName"]
        killer_alliance_tag = kill_info["Killer"]["AllianceName"]

        if killer_alliance_tag != "":
            killer_alliance_tag = f"[{killer_alliance_tag}]"
        
        killer_item_power = round(kill_info["Killer"]["AverageItemPower"])
        killer_name = kill_info["Killer"]["Name"]

        # Victim Info
        victim_guild_name = kill_info["Victim"]["GuildName"]
        victim_alliance_tag = kill_info["Victim"]["AllianceName"]

        if victim_alliance_tag != "":
            victim_alliance_tag = f"[{victim_alliance_tag}]"

        victim_item_power = round(kill_info["Victim"]["AverageItemPower"])
        victim_name = kill_info["Victim"]["Name"]

        # Inventory
        victim_inventory_info = kill_info["Victim"]["Inventory"]
        victim_inventory = []

        for item_info in kill_info["Victim"]["Inventory"]:
            if item_info == None:
                continue
            victim_inventory.append((item_info['Type'], item_info['Quality'], item_info['Count']))
        
        inventory_len = len(victim_inventory)

        if inventory_len < 9: template_n = 1
        elif inventory_len < 17: template_n = 2
        elif inventory_len < 25: template_n = 3
        elif inventory_len < 33: template_n = 4
        elif inventory_len < 41: template_n = 5
        else: template_n = 6

        # Damage and Healing data

        participants_healings = []
        participants_damages = []

        d_full = h_full = False
        for participant in kill_info["Participants"]:

            if not d_full:
                if len(participants_damages) < 5:
                    participant_damage = participant["DamageDone"]
                    if participant_damage > 0:
                        participant_name = participant["Name"]
                        participants_damages.append((participant_name, round(participant_damage)))
                else:
                    d_full = True

            if not h_full:
                if len(participants_healings) < 5:
                    participant_healing = participant["SupportHealingDone"]
                    if participant_healing > 0:
                        participant_name = participant["Name"]
                        participants_healings.append((participant_name, round(participant_healing)))
                else:
                    h_full = True


        """ Empieza el rellenado de datos en la imagen """

        # LLenado de Items en el inventario
        print("Filling data into image")
        await self.debug_channel.trigger_typing()
        inv_template = Image.open(f"Templates/body_{template_n}.png", "r")

        j = -64
        for i in range(len(victim_inventory)):
            if i % 8 == 0:
                j += 64
            offset = (2 + 63 * (i % 8), 2 + j)
            
            url = f"https://gameinfo.albiononline.com/api/gameinfo/items/{victim_inventory[i][0]}.png?count=0&quality={victim_inventory[i][1]}"

            img = Image.open(BytesIO(get(url).content)).resize((67, 67))
            inv_template.paste(img, offset, img.convert("RGBA"))

            draw = ImageDraw.Draw(inv_template)
            count = victim_inventory[i][2]

            if count <= 9:
                draw.text((offset[0] + 48, offset[1] + 45), str(count), (255, 255, 255), font=self.font8)
            elif count <= 99:
                draw.text((offset[0] + 45, offset[1] + 45), str(count), (255, 255, 255), font=self.font8)
            else:
                draw.text((offset[0] + 43, offset[1] + 45), str(count), (255, 255, 255), font=self.font8)
        inv_template.save(f"{event_id}_inventory.png")
        inv_template.close()

        # LLenado de Items Equipados

        template = Image.open("Templates/template10.jpg", "r")

        for key in kill_info["Killer"]["Equipment"]:
            if kill_info["Killer"]["Equipment"][key] == None:
                continue
            
            # Crea el url para la imagen
            item = kill_info["Killer"]["Equipment"][key]["Type"]
            item_quality = kill_info["Killer"]["Equipment"][key]["Quality"]
            
            url = f"https://gameinfo.albiononline.com/api/gameinfo/items/{item}.png?count=0&quality={item_quality}"
            # Crea la imagen a partir del url y adjunta la imagen al template
            img = Image.open(BytesIO(get(url).content)).resize((267, 267))
            
            # Todo Bug Fix at line 219
            #offset = killer_offsets[key]
            offset = self.killer_offsets[key]
            """
            offset_x = (self.killer_offsets[key][0])
            offset_y = (self.killer_offsets[key][1])
            """
            template.paste(img, offset, img.convert("RGBA"))

        
        for key in kill_info["Victim"]["Equipment"]:
            if kill_info["Victim"]["Equipment"][key] == None:
                continue
            # Crea el url para la image
            item = kill_info["Victim"]["Equipment"][key]["Type"]
            item_quality = kill_info["Victim"]["Equipment"][key]["Quality"]

            url = f"https://gameinfo.albiononline.com/api/gameinfo/items/{item}.png?count=0&quality={item_quality}"

            # Crea la imagen a partir del url y adjunta la imagen al template
            img = Image.open(BytesIO(get(url).content)).resize((267, 267))
            #offset = victim_offsets[key]
            offset = self.victim_offsets[key]
            template.paste(img, offset, img.convert("RGBA"))

        print("Filling text data into images")
        # Escribir texto en el template
        draw = ImageDraw.Draw(template)

        # Killer
        draw.text((73, 40), killer_name, (255, 255, 255), font=self.font50) # Name
        draw.text((753, 1024), str(killer_item_power), (255, 255, 255), font=self.font45) # Ip
        draw.text((73, 135), f'{killer_alliance_tag}{killer_guild_name}', (0, 0, 0), font=self.font45)  # Guild

        # Victim 
        draw.text((1546, 40), victim_name,(255, 255, 255),font=self.font50) # Name
        draw.text((1604, 1024), str(victim_item_power), (255, 255, 255), font=self.font45) # Ip
        draw.text((1546, 135), f'{victim_alliance_tag}{victim_guild_name}', (0, 0, 0), font=self.font45) # Guild
        
        # Fame
        draw.text((1171, 1071), str(kill_fame), (0, 0, 0), font=self.font50) # Fame
        # Date
        draw.text((1100, 1160), time_stamp, (0, 0, 0), font=self.font40) # Date
        # Members count
        draw.text((1020, 300), f"GroupMembers: {group_member_count}", ( 0, 0, 0), font=self.font40)
        # Participants count
        draw.text((1020, 350), f"Participants: {participants_count}", (0, 0, 0), font=self.font40)

        pos = 0
        for data in participants_damages:
            draw.text((1020, 500 + pos * 50), f"{data[0]}: {str(data[1])}", (255, 0, 0), font=self.font40)
            pos += 1

        for data in participants_healings:
            draw.text((1020, 500 + pos * 50), f"{data[0]}: {str(data[1])}", (0, 220, 0), font=self.font40)
            pos += 1

        template.save(f"{event_id}.png")
        template.close()
        
        print("Enviando mensajes a discord.")
        await self.debug_channel.send(f"{killer_name} {choice(self.phrases['kill'])} {victim_name}")
        
        await self.debug_channel.send(file=discord.File(f'{event_id}.png'))
        await self.debug_channel.send(f"Inventario de {victim_name}")
        await self.debug_channel.send(file=discord.File(f'{event_id}_inventory.png'))


        file_to_rm = Path(f'{self.last_kills[0]}.png')
        if path.isfile(file_to_rm):
            file_to_rm.unlink()
            print(f'{self.last_kills[0]}.png removed')
        else:
            print(f"{file_to_rm} doesn't exist")

        file_to_rm = Path(f'{event_id}_inventory.png')
        if path.isfile(file_to_rm):
            file_to_rm.unlink()
            print(f'{event_id}_inventory.png removed')
        else:
            print(f"{file_to_rm} doesn't exist")

        """
        if victim_name == "Puchiix":
            user = self.client.get_user(578352120542134273)
            await self.debug_channel.send(f"{user.mention} {choice(self.phrases['personal']['puchiix'])}")
        """


def setup(client):
    client.add_cog(KillBot(client))