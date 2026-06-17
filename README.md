# telegram-shop
A Telegram bot for selling digital goods: VPN, AI subscriptions (ChatGPT, Gemini, Claude, Grok), CS2 Prime, Telegram Stars/Premium, and manuals. Supports Telegram payments and manual confirmation. Admin panel: adding products, keys, and order fulfillment. Configuration via BOT_TOKEN, ADMIN_IDS, and PROVIDER_TOKEN. Data in JSON


Telegram Shop Bot

A Telegram bot for automated sales of digital products: VPN keys, AI subscriptions, Telegram Stars/Premium, CS2 Prime, and manuals. Supports manual and automatic payments (Telegram Payments), administration, and error logging.
Key Features

🛒 Product catalog by category with availability display.

👤 User profile with a history of the last 10 orders.

📊 Statistics for the administrator (number of orders, revenue, issued).

💳 Flexible payment: automatic via Telegram Payments (for Stars and Premium) or manual confirmation with the "Paid" button.

📨 Product delivery: automatic (for Stars) or manual by the administrator (keys, manuals, Premium).

🛠 Admin commands for managing orders, products, secrets, and manuals.

📄 Privacy Policy and Terms of Service (embedded text).

🐛 SQLite error logging and the /errors command for administrators.

🔗 Technical support button — a link to a specified Telegram contact (configured with one variable).

Installation and Configuration
Requirements

Python 3.9+

Telegram Bot Token (obtain from @BotFather)

(Optional) Provider Token for accepting regular payments (not Stars) — also issued by @BotFather.

Step 1. Getting the Code

Clone the repository or create a bot.py file with the code from this project. Step 2. Installing Dependencies

Create a virtual environment and install the package:
bash

python -m venv venv
source venv/bin/activate # Linux/macOS
# or venv\Scripts\activate for Windows

pip install aiogram

If you want to use python-dotenv to load .env (instead of manually parsing it), install it additionally. This is not necessary, as the code already reads .env directly.

Note: The requirements.txt file, if present in the project, should only contain lines for packages, for example:
text

aiogram>=3.0.0

(no need to list imports).

Step 3. Create a .env file

In the project's root folder, create a .env file with the following contents:
env

BOT_TOKEN=your_bot_token
ADMIN_IDS=123456789,987654321
PROVIDER_TOKEN=

BOT_TOKEN — Required.

ADMIN_IDS — A comma-separated list of numeric Telegram administrator IDs (no spaces). Required.

PROVIDER_TOKEN — Optional. To accept regular payments (USD, EUR), specify the token from @BotFather. For Telegram Stars, leave blank (or comment it out).

Step 4. Setting up a support contact

In the bot.py file, find the line:
python

HELP_USERNAME = "@helpingonuser"

Replace @helpingonuser with the actual username of your support team (with the @ symbol). This variable is used in the "🆘 Help" button in the main menu—it will take the user to a private chat with the specified user.
Step 5. Launching the bot
bash

python bot.py

The following will be automatically created upon first launch:

A shop.db database with the orders and error_logs tables.

A shop_data.json file with demo products (if it doesn't exist).

The bot is now ready to use.
Usage
User Interface

/start or /help — welcome screen and main menu.

The main menu consists of the following buttons:

📦 Products — a list of categories.

👤 Profile — your recent orders.

📊 Statistics — general store statistics (available to everyone).

📄 Privacy Policy — policy text.

📜 Terms and Conditions — terms and conditions text.

🆘 Help — direct link to technical support (username is specified in the code).

Purchase Process

Select a category, then a product.

On the product page, click ✅ Buy.

Confirm the purchase.

Next steps depend on the product type:
🔹 For stars and premium products

The bot will ask you to enter the recipient's username (e.g., @ivan). Please check the username carefully — refunds are not issued if the username is incorrect.

After entering the username, an invoice will be sent via Telegram Payments.

For stars products, the bot will immediately notify you of the stars awarded after successful payment.

If the product is premium, the order status changes to paid after payment, and the administrator must manually issue the key using the /deliver command.

🔸 For secret and manual products

After the purchase is confirmed, an order is created with a pending status.

The bot provides payment instructions (manual method: card, cryptocurrency, etc.) and displays the "Paid" button.

You pay using an external payment method and click the button.

The order status changes to paid, and the administrator receives a notification.

The administrator issues the product using /deliver (the key or manual is sent to you in chat).

Administrative Commands

All commands are available only to users whose IDs are listed in ADMIN_IDS.
Command Description
/orders Show the last 20 orders (all users).
/errors Show the last 20 errors from the log. Add "full" after the command to see the full stack trace.
/deliver <order_id> Issue the product for the order. For products with secrets, the first key from the secrets array is taken and sent to the user.
/addproduct <category> <item_key> <type> <price> <currency> <title> Add a new product. Example: /addproduct vpn vpn_fr secret 5 USD "VPN — France".
/addsecret <category> <item_key> <secret> Add one secret (key) to an existing product.
/addmanuals <category> <item_key> <manual1;manual2;...> Add manual names (for manual products).
/ping Functionality check — pong will respond.
Data Structure
Shop_data.json File

Stores all products by category. Each product has the following fields:

title — name,

price — price (number),

currency — currency (USD, EUR, XTR, etc.),

type — type: secret, manual, stars, premium,

secrets — array of keys (for secret, manual, premium types),

manuals — array of manual names (manual only),

stars — number of stars (stars only).

Shop.db Database

Orders Table — all orders with the following fields: id, user_id, username, cat, item, price, currency, type, status, target_username, secret, created_at, updated_at.

The error_logs table contains error logs: id, created_at, level, message, and traceback.

Implementation Features

Loading environment variables from .env is done manually (without the python-dotenv library), but it can be added if desired.

FSM (Finite State Machine) is used for step-by-step username input.

For the XTR (Telegram Stars) currency, the amount is calculated correctly (an integer number of stars is passed, not a multiplier by 100).

The "Paid" button is protected from repeated clicks (order status check).

Error logs are written simultaneously to the console and to the database.

Potential Issues and Solutions
❌ PAYMENT_PROVIDER_INVALID Error

Check that PROVIDER_TOKEN is specified correctly in .env.

For products with currency = "XTR" (Stars), the token must be an empty string.

For regular currencies, get a new token from @BotFather and paste it into .env.

❌ The bot doesn't see variables from .env

Make sure the .env file is in the same folder as bot.py.

Check that the file doesn't contain any extra spaces, quotes, or comments (except for # at the beginning of a line). The format is strictly KEY=value.

❌ I don't receive a delivery notification

The user must have previously sent /start to the bot, otherwise the bot won't be able to message them.

If an error occurs during sending, it will be logged in the error log, which can be viewed via /errors.

Technical Support Setup

Setting up the support contact is as simple as changing one line of code:
python

HELP_USERNAME = "@helpingonuser" # replace with the desired username

This variable is used in the "🆘 Help" button in the main menu, as well as in the welcome message. After changing the variable, the bot will automatically use the new contact.

Author: macros

To contact the developer: Telegram - @imnotyou3
