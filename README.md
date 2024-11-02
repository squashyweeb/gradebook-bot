# GradeBot

`GradeBot` is a Discord bot that fetches and displays your current grades and assignment statuses from a grade portal. It utilizes web scraping to gather the necessary data and sends it to a designated Discord channel.

## Features

- Fetches grades and assignment statuses from the grade portal.
- Displays scores, missing assignments, and the last update date.
- Sends formatted grade information to a Discord channel.

## Prerequisites

- Python 3.8 or higher
- `requests` library
- `beautifulsoup4` library
- `discord.py` library
- `python-dotenv` library

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/squashyweeb/gradebook-bot.git && cd gradebook-bot
   ```

2. Install the required libraries:
   ```bash
   pip install requests beautifulsoup4 discord.py python-dotenv
   ```

3. Create a `.env` file in the root directory of the project with the following content:
   ```plaintext
   DISCORD_TOKEN=your_discord_bot_token
   ```

## Usage

1. Run the bot:
   ```bash
   python gradebook_bot.py
   ```

2. In your Discord server, use the `/check` command to fetch your new cookie in case of failure.

3. In your Discord server, use the `/grades` command to fetch and display your grades.

## Code Explanation

- **`requests`**: Used to send HTTP requests to the grade portal.
- **`BeautifulSoup`**: Parses and extracts data from the HTML response.
- **`discord.py`**: Handles interactions with the Discord API.
- **`.env`**: Stores sensitive information like the Discord bot token.

## Notes

- Ensure that the `DISCORD_TOKEN` in the `.env` file is kept confidential.
- Update the URL and any necessary headers in the `grades` command if there are changes to the grade portal's structure.

## Need Help?

If you need help or encounter any issues, please create an issue ticket at [this link](https://github.com/squashyweeb/gradebook-bot/issues).

## License

This project is licensed under the MIT License.
