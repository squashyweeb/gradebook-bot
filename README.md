# gradebook-bot

`gradebook-bot` is a Discord bot that fetches and displays your current grades and assignment statuses from studentvue grade portal. It utilizes web scraping to gather the necessary data and sends it to a designated Discord channel.

## Features
- Fetches grades and assignment statuses from the studentvue portal.
- Displays scores, missing assignments, and the last update date.
- Sends formatted grade information to a Discord channel.

## Prerequisites
- Python 3.8 or higher
- `requests` library
- `beautifulsoup4` library
- `discord.py` library
- `python-dotenv` library

## Installation
1. Clone the repository: `git clone https://github.com/squashyweeb/gradebook-bot.git && cd gradebook-bot`
2. Install the required libraries: `pip install requests beautifulsoup4 discord.py python-dotenv`
3. Create a `.env` file in the root directory of the project with the following content: `DISCORD_TOKEN=your_discord_bot_token`
4. Get your data from `PXP2_Gradebook`.

## Usage
1. Run the bot: `python gradebook_bot.py`
2. In your Discord server, use the `/grades` command to fetch and display your grades.

## Code Explanation
- **`requests`**: Used to send HTTP requests to the grade portal.
- **`BeautifulSoup`**: Parses and extracts data from the HTML response.
- **`discord.py`**: Handles interactions with the Discord API.
- **`.env`**: Stores sensitive information like the Discord bot token.

## Notes
- Ensure that the `DISCORD_TOKEN` in the `.env` file is kept confidential.
- Update the URL and any necessary headers in the `grades` command if there are changes to the grade portal's structure.

## License
This project is licensed under the MIT License.
