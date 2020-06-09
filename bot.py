# External Libraries
import discord 
import json
from os import path, listdir
from discord.ext import commands
from random import choice   


if __name__ == "__main__":

    # Init Bot and command_prefix
    with open("config.json", "r") as json_data_file:
        config = json.load(json_data_file)
    command_prefixes = config["command_prefix"]
    token = config["token"]
    client = commands.AutoShardedBot(
        command_prefix=commands.when_mentioned_or(*command_prefixes), 
        case_insensitive=True)

    adminUsers = config["admin_users"]
    

    
    # Functions

    @client.event
    async def on_ready():
        #killbot_loop.start()
        
        await client.change_presence(status=discord.Status.online, activity=discord.Game('Albion Online'))
        print("Bot is ready")

        # Load the following functions: rules(), ping(), clear(), test()
        # and the following loops: killbot()
        # Load cogs in folder /cogs
        try:
            currentPath = path.dirname(path.realpath(__file__))
            for filename in listdir(currentPath + "/cogs"):
                if filename.endswith(".py"):
                    client.load_extension(f"cogs.{filename[:-3]}")
            print("Cogs loaded succesfully.")
        except Exception as e:
            print(e)
    
    @client.command()
    async def extension(ctx, option, extension):
        """Reload, load, or unload extensions.
        - Usage: <command-prefix> extension <option> <cog's name>
        - <option> : load, unload, reload
        - Only allowable if user is adminUser.
        """

        # Check if user is in adminUsers
        if str(ctx.author) not in adminUsers:
            await ctx.send(f"No tienes permisos para cambiar las extensiones! {get_name(':eyes:')}")
            return

        try:
            if option == "reload":
                client.reload_extension(f"cogs.{extension}")
                print(f"cogs.{extension} succesfully reloaded")
            elif option == "load":
                client.load_extension(f"cogs.{extension}")
                print(f"cogs.{extension} succesfully loaded")
            elif option == "unload":
                client.unload_extension(f"cogs.{extension}")
                print(f"cogs.{extension} succesfully unloaded")

            # Prompt usage method if option is wrong
            else:
                await ctx.send(
                    f"Usage: `{command_prefixes[0]} extension <option> <extension>`\nOptions: `reload, load, unload`"
                )
                return

        except:
            await ctx.send(f"{extension} extension {option} FAILED.")
            return

        # Success message
        await ctx.send(f"{extension} extension {option.upper()}ED.")


    @client.event
    async def on_member_join(member):
        channel = client.get_channel(config["channel"]["welcome"])
        await channel.send(f'Bienvenido a Barbarian {member.mention}!\n' +
                            'Porfavor cambiate el apodo al nick del juego. ')

    @client.event
    async def on_member_remove(member):
        channel = client.get_channel(config["channel"]["welcome"])
        await channel.send(f'{member.mention} {choice(frases)}')

    """
    @client.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("No tengo ni puta idea de lo que me hablas. Intenta 'bk help'")
        else:
            print('__________________Otro tipo de error!!!_______________________')
            print(error)
    """

    # Bot Run
    client.run(token)
