import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands, tasks
import os
import datetime
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('GradeBot')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
USERNAME = os.getenv('STUDENT_USERNAME')
PASSWORD = os.getenv('STUDENT_PASSWORD')

# Replace with your actual Discord channel IDs
GRADES_CHANNEL_ID = CHANNEL_ID( put yours)  # Channel for regular 12-hour updates
CHANGE_CHANNEL_ID = CHANNEL_ID( put yours)    # Channel for hourly change updates

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
        self.previous_grades = {}  # Initialize previous grades

    def login(self):
        login_url = "https://studentvue.phoenixunion.org/PXP2_Login_Student.aspx?regenerateSessionId=true"
        logger.info("Attempting to log in to StudentVue.")

        try:
            # Fetch the login page to retrieve dynamic form fields
            login_page = self.session.get(login_url)
            login_page.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch login page: {e}")
            return False

        soup = BeautifulSoup(login_page.content, 'html.parser')

        # Extract necessary form fields
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})
        viewstate_gen = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
        event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})

        if not (viewstate and viewstate_gen and event_validation):
            logger.error("Missing form fields on the login page.")
            return False

        # Prepare form data
        form_data = {
            "__VIEWSTATE": viewstate['value'],
            "__VIEWSTATEGENERATOR": viewstate_gen['value'],
            "__EVENTVALIDATION": event_validation['value'],
            "ctl00$MainContent$username": self.username,
            "ctl00$MainContent$password": self.password,
            "ctl00$MainContent$Submit1": "Login"
        }

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "studentvue.phoenixunion.org",
            "Origin": "https://studentvue.phoenixunion.org",
            "Referer": login_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Upgrade-Insecure-Requests": "1",
            "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }

        # Send the login request
        try:
            response = self.session.post(login_url, headers=headers, data=form_data)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Login request failed: {e}")
            return False

        if "Home_PXP2.aspx" in response.url:
            logger.info("Login successful!")

            # Extract specific cookies
            cookies = self.session.cookies.get_dict()
            asp_net_session_id = cookies.get("ASP.NET_SessionId")
            lm_synergy = cookies.get("LM_Synergy")

            if asp_net_session_id and lm_synergy:
                self.global_cookies = f"PVUE=00; ASP.NET_SessionId={asp_net_session_id}; LM_Synergy={lm_synergy}"
                logger.info(f"Cookies updated: {self.global_cookies}")
                return True
            else:
                logger.error("Required cookies not found after login.")
                return False
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

        url = 'https://studentvue.phoenixunion.org/PXP2_Gradebook.aspx?AGU=0&studentGU=50A22448-6B17-437F-AE42-662260A94136'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Cookie': self.global_cookies,
            'Host': 'studentvue.phoenixunion.org',
            'Referer': 'https://studentvue.phoenixunion.org/PXP2_Assessment.aspx?AGU=0&StudentAssessment=1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

        try:
            response = self.session.get(url, headers=headers)
            if response.status_code == 500:
                logger.error("Received 500 Internal Server Error from StudentVue.")
                return None
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            logger.error(f"Failed to fetch grades page: {e}")
            return None

    def parse_grades(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')

        grades_data = {}
        class_items = soup.find_all('div', class_='gb-class-row')

        logger.info(f"Class items found: {len(class_items)}")

        for cls in class_items:
            try:
                class_name_element = cls.find_previous('div', class_='gb-class-header')
                class_name = class_name_element.find('button', class_='course-title').text.strip() if class_name_element else None

                if not class_name:
                    logger.warning("Encountered a class with no name. Skipping.")
                    continue  # Skip classes without a valid name

                score_element = cls.find('span', class_='score')
                score = score_element.text.strip() if score_element else 'N/A'
                letter_grade = convert_to_letter_grade(score.replace('%', '')) if score != 'N/A' else 'N/A'

                missing_assignments_element = cls.find('div', class_='class-item-lessemphasis')
                missing_assignments = 0
                if missing_assignments_element:
                    missing_assignments_text = missing_assignments_element.find_all('div')[0].text.strip()
                    missing_assignments = int(missing_assignments_text.split()[0]) if 'Missing' in missing_assignments_text else 0

                last_update_element = cls.find('span', class_='last-update')
                last_update = last_update_element.text.strip().replace('Last Update:', '').strip() if last_update_element else 'N/A'

                logger.info(f"Class: {class_name}, Score: {score}, Letter Grade: {letter_grade}, Missing Assignments: {missing_assignments}, Last Update: {last_update}")

                # Update grades_data only if class_name is valid
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

# Initialize StudentVueSession
studentvue = StudentVueSession(USERNAME, PASSWORD)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    # Attempt to login on startup
    if studentvue.login():
        logger.info("Successfully logged in on startup.")
    else:
        logger.warning("Failed to log in on startup. Will attempt to log in when fetching grades.")
    fetch_grades.start()    # Start the task to fetch grades every 12 hours
    check_grade_changes.start()  # Start the task to check grade changes every hour
    countdown.start()       # Start the countdown task

@bot.command()
async def grades(ctx):
    logger.info(f"Grades command invoked by {ctx.author}")
    html_content = studentvue.fetch_grades_page()

    if not html_content:
        # Attempt to re-login and retry once
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
            message += (f"**{cls}**: Grade: {details['letter_grade']}, "
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

@tasks.loop(hours=12)
async def fetch_grades():
    channel = bot.get_channel(GRADES_CHANNEL_ID)  # Channel for regular updates
    if channel:
        logger.info("Starting scheduled grades fetch.")
        html_content = studentvue.fetch_grades_page()

        if not html_content:
            # Attempt to re-login and retry once
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
                message += (f"**{cls}**: Grade: {details['letter_grade']}, "
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
    """
    channel = bot.get_channel(CHANGE_CHANNEL_ID)  # Channel for change updates
    if not channel:
        logger.error("Change channel not found.")
        return

    logger.info("Starting hourly grade change check.")
    html_content = studentvue.fetch_grades_page()

    if not html_content:
        # Attempt to re-login and retry once
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
            # Compare letter grades
            if details['letter_grade'] != prev_details.get('letter_grade'):
                changes.append((cls, prev_details.get('letter_grade'), details['letter_grade']))
        else:
            # New class added
            changes.append((cls, 'N/A', details['letter_grade']))

    # Check for removed classes
    for cls in previous_grades:
        if cls not in current_grades:
            changes.append((cls, previous_grades[cls].get('letter_grade'), 'Removed'))

    if changes:
        message = "🔔 **Grade Updates Detected:**\n"
        for cls, old_grade, new_grade in changes:
            message += f"**{cls}**: Grade changed from **{old_grade}** to **{new_grade}**\n"
        await channel.send(message)
        logger.info(f"Posted grade changes: {changes}")
    else:
        logger.info("No grade changes detected.")

    # Update previous_grades with current_grades
    studentvue.previous_grades = current_grades

@tasks.loop(hours=1)
async def countdown():
    try:
        now = datetime.now(timezone.utc)  # Timezone-aware datetime in UTC
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
