import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands, tasks
import os
import datetime
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('GradeBot')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
USERNAME = os.getenv('STUDENT_USERNAME')
PASSWORD = os.getenv('STUDENT_PASSWORD')

# Replace with your actual Discord channel IDs
GRADES_CHANNEL_ID = 123456789012345678  # Replace with your actual channel ID
CHANGE_CHANNEL_ID = 123456789012345678  # Replace with your actual channel ID

if not all([TOKEN, USERNAME, PASSWORD]):
    logger.error("Missing environment variables. Please check your .env file.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

def convert_to_letter_grade(percentage):
    """
    Convert a numerical percentage grade to a letter grade.
    """
    try:
        percentage = float(percentage)
    except ValueError:
        return 'N/A'
    
    if 90 <= percentage <= 100:
        return 'A'
    elif 80 <= percentage < 90:
        return 'B'
    elif 70 <= percentage < 80:
        return 'C'
    elif 60 <= percentage < 70:
        return 'D'
    elif 0 <= percentage < 60:
        return 'F'
    else:
        return 'N/A'

class StudentVueSession:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.global_cookies = None
        self.previous_grades = {} 

    def login(self):
        login_url = "https://your-school-portal.com/login"  # Replace with the actual login URL
        logger.info("Attempting to log in.")

        try:
            login_page = self.session.get(login_url)
            login_page.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch login page: {e}")
            return False

        soup = BeautifulSoup(login_page.content, 'html.parser')

        viewstate = soup.find('input', {'name': '__VIEWSTATE'})
        viewstate_gen = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
        event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})

        if not (viewstate and viewstate_gen and event_validation):
            logger.error("Missing form fields on the login page.")
            return False

        form_data = {
            "__VIEWSTATE": viewstate['value'],
            "__VIEWSTATEGENERATOR": viewstate_gen['value'],
            "__EVENTVALIDATION": event_validation['value'],
            "username": self.username,
            "password": self.password,
            "submit": "Login"
        }

        headers = {
            "User -Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }

        try:
            response = self.session.post(login_url, headers=headers, data=form_data)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Login request failed: {e}")
            return False

        if "HomePage" in response.url:  # Adjust this condition based on the actual URL after login
            logger.info("Login successful!")

            cookies = self.session.cookies.get_dict()
            self.global_cookies = cookies  # Store the cookies directly
            logger.info(f"Cookies updated: {self.global_cookies}")
            return True
        else:
            logger.error("Login failed or unexpected redirect.")
            return False

    def get_cookies(self):
        return self.global_cookies

    def is_logged_in(self):
        return self.global_cookies is not None

    def fetch_grades_page(self):
        if not self.is_logged_in():
            logger.warning("Not logged in. Attempting to log in.")
            if not self.login():
                logger.error("Login failed. Cannot fetch grades.")
                return None

        url = 'https://your-school-portal.com/grades'  # Replace with the actual grades URL
        headers = {
            'User -Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Cookie': self.global_cookies,
        }

        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            logger.error(f"Failed to fetch grades page: {e}")
            return None

    def parse_grades(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')

        grades_data = {}
        class_items = soup.find_all('div', class_='grade-item')

        logger.info(f"Class items found: {len(class_items)}")

        for cls in class_items:
            try:
                class_name_element = cls.find_previous('div', class_='class-header')
                class_name = class_name_element.find('button', class_='course-title').text.strip() if class_name_element else None

                if not class_name:
                    logger.warning("Encountered a class with no name. Skipping.")
                    continue  

                score_element = cls.find('span', class_='score')
                score = score_element.text.strip() if score_element else 'N/A'
                letter_grade = convert_to_letter_grade(score.replace('%', '')) if score != 'N/A' else 'N/A'

                missing_assignments_element = cls.find('div', class_='missing-assignments')
                missing_assignments = 0
                if missing_assignments_element:
                    missing_assignments_text = missing_assignments_element.find_all('div')[0].text.strip()
                    missing_assignments = int(missing_assignments_text.split()[0]) if 'Missing' in missing_assignments_text else 0

                last_update_element = cls.find('span', class_='last-update')
                last_update = last_update_element.text.strip().replace('Last Update:', '').strip() if last_update_element else 'N/A'

                logger.info(f"Class: {class_name}, Score: {score}, Letter Grade: {letter_grade}, Missing Assignments: {missing_assignments}, Last Update: {last_update}")

                if class_name:
                    if class_name not in grades_data:
                        grades_data[class_name] = {
                            "score": score,
                            "letter_grade": letter_grade,
                            "missing_assignments": missing_assignments,
                            "last_update": last_update
                        }
                    else:
                        existing_data = grades_data[class_name]

                        if letter_grade != 'N/A':
                            existing_data['letter_grade'] = letter_grade
                        existing_data['missing_assignments'] = max(existing_data['missing_assignments'], missing_assignments)
                        if last_update != 'N/A' and (existing_data['last_update'] == 'N/A' or last_update > existing_data['last_update']):
                            existing_data['last_update'] = last_update
                        grades_data[class_name] = existing_data

            except Exception as e:
                logger.error(f"Error processing class item: {e}")

        return grades_data

#  StudentVueSession
studentvue = StudentVueSession(USERNAME, PASSWORD)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    # Attempt to login on startup
    if studentvue.login():
        logger.info("Successfully logged in on startup.")
    else:
        logger.warning("Failed to log in on startup. Will attempt to log in when fetching grades.")
    fetch_grades.start()    
    check_grade_changes.start()  
    countdown.start()       

@bot.command()
async def grades(ctx):
    logger.info(f"Grades command invoked by {ctx.author}")
    html_content = studentvue.fetch_grades_page()

    if not html_content:
        # Attempt to re-login!
        logger.info("Attempting to re-login and retry fetching grades.")
        if studentvue.login():
            html_content = studentvue.fetch_grades_page()
            if not html_content:
                await ctx.send("Failed to fetch grades after re-authentication.")
                return
        else:
            await ctx.send("Failed to authenticate. Please try again later.")
            return

    grades_data = studentvue.parse_grades(html_content)

    message = "📚 **Here are your current grades and assignment statuses:**\n"
    if grades_data:
        for cls, details in grades_data.items():
            message += (f"**{cls}**: Score: {details['score']}, Grade: {details['letter_grade']}, "
                        f"Missing Assignments: {details['missing_assignments']}, "
                        f"Last Update: {details['last_update']}\n")
    else:
        message = "No grades data found."

    await ctx.send(message)

@bot.command()
async def check(ctx):
    logger.info(f"Check command invoked by {ctx.author}")
    if studentvue.login():
        await ctx.send("Cookies have been updated successfully.")
    else:
        await ctx.send("Failed to update cookies. Please check your credentials.")

@bot.command()
async def time(ctx):
    """Shows time remaining until next grade updates"""
    logger.info(f"Time command invoked by {ctx.author}")
    
    now = datetime.now(timezone.utc)
    next_regular_update = fetch_grades.next_iteration
    next_change_check = check_grade_changes.next_iteration
    
    message = "⏰ **Update Schedule **\n"
    
    # Check time
    if next_regular_update:
        time_to_regular = next_regular_update - now
        regular_hours, remainder = divmod(int(time_to_regular.total_seconds()), 3600)
        regular_minutes, regular_seconds = divmod(remainder, 60)
        message += f"📚 Next full grade update in: **{regular_hours}h {regular_minutes}m {regular_seconds}s**\n"
    else:
        message += "📚 Regular grade update schedule not available\n"
    
    # Check time 
    if next_change_check:
        time_to_check = next_change_check - now
        check_hours, remainder = divmod(int(time_to_check.total_seconds()), 3600)
        check_minutes, check_seconds = divmod(remainder, 60)
        message += f"🔍 Next grade change check in: **{check_minutes}m {check_seconds}s**"
    else:
        message += "🔍 Grade change check schedule not available"
    
    await ctx.send(message)

@tasks.loop(hours=12)
async def fetch_grades():
    channel = bot.get_channel(GRADES_CHANNEL_ID)  
    if channel:
        logger.info("Starting scheduled grades fetch.")
        html_content = studentvue.fetch_grades_page()

        if not html_content:
            # Attempt to re-login
            logger.info("Scheduled fetch: Attempting to re-login and retry fetching grades.")
            if studentvue.login():
                html_content = studentvue.fetch_grades_page()
                if not html_content:
                    logger.error("Scheduled fetch: Failed to fetch grades after re-authentication.")
                    return
            else:
                logger.error("Scheduled fetch: Failed to authenticate.")
                return

        grades_data = studentvue.parse_grades(html_content)

        message = "📚 **Current Grades and Assignment Statuses:**\n"
        if grades_data:
            for cls, details in grades_data.items():
                message += (f"**{cls}**: Score: {details['score']}, Grade: {details['letter_grade']}, "
                            f"Missing Assignments: {details['missing_assignments']}, "
                            f"Last Update: {details['last_update']}\n")
        else:
            message = "No grades data found."

        await channel.send(message)
        logger.info("Scheduled grades fetch completed successfully.")
    else:
        logger.error("Scheduled fetch: Grades channel not found.")

@tasks.loop(hours=1)
async def check_grade_changes():
    """
    Task to check for any grade changes every hour and post updates.
    Tracks both percentage and letter grade changes.
    """
    channel = bot.get_channel(CHANGE_CHANNEL_ID)  
    if not channel:
        logger.error("Change channel not found.")
        return

    logger.info("Starting hourly grade change check.")
    html_content = studentvue.fetch_grades_page()

    if not html_content:
        
        logger.info("Hourly check: Attempting to re-login and retry fetching grades.")
        if studentvue.login():
            html_content = studentvue.fetch_grades_page()
            if not html_content:
                logger.error("Hourly check: Failed to fetch grades after re-authentication.")
                return
        else:
            logger.error("Hourly check: Failed to authenticate.")
            return

    current_grades = studentvue.parse_grades(html_content)
    previous_grades = studentvue.previous_grades

    changes = []

    for cls, details in current_grades.items():
        prev_details = previous_grades.get(cls)
        if prev_details:
            
            current_score = float(details['score'].replace('%', '')) if details['score'] != 'N/A' else None
            prev_score = float(prev_details['score'].replace('%', '')) if prev_details.get('score') != 'N/A' else None
            
            
            if current_score is not None and prev_score is not None:
                score_changed = abs(current_score - prev_score) >= 0.1  
                letter_changed = details['letter_grade'] != prev_details.get('letter_grade')
                
                if score_changed or letter_changed:
                    score_diff = round(current_score - prev_score, 2) if score_changed else 0
                    changes.append({
                        'class': cls,
                        'old_score': f"{prev_score}%",
                        'new_score': f"{current_score}%",
                        'score_diff': score_diff,
                        'old_letter': prev_details.get('letter_grade'),
                        'new_letter': details['letter_grade']
                    })
        else:
            #
            current_score = details['score'] if details['score'] != 'N/A' else 'N/A'
            changes.append({
                'class': cls,
                'old_score': 'N/A',
                'new_score': current_score,
                'score_diff': None,
                'old_letter': 'N/A',
                'new_letter': details['letter_grade']
            })

    
    for cls in previous_grades:
        if cls not in current_grades:
            changes.append({
                'class': cls,
                'old_score': previous_grades[cls].get('score', 'N/A'),
                'new_score': 'Removed',
                'score_diff': None,
                'old_letter': previous_gr ades[cls].get('letter_grade', 'N/A'),
                'new_letter': 'Removed'
            })

    if changes:
        message = "🔔 **Grade Updates Detected:**\n"
        for change in changes:
            if change['score_diff'] is not None:
                direction = "📈" if change['score_diff'] > 0 else "📉"
                message += (
                    f"**{change['class']}**:\n"
                    f"- Grade: {change['old_score']} → {change['new_score']} "
                    f"({direction} {'+' if change['score_diff'] > 0 else ''}{change['score_diff']}%)\n"
                    f"- Letter Grade: {change['old_letter']} → {change['new_letter']}\n"
                )
            else:
                message += (
                    f"**{change['class']}**:\n"
                    f"- Grade: {change['old_score']} → {change['new_score']}\n"
                    f"- Letter Grade: {change['old_letter']} → {change['new_letter']}\n"
                )
        await channel.send(message)
        logger.info(f"Posted grade changes: {changes}")
    else:
        logger.info("No grade changes detected.")

    # Update previous_grades with current_grades
    studentvue.previous_grades = current_grades

@tasks.loop(hours=1)
async def countdown():
    try:
        now = datetime.now(timezone.utc)  
        next_run = fetch_grades.next_iteration
        if next_run:
            time_remaining = next_run - now

            if time_remaining.total_seconds() > 0:
                hours, remainder = divmod(int(time_remaining.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                logger.info(f"Time until next regular fetch: {hours} hours, {minutes} minutes, {seconds} seconds")
            else:
                logger.info("The scheduled fetch time has already passed.")
        else:
            logger.info("Next fetch time not set.")
    except Exception as e:
        logger.error(f"An error occurred in the countdown task: {e}")

# Ensure that the background tasks start after the bot is ready
@fetch_grades.before_loop
async def before_fetch_grades():
    await bot.wait_until_ready()

@check_grade_changes.before_loop
async def before_check_grade_changes():
    await bot.wait_until_ready()

@countdown.before_loop
async def before_countdown():
    await bot.wait_until_ready()

bot.run(TOKEN)
