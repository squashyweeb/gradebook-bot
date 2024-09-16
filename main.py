import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def grades(ctx):
    url = 'your info'
    headers = {
your info
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        grades_data = {}
        class_items = soup.find_all('div', class_='gb-class-row')

        for cls in class_items:
            try:
                class_name_element = cls.find_previous('div', class_='gb-class-header')
                class_name = class_name_element.find('button', class_='course-title').text.strip() if class_name_element else 'Unknown'
                
                score_element = cls.find('span', class_='score')
                score = score_element.text.strip() if score_element else 'N/A'

                missing_assignments_element = cls.find('div', class_='class-item-lessemphasis')
                missing_assignments = 0
                if missing_assignments_element:
                    missing_assignments_text = missing_assignments_element.find_all('div')[0].text.strip()
                    missing_assignments = int(missing_assignments_text.split()[0]) if 'Missing' in missing_assignments_text else 0

                last_update_element = cls.find('span', class_='last-update')
                last_update = last_update_element.text.strip().replace('Last Update:', '').strip() if last_update_element else 'N/A'

                if class_name != 'Unknown':
                    if class_name not in grades_data:
                        grades_data[class_name] = {
                            "score": score,
                            "missing_assignments": missing_assignments,
                            "last_update": last_update
                        }
                    else:
                        existing_data = grades_data[class_name]
                        if score != 'N/A':
                            existing_data['score'] = score
                        existing_data['missing_assignments'] = max(existing_data['missing_assignments'], missing_assignments)
                        if last_update != 'N/A' and (existing_data['last_update'] == 'N/A' or last_update > existing_data['last_update']):
                            existing_data['last_update'] = last_update
                        grades_data[class_name] = existing_data

            except Exception as e:
                print(f"Error processing class item: {e}")

        message = "Here are your current grades and assignment statuses:\n"
        if grades_data:
            for cls, details in grades_data.items():
                message += (f"{cls}: Score: {details['score']}, "
                            f"Missing Assignments: {details['missing_assignments']}, "
                            f"Last Update: {details['last_update']}\n")
        else:
            message = "No grades data found."

        await ctx.send(message)

    except requests.RequestException as e:
        print(f"Request error: {e}")
        await ctx.send("Failed to fetch grades. Please try again later.")

bot.run(TOKEN)
