import discord
from discord.ext import tasks
import numpy as np
from new_system.back_end.manage_db import DBManager
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import io
from urllib.request import Request, urlopen
import random
import asyncio
import g4f

g4f.logging = True # enable logging
g4f.check_version = False # Disable automatic version checking
current_model = "gpt-3.5-turbo"
#current_model=g4f.models.gpt_4


## Here set your appropriate discord ids etc.
coffee_channel_id = 0
coffee_group = ''
some_admin_id = 0
admin_ids = [some_admin_id]
admin_mention = ''
for admin in admin_ids:
    admin_mention += '<@{}> '.format(admin)
admin_mention = admin_mention[:-1]

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

@tasks.loop(hours=24)
async def greeting_in_the_morning():
    now = datetime.now()
    seconds_until_working_hours = (timedelta(hours=24) - (now - now.replace(hour=9, minute=45, second=0, microsecond=0))).total_seconds() % (24 * 3600)
    # filter weekend (optional)
    day = (now + timedelta(seconds=seconds_until_working_hours)).weekday()
    if day >= 5:
        return

    await asyncio.sleep(seconds_until_working_hours)
    channel = await client.fetch_channel(coffee_channel_id)
    await channel.send("Good Morning!\nHow about a cup of coffee?")

@tasks.loop(hours=24)
async def first_coffee_of_the_day():
    now = datetime.now()
    seconds_until_next_day = (timedelta(hours=24) - (now - now.replace(hour=0, minute=1, second=0, microsecond=0))).total_seconds() % (24 * 3600)
    midnight_today = now.replace(hour=0, minute=1, second=0, microsecond=0)
    ## filter weekend (optional)
    # day = (now + timedelta(seconds=seconds_until_next_day)).weekday()
    # if day >= 5:
    #     return

    coffee_data = db.getCoffeeDataByTimeFrame(start_date=midnight_today)
    if len(coffee_data) != 0:
        await asyncio.sleep(seconds_until_next_day)
        now = datetime.now()
        midnight_today = now.replace(hour=0, minute=1, second=0, microsecond=0)

    user_id = -1
    first_coffee_not_detected = True
    while first_coffee_not_detected:
        coffee_data = db.getCoffeeDataByTimeFrame(start_date=midnight_today)
        if (len(coffee_data) > 0):
            first_coffee_not_detected = False
            user_id = coffee_data[0][0]
        else:
            now = datetime.now()
            seconds_until_next_day = (timedelta(hours=24) - (now - now.replace(hour=0, minute=1, second=0, microsecond=0))).total_seconds() % (24 * 3600)
            if (seconds_until_next_day < 5*60):
                print("[Info] ({}) No coffees today. Therefore, no first coffee of the day message.".format(now))
                return
            await asyncio.sleep(60)

    #get name of first coffee person
    if (user_id < 0):
        print("[Error] Could not get user id of first coffee of the day")
        return

    first_name, last_name = db.getName(user_id)
    channel = await client.fetch_channel(coffee_channel_id)
    await channel.send("First coffee of the day: {} {}".format(first_name, last_name))

@tasks.loop(hours=24)
async def coffee_summary_message():
    now = datetime.now()
    seconds_to_wait = (timedelta(hours=24) - (now - now.replace(hour=18, minute=00, second=0, microsecond=0))).total_seconds() % (24 * 3600)
    # filter weekend (optional)
    day = (now + timedelta(seconds=seconds_to_wait)).weekday()
    if day >= 5:
        return
    ## wait until reminder
    await asyncio.sleep(seconds_to_wait)
    ## bring the reminder and wait another 30min
    msg = "REMINDER! Did you bill all your coffees already?"
    channel = await client.fetch_channel(coffee_channel_id)
    await channel.send(msg)
    await asyncio.sleep(30 * 60)

    # get total coffees of today
    res = db.getCoffeeDataByTimeFrame(start_date = datetime.today().replace(hour=0,minute=0,second=0,microsecond=0))
    num_coffees = len(res)
    prompt = ""
    if num_coffees == 0:
        prompt = "Write a 1-2 sentence comment that no coffees have been consumed today. Let people know you're extremely sad and disappointed. It's the worst day ever! Just answer with the message."
    elif num_coffees >= 1 and num_coffees < 11:
        prompt = f"Write a 1-2 sentence comment about the extremely low coffee consumption at our institute. Let people know you're disappointed and angry. It has been only {num_coffees} coffees. Just answer with the message."
    elif num_coffees >= 11 and num_coffees < 16:
        prompt = f"Write a 1-2 sentence comment about the low coffee consumption at our institute. Let people know you're disappointed. It has been only {num_coffees} coffees. Just answer with the message."
    elif num_coffees >= 16 and num_coffees < 21:
        prompt = f"Write a 1-2 sentence comment about the low coffee consumption at our institute. Let people know you're disappointed. It has been only {num_coffees} coffees. Make it passive aggressive. Just answer with the message."
    elif num_coffees >= 21 and num_coffees < 26:
        prompt = f"Write a 1-2 sentence comment about the low coffee consumption at our institute. Let people know they should drink more. It has been only {num_coffees} coffees. Make it passive aggressive. Just answer with the message."
    elif num_coffees >= 26 and num_coffees < 31:
        prompt = f"Write a 1-2 sentence comment about the not so great coffee consumption at our institute. Let people know that there is potential for more. It has been only {num_coffees} coffees. Make it encouraging. Just answer with the message."
    elif num_coffees >= 31 and num_coffees < 36:
        prompt = f"Write a 1-2 sentence comment about the okay coffee consumption at our institute. Let people know one more would be possible. It has been {num_coffees} coffees. Put in a little praise. Just answer with the message."
    elif num_coffees >= 36:
        prompt = f"Write a 1-2 sentence comment about the large coffee consumption at our institute. Let people know they are doing great. It has been {num_coffees} coffees. Put in a big praise. Just answer with the message."

    # generate message
    response = "<!DOCTYPE html>"
    while "<!DOCTYPE html>" in response:
        response = await g4f.ChatCompletion.create_async(
            model=current_model,
            messages=[{"role": "user", "content": prompt}],
        )

    if ('\n\n' in response):
        response = response.split('\n\n')[1]

    channel = await client.fetch_channel(coffee_channel_id)
    await channel.send(response)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    #greeting_in_the_morning.start()
    coffee_summary_message.start()
    first_coffee_of_the_day.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != coffee_channel_id and message.channel.type != discord.ChannelType.private:
        return

    if client.user in message.mentions and message.channel.id == coffee_channel_id:
        print("Got mentioned. Generating answer...")
        prompt = f"Reply to the message from {message.author.name}: {message.content.replace('<@1106206646310535168>', '')}. Reply as CoffeeBot. Keep it as a short text message and just answer with the message."
        response = "<!DOCTYPE html>"
        while "<!DOCTYPE html>" in response:
            response = await g4f.ChatCompletion.create_async(
                model=current_model,
                messages=[{"role": "user", "content": prompt}],
            )
        if response == "":
            await message.channel.send("Could not generate a response.")
            return
        await message.channel.send(response)
    if message.content.startswith('!'):
        user_id = db.getIDfromDiscordID(message.author.id)
        if (user_id == ""):
            await message.channel.send("I don't know you ...")
            return
        if message.content.startswith('!stats'):
            stats_user_id = user_id
            split = message.content.split(" ", 1)
            if len(split) > 1:
                if (message.author.id in admin_ids):
                    if split[1].isnumeric():
                        stats_user_id = db.getIDfromDiscordID(split[1])
                    else:
                        stats_user_id = db.getIDfromDiscordName(split[1])
                    if stats_user_id == "":
                        msg = "Unknown user."
                        await message.author.send(msg)
                        return
                else:
                    msg="Sorry, you do not have permission to use this command."
                    await message.channel.send(msg)
                    return
            
            first_name, last_name = db.getName(stats_user_id)
            creation_date = db.getCreationDate(stats_user_id)[:10]
            debts = db.getDebts(stats_user_id)
            num_coffees = db.getTotalUserCoffees(stats_user_id)
            cost_coffees = db.getTotalCoffeesEuro(stats_user_id)
            total_paid = db.getTotalPaid(stats_user_id)
            milk_purchased = db.getMilkPurchased(stats_user_id)
            beans_purchased = db.getBeansPurchased(stats_user_id)

            msg = \
            "Printing stats of {} {}\n###############################\nCreation Date: {}\nDebts: {:.2f} Euro\nTotal Coffees: {}\nTotal Coffee Cost: {:.2f} Euro\nTotal Payments: {:.2f} Euro\nMilk Purchased: {:.2f} Euro\nBeans Purchased: {:.2f} Euro"\
            .format(first_name, last_name, creation_date, debts, num_coffees, cost_coffees, total_paid, milk_purchased, beans_purchased)
            await message.author.send(msg)

        elif message.content.startswith('!today'):
            img = getToday()
            graph = discord.File(img, filename="today.png")
            await message.channel.send(file=graph)

        elif message.content.startswith('!meme'):
            with open('memes.txt', 'r') as f:
                lines = f.readlines()
                num_lines = len(lines)
                number = random.randint(0, num_lines - 1)
                await message.channel.send(lines[number])

        elif message.content.startswith('!send'):
            if (message.author.id in admin_ids):
                split = message.content.split()
                if len(split) > 1:
                    # check if meme is already in list
                    with open('memes.txt', 'r') as f:
                        for line in f:
                            if line.startswith(split[1]):
                                await message.channel.send("Meme already in list.")
                                return
                    url = split[1] + "\n"
                    with open('memes.txt','a') as f:
                        f.write(url)
                    await message.channel.send("Meme successfully added.")
                else:
                    await message.channel.send("Input invalid.")
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!weekend'):
            if (message.author.id in admin_ids):
                weekend_drinkers = getWeekendDrinkers()
                msg = ""
                
                i = 0
                for line in weekend_drinkers:
                    i += 1
                    msg += line + "\n"
                    if i == 10:
                        await message.author.send(msg)
                        i = 0
                        msg = ""
                if i != 0:
                    await message.author.send(msg)
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!thisweek'):
            img = getWeek(0)
            graph = discord.File(img, filename="thisweek.png")
            await message.channel.send(file=graph)

        elif message.content.startswith('!lastweek'):
            img = getWeek(1)
            graph = discord.File(img, filename="lastweek.png")
            await message.channel.send(file=graph)

        elif message.content.startswith('!myweek'):
            img = getPersonalWeek(user_id, 0)
            graph = discord.File(img, filename="myweek.png")

            split = message.content.split()
            if len(split) > 1:
                if split[1].lower() == "here":
                    await message.channel.send(file=graph)
                else: 
                    await message.author.send(file=graph)
            else:
                await message.author.send(file=graph)

        elif message.content.startswith('!mylastweek'):
            img = getPersonalWeek(user_id, 1)
            graph = discord.File(img, filename="mylastweek.png")

            split = message.content.split()
            if len(split) > 1:
                if split[1].lower() == "here":
                    await message.channel.send(file=graph)
                else: 
                    await message.author.send(file=graph)
            else:
                await message.author.send(file=graph)

        elif message.content.startswith('!overall'):
            img = getOverallTimeFrame()
            graph = discord.File(img, filename="overall.png")
            await message.channel.send(file=graph)

        elif message.content.startswith('!myoverall'):
            img = getPersonalTimeFrame(user_id)
            graph = discord.File(img, filename="myoverall.png")

            split = message.content.split()
            if len(split) > 1:
                if split[1].lower() == "here":
                    await message.channel.send(file=graph)
                else: 
                    await message.author.send(file=graph)
            else:
                await message.author.send(file=graph)

        elif message.content.startswith('!duty'):
            if (message.author.id in admin_ids):
                names = getDutySuggestion()
                msg = "People that should buy the next pack of milk or beans:\n"
                i = 1
                for name in names:
                    msg += "{}. {}\n".format(i, name)
                    i += 1
                await message.author.send(msg)
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!snitch'):
            if (message.author.id in admin_ids):
                snitch_uid = ""
                num = 3
                split = message.content.split()
                if len(split) > 1:
                    if split[1].isdigit():
                        num = int(split[1])
                    else:
                        if split[1].isnumeric():
                            snitch_uid = db.getIDfromDiscordID(split[1])
                        else:
                            if split[1].startswith('"'):
                                split = message.content.split('"')
                            snitch_uid = db.getIDfromDiscordName(split[1])
                            print(len(split))
                        if snitch_uid == "":
                            msg = "Unknown user."
                            await message.author.send(msg)
                            return
                        if len(split) > 2:
                            if split[2].strip().isdigit():
                                num = int(split[2].strip())
                        
                if num > 20:
                    num = 20
                if snitch_uid == "":
                    names, dates = getLastCoffees(num)
                    msg="Last {} coffee drinkers are:\n".format(num)
                    for (name,date) in zip(names,dates):
                        msg+="{} at {}\n".format(name, date)
                    await message.author.send(msg)
                else:
                    name, dates = getMyLastCoffees(snitch_uid, num)
                    msg="Last {} coffees of {}:\n".format(num, name)
                    for date in dates:
                        msg+="{}\n".format(date)
                    await message.author.send(msg)
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!mylast'):
            num = 3
            split = message.content.split()
            if len(split) > 1:
                if split[1].isdigit():
                    num = int(split[1])
            if num > 20:
                num = 20

            name, dates = getMyLastCoffees(user_id, num)

            msg="Last {} coffees of {}:\n".format(num, name)
            for date in dates:
                msg+="{}\n".format(date)
            await message.author.send(msg)

        elif message.content.startswith('!help'):
            command_list = []
            command_list.append("Command List:")
            command_list.append("`!stats [discord_name]`- Print your current user stats. Discord name use is for admins only.")
            command_list.append("`!today` - Get the total consumption distribution of today")
            command_list.append("`!thisweek` - Get the total consumption distribution of this week")
            command_list.append("`!lastweek` - Get the total consumption distribution of last week")
            command_list.append("`!overall` - Get the whole recorded consumption distribution")
            command_list.append("`!myweek [here]` - Get the total personal consumption distribution of this week")
            command_list.append("`!mylastweek [here]` - Get the total personal consumption distribution of last week")
            command_list.append("`!myoverall [here]` - Get the whole personal recorded consumption distribution")
            command_list.append("`!mylast [n]` - Print information about your last `3 or n (1 ... 20)` consumed coffees")
            command_list.append("`!price` - Prints the current coffee price")
            command_list.append("`!pay` - Get some information about how to pay for your coffee")
            command_list.append("`!highscore` - Print the current highscore")
            command_list.append("`!ctc` - Start a call to consume")
            command_list.append("`!meme` - Get a random meme from the list")
            command_list.append("`!send <link>` - Send a link to a meme (admin use only)")
            command_list.append("`!duty` - Print a suggestion for the next bean or milk purchase duty (admin use only)")
            command_list.append("`!snitch [discord_name] [n]` - Print information about the last `3 or n (1 ... 20)` consumed coffees (admin use only). If discord_name given, only for this person.")
            command_list.append("`!ipaid <amount>` - Claim that you made a payment to the coffee admins.")
            command_list.append("`!accept <id>` - Accept the payment claim with a certain id (admin use only).")
            command_list.append("`!buycoffee [n]` - In case you're not having your badge with you, you can also buy `1 or n (1 ... 5)` coffees here.")
            command_list.append("`!fetchnames` - Gathers current names for the registered discord IDs and sends them to the database (admin use only).")
            command_list.append("`!timeframe <start> <end>` - Generates a graph of overall coffee data for the specified time frame. Dates have to be in iso format (e.g. `2023-01-01`); `<end>` can be today.")
            command_list.append("`!mytimeframe <start> <end>` - Generates a graph of you personal coffee data for the specified time frame. Dates have to be in iso format (e.g. `2023-01-01`); `<end>` can be today.")
            command_list.append("`!mypayments` - Returns amount and date of past personal payments.")
            command_list.append("`!triggerbeanwarning` - Creates a warning for critically low bean stock (admin use only).")
            command_list.append("`!triggermilkwarning` - Creates a warning for critically low milk stock (admin use only).")
            command_list.append("`!balance` - Get a plot of the coffee treasury balance over time (admin use only).")
            command_list.append("`!bringmecoffee` - Ask the Bot to bring you coffee.")
            command_list.append("`!prompt [private]` - Test a prompt on the bot (admin use only).")
            command_list.append("`!setcredentials <username> <password>` - Set new credentials for the login on the device. Only works in a private conversation with the bot.")
            
            msg = ""
            for i in range(len(command_list)):
                msg += command_list[i] + "\n"
                if i % 5 == 0 or i == len(command_list)-1:
                    msg = msg[:-1]
                    await message.channel.send(msg)
                    msg = ""

        elif message.content.startswith('!price'):
            price = db.getCurrentCoffeePrice()
            await message.channel.send("The current coffee price is {:.2f} Euro".format(price))

        elif message.content.startswith('!pay'):
            await message.channel.send("For direct payments we only accept cash.\nAlternatively, you can buy the next batch of coffee beans or milk and have it count as payment.\nHand over your receipt or cash to {}.".format(admin_mention))

        elif message.content.startswith('!highscore'):
            res = getHighscore()
            msg = "Highscore of active users:\n"
            if (message.author.id in admin_ids):
                for i in range(res.shape[1]):
                    msg+="{}\t{}\n".format(res[0,i], res[1,i])
                await message.author.send(msg)
            else:
                for i in range(res.shape[1]):
                    msg+="{}\t{}\n".format(res[0,i], "anonymous{}".format(i))
                await message.channel.send(msg)

        elif message.content.startswith('!ctc'):
            if message.channel.id != coffee_channel_id:
                msg = "You cannot start a call to consume in a private conversation or in this channel."
                await message.channel.send(msg)
                return

            prompt = "Write a 1-2 sentence message that commands everyone to go and consume coffee at once. Just answer with the message."

            response = "<!DOCTYPE html>"
            while "<!DOCTYPE html>" in response:
                response = await g4f.ChatCompletion.create_async(
                    model=current_model,
                    messages=[{"role": "user", "content": prompt}],
                )

            print(response)
            if ('\n\n' in response):
                response = response.split('\n\n')[1]

            msg = f"<@{message.author.id}> has started a call to consume for {hot_beverage_junkies}.\n{response}"
            await message.channel.send(msg)

        elif message.content.startswith('!ipaid'):
            split = message.content.split()
            if len(split) > 1 and is_float(split[1]):
                ## insert pending payment
                amount = float(split[1])
                payment_id = db.insertPendingPayment(user_id, amount)
                first_name, last_name = db.getName(user_id)
                ## bcast to admins
                for admin in admin_ids:
                    admin_channel = await client.fetch_user(admin)
                    await admin_channel.send("{} {} claims to have paid {:.2f} Euro. The payment id is {}".format(first_name, last_name, amount, payment_id))
                msg = "Your payment (id {}) has been added as pending.\nYou'll get a message when the payment has been accepted.".format(payment_id)
                await message.channel.send(msg)
            else:
                msg="Give amount or format amount as valid float (e.g. 12.90)."
                await message.channel.send(msg)
        
        elif message.content.startswith('!accept'):
            if (message.author.id in admin_ids):
                split = message.content.split()
                if len(split) > 1 and split[1].isnumeric():
                    pending_id = int(split[1])
                    user_of_pending_payment = db.transferPendingPayment(pending_id)
                    discord_id_of_pending_payment = db.getDiscordID(user_of_pending_payment)
                    if user_of_pending_payment == "" or discord_id_of_pending_payment == "":
                        msg = "Invalid pending payment ID. Maybe the payment is already accepted."
                        await message.channel.send(msg)
                        return
                    else:
                        user_discord_channel = await client.fetch_user(int(discord_id_of_pending_payment))
                        await user_discord_channel.send("Your payment with id {} has been accepted.".format(pending_id))
                        await message.author.send("Payment with id {} has been successfully accepted.".format(pending_id))
                else:
                    msg="You have to add a pending payment id"
                    await message.channel.send(msg)
                    return
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!buycoffee'):
            num = 1
            if message.channel.id != coffee_channel_id:
                msg = "You cannot buy coffees in a private conversation or in this channel.\n Go to the **coffee_tea_visus** channel."
                await message.channel.send(msg)
                return
            else:
                split = message.content.split()
                if len(split) > 1:
                    if split[1].isnumeric():
                        num = int(split[1])
                        if num > 5:
                            msg = "You cannot buy more than 5 coffees with one command."
                            await message.channel.send(msg)
                            return
                    else:
                        msg = "Invalid amount."
                        await message.channel.send(msg)
                        return

                for i in range(num):
                    bill_coffee(user_id)

                msg = "Successfully bought {} coffee(s).".format(num)
                await message.channel.send(msg)
        
        elif message.content.startswith('!fetchnames'):
            if (message.author.id in admin_ids):
                data = db.getAllDiscordIDs()
                for uid,discord_id in data:
                    if discord_id != None and discord_id != '':
                        user = await client.fetch_user(int(discord_id))
                        db.changeUsersDiscordName(uid,str(user))
                await message.channel.send("Done.")
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!timeframe'):
            split = message.content.split()
            if len(split) != 3:
                msg="Please provide a start and an end date."
                await message.channel.send(msg)
                return
            else:
                ## check start
                try:
                    start = datetime.strptime("{}".format(split[1]), '%Y-%m-%d')
                except:
                    msg="Please provide a start date in the format of %Y-%m-%d (e.g. 2023-01-01)."
                    await message.channel.send(msg)
                    return
                
                ## check end
                try:
                    if split[2] == "today":
                        end = datetime.now()
                    else:
                        end = datetime.strptime("{}".format(split[2]), '%Y-%m-%d')
                except:
                    msg="Please provide a end date in the format of %Y-%m-%d (e.g. 2023-01-01) or today"
                    await message.channel.send(msg)
                    return
                
                ## create the graph
                img = getOverallTimeFrame(start_date=start, end_date=end)
                graph = discord.File(img, filename="timeframe.png")
                await message.channel.send(file=graph)

        elif message.content.startswith('!mytimeframe'):
            split = message.content.split()
            if len(split) != 3:
                msg="Please provide a start and an end date."
                await message.channel.send(msg)
                return
            else:
                ## check start
                try:
                    start = datetime.strptime("{}".format(split[1]), '%Y-%m-%d')
                except:
                    msg="Please provide a start date in the format of %Y-%m-%d (e.g. 2023-01-01)."
                    await message.channel.send(msg)
                    return
                
                ## check end
                try:
                    if split[2] == "today":
                        end = datetime.now()
                    else:
                        end = datetime.strptime("{}".format(split[2]), '%Y-%m-%d')
                except:
                    msg="Please provide a end date in the format of %Y-%m-%d (e.g. 2023-01-01) or today"
                    await message.channel.send(msg)
                    return
                
                img = getPersonalTimeFrame(user_id, start_date=start, end_date=end)
                graph = discord.File(img, filename="mytimeframe.png")
                await message.author.send(file=graph)

        elif message.content.startswith('!test'):
            if (message.author.id in admin_ids):
                today = datetime.today()
                yesterday = today - timedelta(days = 1)
                start = datetime.strptime("2023-06-20", '%Y-%m-%d')
                end = datetime.strptime("2023-06-21", '%Y-%m-%d')
                res = db.getCoffeeDataByTimeFrame(start_date=start,end_date=end)
                print(res)
                print(len(res))
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!mypayments'):
            amounts, dates = getPersonalPayments(user_id)
            first_name, last_name = db.getName(user_id)
            msg = "{} {} payment overview:\n".format(first_name, last_name)
            for i in range(len(dates)):
                msg+= "{:.2f} Euro paid on {}\n".format(amounts[i],dates[i])
                if (i+1) % 10 == 0:
                    await message.author.send(msg)
                    msg = ""
            if msg != "":
                await message.author.send(msg)

        elif message.content.startswith('!triggerbeanwarning'):
            if (message.author.id in admin_ids):
                channel = await client.fetch_channel(coffee_channel_id)
                msg = "{}\n:rotating_light: :rotating_light: :rotating_light:  !!! WARNING !!! :rotating_light: :rotating_light: :rotating_light:\n\n ~ Coffee bean stock is critically low! ~ \n\n:rotating_light: :rotating_light: :rotating_light:  !!! WARNING !!! :rotating_light: :rotating_light: :rotating_light:".format(hot_beverage_junkies)
                await channel.send(msg)
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!triggermilkwarning'):
            if (message.author.id in admin_ids):
                channel = await client.fetch_channel(coffee_channel_id)
                msg = "{}\n:warning: :warning: :warning:  !!! WARNING !!! :warning: :warning: :warning:\n\n:milk: Milk stock is critically low! :milk:\n\n:warning: :warning: :warning:  !!! WARNING !!! :warning: :warning: :warning:".format(hot_beverage_junkies)
                await channel.send(msg)
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!balance'):
            if (message.author.id in admin_ids):
                img = getBalance()
                graph = discord.File(img, filename="balance.png")
                await message.channel.send(file=graph)
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)

        elif message.content.startswith('!bringmecoffee'):
            await message.channel.send("Of cause my dear.\nThe coffee will be right at your desk.")

        elif message.content.startswith('!prompt'):
            if (message.author.id in admin_ids):
                channel = await client.fetch_channel(coffee_channel_id)
                split = message.content.split()
                response = "<!DOCTYPE html>"
                if (len(split) > 1):
                    if split[1] == "private":
                        channel = await client.fetch_user(admin[0])
                        prompt = message.content.split(" ", 2)[2]
                        print(prompt)
                    else:
                        prompt = message.content.split(" ", 1)[1]
                        print(prompt)
                    while "<!DOCTYPE html>" in response:
                        response = await g4f.ChatCompletion.create_async(
                            model=current_model,
                            messages=[{"role": "user", "content": prompt}],
                        )
                else:
                    msg="Invalid: Empty prompt."
                    await message.channel.send(msg)
                    return
                
                print(response)
                if ('\n\n' in response):
                    response = response.split('\n\n')[1]

                await channel.send(response)
            else:
                msg="Sorry, you do not have permission to use this command."
                await message.channel.send(msg)
        elif message.content.startswith('!setcredentials'):
            if message.channel.type != discord.ChannelType.private:
                await message.channel.send("Please use a private conversation for that!")
                return
            else:
                split = message.content.split()
                if (len(split) != 3):
                    await message.channel.send("Expected format: !setcredentials username password. No spaces in username and password allowed.")
                    return
                else:
                    db.setUserCredentials(user_id, split[1], split[2])
                    await message.channel.send("Successfully set new credentials.")
        else:
            msg = "Command invalid ..."
            await message.channel.send(msg)
            
def getHighscore():
    data = db.getTotalCoffeesAllUsers()

    data_with_key = {}
    keys = ["first_name", "last_name", "count", "inactive"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            data_with_key[keys[i]].append(row[i])
    
    active = np.invert(np.array(data_with_key["inactive"], dtype=bool))
    # use only active entries
    count = np.array(data_with_key["count"])[active]
    first_name = np.array(data_with_key["first_name"])[active]
    last_name = np.array(data_with_key["last_name"])[active]

    sort_array = np.argsort(count)[::-1]; ## reverse
    
    count_sorted = count[sort_array]
    first_name_sorted = first_name[sort_array]
    last_name_sorted = last_name[sort_array]

    hs_count = []
    hs_name = []
    for i in range(10):
        hs_name.append("{} {}".format(first_name_sorted[i], last_name_sorted[i]))
        hs_count.append(count_sorted[i])

    return np.array((hs_count,hs_name))

 
def getDutySuggestion():
    data = db.getTableData("user_balance")

    data_with_key = {}
    keys = ["count", "balance", "user_id", "rfid", "first_name", "last_name", "date"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            data_with_key[keys[i]].append(row[i])

    debts = -1.0 * np.array(data_with_key["balance"])
    first_id = np.argmax(debts)
    first_id_name = "{} {}".format(data_with_key["first_name"][first_id], data_with_key["last_name"][first_id])
    debts[first_id] = 0
    second_id = np.argmax(debts)
    second_id_name = "{} {}".format(data_with_key["first_name"][second_id], data_with_key["last_name"][second_id])
    debts[second_id] = 0
    third_id = np.argmax(debts)
    third_id_name = "{} {}".format(data_with_key["first_name"][third_id], data_with_key["last_name"][third_id])

    return [first_id_name, second_id_name, third_id_name]


def getWeekendDrinkers():
    data = db.getCoffeeData()
    data_with_key = {}
    keys = ["user_id", "price", "date"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            if keys[i] == "date":
                data_with_key[keys[i]].append(datetime.strptime(row[i].split(".")[0], '%Y-%m-%d %H:%M:%S'))
            else:
                data_with_key[keys[i]].append(row[i])

    # accumulate data
    all_dates = []
    for date in  data_with_key["date"]:
        all_dates.append(date.date())

    all_dates = np.array(all_dates).tolist()
    data_with_key["user_id"] = np.array(data_with_key["user_id"])
    data_with_key["price"] = np.array(data_with_key["price"])
    data_with_key["date"] = np.array(data_with_key["date"])

    #find the saturday drinker
    weekend_drinker = []
    for i in range(len(all_dates)):
        if all_dates[i].weekday() >= 5:
            uid = data_with_key["user_id"][i]
            name = db.getName(uid)
            string = "Weekend drinker {} on {}".format(name,all_dates[i])
            weekend_drinker.append(string)

    return weekend_drinker


def getToday():
    request_date = datetime.today().date()

    data = db.getCoffeeData()
    data_with_key = {}
    keys = ["user_id", "price", "date"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            if keys[i] == "date":
                data_with_key[keys[i]].append(datetime.strptime(row[i].split(".")[0], '%Y-%m-%d %H:%M:%S'))
            else:
                data_with_key[keys[i]].append(row[i])

    # accumulate data
    all_dates = []
    for date in  data_with_key["date"]:
        all_dates.append(date.date())

    all_dates = np.array(all_dates).tolist()
    data_with_key["user_id"] = np.array(data_with_key["user_id"])
    data_with_key["price"] = np.array(data_with_key["price"])
    data_with_key["date"] = np.array(data_with_key["date"])

    seen = set()
    unique_dates = [x for x in all_dates if x not in seen and not seen.add(x)]
    date_count = []
    for date in unique_dates:
        date_count.append(all_dates.count(date))

    todays_hours = []
    request_date = datetime.today().date()
    for i in range(len(all_dates)):
        if all_dates[i] == request_date:
            todays_hours.append(data_with_key["date"][i].hour)

    seen = set()
    unique_hours = [x for x in todays_hours if x not in seen and not seen.add(x)]
    hours_count = []
    for hour in unique_hours:
        hours_count.append(todays_hours.count(hour))

    fig, ax = plt.subplots(1, 1, figsize=(8, 4), constrained_layout=True)
    ax.bar(unique_hours, hours_count)
    ax.set_xlabel("time on {}".format(request_date))
    ax.set_ylabel("#coffees")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlim([0,24])
    ax.xaxis.set_ticks(np.arange(0, 24, 1.0))
    labels = ax.get_xticks().tolist()
    new_labels = [str(int(label))+":00" for label in labels]
    ax.set_xticklabels(new_labels)
    # Rotates and right-aligns the x labels so they don't crowd each other.
    for label in ax.get_xticklabels(which='major'):
        label.set(rotation=30, horizontalalignment='right')

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    return buf


def getLastCoffees(num = 3):

    data = db.getCoffeeData(num)
    data_with_key = {}
    keys = ["user_id", "price", "date"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            if keys[i] == "date":
                data_with_key[keys[i]].append(datetime.strptime(row[i].split(".")[0], '%Y-%m-%d %H:%M:%S'))
            else:
                data_with_key[keys[i]].append(row[i])

    # accumulate data
    all_dates = []
    for date in  data_with_key["date"]:
        all_dates.append(date.date())

    all_dates = np.array(all_dates).tolist()
    data_with_key["user_id"] = np.array(data_with_key["user_id"])
    data_with_key["price"] = np.array(data_with_key["price"])
    data_with_key["date"] = np.array(data_with_key["date"])


    if num > len(data_with_key["date"]):
        num = len(data_with_key["date"])

    names = []
    dates = []
    for i in range(-num,0):
        uid = data_with_key["user_id"][i]
        fist_name, last_name = db.getName(uid)
        names.append("{} {}".format(fist_name, last_name))
        dates.append(data_with_key["date"][i])

    return reversed(names), reversed(dates)


def getMyLastCoffees(user_id, num = 3):

    data = db.getCoffeesOfUser(user_id, num)
    data_with_key = {}
    keys = ["price", "date"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            if keys[i] == "date":
                data_with_key[keys[i]].append(datetime.strptime(row[i].split(".")[0], '%Y-%m-%d %H:%M:%S'))
            else:
                data_with_key[keys[i]].append(row[i])

    # accumulate data
    all_dates = []
    for date in  data_with_key["date"]:
        all_dates.append(date.date())

    all_dates = np.array(all_dates).tolist()
    data_with_key["price"] = np.array(data_with_key["price"])
    data_with_key["date"] = np.array(data_with_key["date"])

    if num > len(data_with_key["date"]):
        num = len(data_with_key["date"])

    first_name, last_name = db.getName(user_id)
    name = "{} {}".format(first_name, last_name)
    dates = []
    for i in range(-num,0):
        dates.append(data_with_key["date"][i])

    return name, reversed(dates)


def getWeek(week_id):

    request_date = datetime.today().date()

    if (week_id == 0):
        last_monday = request_date - timedelta(days=request_date.weekday())
        coming_sunday = request_date + timedelta(days=6-request_date.weekday())
    else:
        last_monday = request_date - timedelta(days=request_date.weekday() + 7)
        coming_sunday = last_monday + timedelta(days=6)

    xlim_min = datetime.fromisoformat((last_monday - timedelta(days=1)).isoformat())
    xlim_max = datetime.fromisoformat((coming_sunday + timedelta(days=1)).isoformat())

    data = db.getCoffeeDataByTimeFrame(start_date=xlim_min,end_date=xlim_max)
    data_with_key = {}
    keys = ["user_id", "price", "date"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            if keys[i] == "date":
                data_with_key[keys[i]].append(datetime.strptime(row[i].split(".")[0], '%Y-%m-%d %H:%M:%S'))
            else:
                data_with_key[keys[i]].append(row[i])

    # accumulate data
    all_dates = []
    for date in  data_with_key["date"]:
        all_dates.append(date.date())

    all_dates = np.array(all_dates).tolist()
    data_with_key["user_id"] = np.array(data_with_key["user_id"])
    data_with_key["price"] = np.array(data_with_key["price"])
    data_with_key["date"] = np.array(data_with_key["date"])

    seen = set()
    unique_dates = [x for x in all_dates if x not in seen and not seen.add(x)]
    date_count = []
    for date in unique_dates:
        date_count.append(all_dates.count(date))

    fig, ax = plt.subplots(1, 1, figsize=(8, 4), constrained_layout=True)
    ax.bar(unique_dates, date_count)
    ax.set_xlim([xlim_min, xlim_max])
    ax.set_xticks([last_monday, coming_sunday])
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=[0,1,2,3,4,5,6]))
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True)
    ax.set_xlabel("date")
    ax.set_ylabel("#coffees")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %a'))
    # Rotates and right-aligns the x labels so they don't crowd each other.
    i = 0
    for label in ax.get_xticklabels(which='major'):
        if (i == 0 or i == len(ax.get_xticklabels(which='major'))):
            label.set(rotation=30, horizontalalignment='right', visible=False)
        else:
            label.set(rotation=30, horizontalalignment='right')
        i = i + 1

        

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    return buf


def getPersonalWeek(user_id, week_id):
    first_name, last_name = db.getName(user_id)
    name = "{} {}".format(first_name, last_name)

    request_date = datetime.today().date()

    if (week_id == 0):
        last_monday = request_date - timedelta(days=request_date.weekday())
        coming_sunday = request_date + timedelta(days=6-request_date.weekday())
        title = "This weeks coffees of {}".format(name)
    elif(week_id == 1):
        last_monday = request_date - timedelta(days=request_date.weekday() + 7)
        coming_sunday = last_monday + timedelta(days=6)
        title = "Last weeks coffees of {}".format(name)
    else:
        return

    xlim_min = datetime.fromisoformat((last_monday - timedelta(days=1)).isoformat())
    xlim_max = datetime.fromisoformat((coming_sunday + timedelta(days=1)).isoformat())

    data = db.getCoffeesOfUserByTimeFrame(user_id, start_date=xlim_min, end_date=xlim_max)


    data_with_key = {}
    keys = ["price", "date"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            if keys[i] == "date":
                data_with_key[keys[i]].append(datetime.strptime(row[i].split(".")[0], '%Y-%m-%d %H:%M:%S'))
            else:
                data_with_key[keys[i]].append(row[i])

    # accumulate data
    all_dates = []
    for date in  data_with_key["date"]:
        all_dates.append(date.date())

    all_dates = np.array(all_dates).tolist()
    data_with_key["price"] = np.array(data_with_key["price"])
    data_with_key["date"] = np.array(data_with_key["date"])

    seen = set()
    unique_dates = [x for x in all_dates if x not in seen and not seen.add(x)]
    date_count = []
    for date in unique_dates:
        date_count.append(all_dates.count(date))


    fig, ax = plt.subplots(1, 1, figsize=(8, 4), constrained_layout=True)
    ax.set_title(title)
    ax.bar(unique_dates, date_count)
    ax.set_xlim([xlim_min, xlim_max])
    ax.set_xticks([last_monday, coming_sunday])
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=[0,1,2,3,4,5,6]))
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True)
    ax.set_xlabel("date")
    ax.set_ylabel("#coffees")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %a'))
    # Rotates and right-aligns the x labels so they don't crowd each other.
    i = 0
    for label in ax.get_xticklabels(which='major'):
        if (i == 0 or i == len(ax.get_xticklabels(which='major'))):
            label.set(rotation=30, horizontalalignment='right', visible=False)
        else:
            label.set(rotation=30, horizontalalignment='right')
        i = i + 1

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    return buf


def getPersonalTimeFrame(user_id, start_date="", end_date=""):

    start = datetime.strptime("2022-06-21 07:00:00", '%Y-%m-%d %H:%M:%S')
    if start_date != "":
        start = start_date
    
    stop = datetime.now()
    if end_date != "":
        stop = end_date

    data = db.getCoffeesOfUserByTimeFrame(user_id, start_date=start, end_date=stop)
    first_name, last_name = db.getName(user_id)
    name = "{} {}".format(first_name, last_name)

    data_with_key = {}
    keys = ["user_id", "price", "date"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            if keys[i] == "date":
                data_with_key[keys[i]].append(datetime.strptime(row[i].split(".")[0], '%Y-%m-%d %H:%M:%S'))
            else:
                data_with_key[keys[i]].append(row[i])

    # accumulate data
    all_dates = []
    for date in  data_with_key["date"]:
        all_dates.append(date.date())

    all_dates = np.array(all_dates).tolist()
    data_with_key["user_id"] = np.array(data_with_key["user_id"])
    data_with_key["price"] = np.array(data_with_key["price"])
    data_with_key["date"] = np.array(data_with_key["date"])

    seen = set()
    unique_dates = [x for x in all_dates if x not in seen and not seen.add(x)]
    date_count = []
    for date in unique_dates:
        date_count.append(all_dates.count(date))

    title = "Coffees of {} between {} and {}".format(name, start, stop)

    fig, ax = plt.subplots(1, 1, figsize=(24, 4), constrained_layout=True)
    ax.set_title(title)
    ax.bar(unique_dates, date_count)
    ax.set_xlim([start - timedelta(days=1), stop])
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=[0]))
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True)
    ax.set_xlabel("date")
    ax.set_ylabel("#coffees")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %a'))
    # Rotates and right-aligns the x labels so they don't crowd each other.
    for label in ax.get_xticklabels(which='major'):
            label.set(rotation=30, horizontalalignment='right')
        
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    return buf


def getOverallTimeFrame(start_date="", end_date=""):

    start = datetime.strptime("2022-06-21 07:00:00", '%Y-%m-%d %H:%M:%S')
    if start_date != "":
        start = start_date

    stop = datetime.now()
    if end_date != "":
        stop = end_date

    data = db.getCoffeeDataByTimeFrame(start_date=start, end_date=stop)

    data_with_key = {}
    keys = ["user_id", "price", "date"]
    for key in keys:
        data_with_key[key] = []

    for row in data:
        for i in range(len(row)):
            if keys[i] == "date":
                data_with_key[keys[i]].append(datetime.strptime(row[i].split(".")[0], '%Y-%m-%d %H:%M:%S'))
            else:
                data_with_key[keys[i]].append(row[i])

    # accumulate data
    all_dates = []
    for date in  data_with_key["date"]:
        all_dates.append(date.date())

    all_dates = np.array(all_dates).tolist()
    data_with_key["user_id"] = np.array(data_with_key["user_id"])
    data_with_key["price"] = np.array(data_with_key["price"])
    data_with_key["date"] = np.array(data_with_key["date"])

    seen = set()
    unique_dates = [x for x in all_dates if x not in seen and not seen.add(x)]
    date_count = []
    for date in unique_dates:
        date_count.append(all_dates.count(date))

    fig, ax = plt.subplots(1, 1, figsize=(24, 4), constrained_layout=True)
    ax.bar(unique_dates, date_count)
    ax.set_xlim([start - timedelta(days=1), stop])
    loc = mdates.WeekdayLocator(byweekday=[0], interval=2)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True)
    ax.set_xlabel("date")
    ax.set_ylabel("#coffees")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %a'))
    # Rotates and right-aligns the x labels so they don't crowd each other.
    for label in ax.get_xticklabels(which='major'):
            label.set(rotation=30, horizontalalignment='right')

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    return buf


def getPersonalPayments(user_id):
    data = db.getPaymentDataOfUser(user_id)
    amounts = []
    dates = []
    for amount, date in data:
        amounts.append(amount)
        dates.append(date)
    return amounts, dates


def getBalance():
    initial_start = datetime.strptime("2022-06-27 00:00:00", '%Y-%m-%d %H:%M:%S')

    initial_coffee_data = db.getCoffeeDataByTimeFrame(end_date=initial_start)
    initial_coffee_cost = 0.0
    for data in initial_coffee_data:
        initial_coffee_cost += data[1] #price

    initial_payment_data = db.getPaymentDataByTimeFrame(end_date=initial_start)
    initial_payments = 0.0
    for data in initial_payment_data:
        initial_payments += data[0] #price

    time = []
    time.append(initial_start)
    balance = []
    balance.append(initial_coffee_cost - initial_payments)
    print(initial_coffee_cost - initial_payments)

    start = initial_start
    end = initial_start + timedelta(days=7)
    while (end < datetime.today()):
        coffee_data = db.getCoffeeDataByTimeFrame(start_date=start, end_date=end)
        coffee_cost = 0.0
        for data in coffee_data:
            coffee_cost += data[1]

        payment_data = db.getPaymentDataByTimeFrame(start_date=start, end_date=end)
        payments = 0.0
        for data in payment_data:
            payments += data[0] #price

        time.append(end)
        old_balance = balance[-1]
        balance.append(old_balance + coffee_cost - payments)

        start = end
        end = end + timedelta(days=7)

    print(len(balance))

    fig, ax = plt.subplots(1, 1, figsize=(12, 4), constrained_layout=True)
    ax.plot(time, balance, 'o-')
    ax.set_xlim([initial_start, time[-1]])
    loc = mdates.WeekdayLocator(byweekday=[0], interval=2)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True)
    ax.set_xlabel("date")
    ax.set_ylabel("balance [Euro]")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %a'))
    # Rotates and right-aligns the x labels so they don't crowd each other.
    for label in ax.get_xticklabels(which='major'):
            label.set(rotation=30, horizontalalignment='right')

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    return buf


def bill_coffee(user_id):
    def checkNotNoneType(t):
        if 'NoneType' in str(t) or 'None' in str(t):
            return False
        else:
            return True

    THRESHOLD_COFFEE = 1.0
    THRESHOLD_MILK = 1.0
    THRESHOLD_SUGAR = 1.0

    CUP_INFILL = 0.3

    # in grams
    COFFEE_WEIGHT_SMALL_INSERT = 10
    COFFEE_WEIGHT_LARGE_INSERT = 18
    COFFEE_WEIGHT_DEFAULT_INSERT = COFFEE_WEIGHT_SMALL_INSERT
    # teaspoon in grams
    TSP_WEIGHT = 5.69

    # buy coffee
    db.billCoffee(user_id)

    # Coffee Amount Calculation
    coffee_bean_id = db.getRefillBeanID()

    bean_stock = db.getBeanStockOf(coffee_bean_id)


    # get insert for coffee amount measurement
    u_portafilter = db.getUserProfilePortafilter(user_id)

    if u_portafilter == "small":
        c_insert = COFFEE_WEIGHT_SMALL_INSERT
    elif u_portafilter == "large":
        c_insert = COFFEE_WEIGHT_LARGE_INSERT
    else: #default ist small
        c_insert = COFFEE_WEIGHT_DEFAULT_INSERT

    notification_resource_names = []
    if checkNotNoneType(bean_stock):
        cal_coffee = float(bean_stock) - c_insert
        if cal_coffee < 0:
            cal_coffee = 0
        if cal_coffee <= THRESHOLD_COFFEE:
            notification_resource_names.append((coffee_bean_id, cal_coffee))
    else:
        cal_coffee = None

    # Milk Amount Calculation
    milk_type = db.getUserProfileMilkType(user_id)
    milk_stock = db.getStockOfMilkType(milk_type)
    milk_shots = db.getUserProfileMilkShots(user_id)
    milk_product_ids = db.getMilkProductIDsOfTypeInStock(milk_type)

    if milk_product_ids is not None:
        if len(milk_product_ids) > 1:
            lowest_stock = float("inf")
            mp_id_stocks = []
            for mp_id in milk_product_ids:
                mp_id_stock = db.getMilkStockOf(mp_id[0])
                mp_id_stocks.append(mp_id_stock)
                lowest_stock = min(lowest_stock, mp_id_stock)
            if np.isinf(lowest_stock):
                milk_product_id = None
            else:
                milk_stock = lowest_stock
                mp_id_stocks = np.array(mp_id_stocks)
                milk_product_id = np.where(mp_id_stocks == lowest_stock)[0][0]
        else:
            milk_product_id = milk_product_ids[0][0]
    else:
        milk_product_id = None

    def numeric(equation):
        y = equation[:-4].split('/') #removing the " cup" from 1/8 cup and splitting by /
        x = float(y[0])/float(y[1])
        return x

    print(milk_shots)

    if checkNotNoneType(milk_stock) and checkNotNoneType(milk_shots):
        cal_milk = float(milk_stock) - (numeric(milk_shots) * CUP_INFILL)
    elif checkNotNoneType(milk_stock):
        cal_milk = float(milk_stock) - 0
    else:
        cal_milk = None
    
    if cal_milk and cal_milk < 0:
        cal_milk = 0

    # Milk Amount Calculation
    sugar_type = db.getUserProfileSugarType(user_id)
    sugar_amount = db.getSugarTypeAmount(sugar_type)
    sugar_tsp = db.getUserProfileSugarTSP(user_id)

    if checkNotNoneType(sugar_amount) and checkNotNoneType(sugar_tsp):
        cal_sugar = float(sugar_amount) - TSP_WEIGHT * float(sugar_tsp)
    elif checkNotNoneType(sugar_amount):
        cal_sugar = float(sugar_amount) - 0
    else:
        cal_sugar = None

    if cal_sugar and cal_sugar < 0:
        cal_sugar = 0

    print(f"[BILLCOFFEE] Bean_Product_ID: {coffee_bean_id} Milk_Product_ID: {milk_product_id} Sugar_type_ID: {sugar_type}")
    print(f"[BILLCOFFEE] Bean_amount {cal_coffee} Milk_amount {cal_milk} Sugar_amount {cal_sugar}")

    db.updateResourcesOnCoffeeBill(coffee_bean_id, milk_product_id, sugar_type, cal_coffee, cal_milk, cal_sugar)


## MAIN
db = DBManager()

## Start Bot with token
client.run('')