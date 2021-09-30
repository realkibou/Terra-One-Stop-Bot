#!/usr/bin/python3

import os

# SETUP
NETWORK = 'TESTNET'
mnemonic = os.environ.get('MNEMONIC', '')

# Read me: When to claim, sell, unstake? - What is the right min_total_value?
# That depends on what you want to do with that free UST. Lets say you want to hold that profit on Anchor Earn:
# If you plan to sell and then deposit the gained UST for at least 1 month, I will gain (19.45% APY) 1.47%.
# If the transaction fees are 2 UST, the break-even amount to sell/deposit would be (2 / 1.47% =) 136 UST.
# If you would hold it for 2 month 2.96%, hence (2 / 2.96% =) 67 UST.

# CLAIM & SELL MIR, SPEC. ANC REWARDS
# min_price AND min_total_value must both be fulfilled for your token to be sold.
MIR_claim_and_sell_token = False
MIR_min_price = 4  # Min price acceptable to sell in UST
# Min amount (qty * price in UST) to sell MIR tokens.
MIR_min_total_value = 136

SPEC_claim_and_sell_token = False
SPEC_min_price = 6
SPEC_min_total_value = 136

ANC_claim_and_sell_token = False
ANC_min_price = 2
ANC_min_total_value = 136

# MIRROR: CLAIMING UNLOCKED UST
Mirror_claim_unlocked_UST = False
Mirror_min_amount_UST_to_claim = 136

# ANCHOR BORROW: MAINTAIN LTV RATIO / REPAY BORROWED UST IF REQUIRED
# READ the example carefully, as Anchor works opposite for Mirror's liquidation ratio's logic.
# Example:  Lets say the you would get liquidated at 60% or 0.6 LTV (borrowed_amount / deposited collateral)
#           The script will trigger a repay when 0.6 + lower_distance (by default: 0.6 + -0.1 = 0.5 = 50%) is reached.
#           It will repay debt to get back to 0.6 + target_distance (by default: 0.6 + -0.15 = 0.45 = 45%).
Anchor_enable_auto_repay_of_debt = False
# Allow the script to withdraw deposited UST on Anchor Earn to repay the debt
Anchor_enable_withdraw_of_deposited_UST = False
# If you even after a withdrawl of deposited UST, you dont have enough UST, you can perform a partial repayment
Anchor_enable_partially_repay_if_not_enough_UST_in_wallet = False
Anchor_lower_distance = -0.1
Anchor_target_distance = -0.15
# Even if a repay is required to restor the required target_distance, it will not be excetuted if the min_deposit is undershot
Anchor_min_repay_limit = 10

# ANCHOR: BORROW MORE UST FOR YOUR DEPOSITED COLATERAL
# If you want, you can tell the script to borrow more from Anchor if your set upper_distance allows it.
Anchor_enable_auto_borrow_UST = False
Anchor_upper_distance = -0.2  # Upper distance above that a withdraw will be executed
#           If the collateral ratio is bigger than 0.6 + upper_distance (by default: 0.6 + -0.2 = 0.40 = 40%) it will withdrawl collateral.
#           It will borrow more UST to get back to 0.6 + target_distance (by default: 0.6 + -0.15 = 0.45 = 45%).
# Cooldown in days after collateral has been withdrawn. Example: 3 means it happens only once every 3 days.
Anchor_borrow_cooldown = 3
# Set a minimum limit, otherwise the script may borrow continuously
Anchor_min_borrow_limit = 136

# ANCHOR EARN: DEPOSIT UST FROM SELLING ANC, MIR, SPEC
Anchor_enable_deposit_borrowed_UST = False
Anchor_min_deposit_amount = 136

# MIRROR: MAINTAIN COLLATERAL RATIO / DEPOSIT COLATERAL IF REQUIRED
# Example:  Lets say the minimum ratio for the given mAsset on Mirror is 150% or 1.5.
#           The script will trigger a collateral deposit when 1.5 + lower_distance (by default: 1.5 + 0.1 = 1.6 = 160%) is reached.
#           It will deposit enough collateral to get back to 1.5 + target_distance (by default: 1.5 + 0.2 = 1.7 = 170%).
Mirror_enable_deposit_collateral = False
Mirror_lower_distance = 0.1
Mirror_target_distance = 0.2
# Even if a deposit is required to restor the required target_distance, it will not be excetuted if the min_deposit is undershot
Mirror_min_deposit_limit = 10

# MIRROR: WITHDRAWL OF COLATERAL
# If you want, you can tell the script to withdraw collateral if your set upper_distance allows it.
Mirror_enable_withdraw_collateral = False
Mirror_upper_distance = 0.3  # Upper distance above that a withdraw will be executed
#           If the collateral ratio is bigger than 1.5 + upper_distance (by default: 1.5 + 0.3 = 1.8 = 180%) it will withdrawl collateral.
#           It will deposit enough collateral to get back to 1.5 + target_distance (by default: 1.5 + 0.2 = 1.7 = 170%).
# Cooldown in days after collateral has been withdrawn. Example: 3 means it happens only once every 3 days. 0 means it will happen always.
Mirror_withdraw_cooldown = 3

# LOGGING
# If False, default.log will include almost everything. If False only WARNINGs and ERRORs will be logged.
Debug_mode = True
# To avoid notification spam, ALL NOTIFICATIONS will be disabled in debug mode
Logging_detail = 'simple'  # detailed, moderate, simple. Recommended: simple
# Logs summary of what has happend, if something has happend send as by NOTIFICATIONS below defined.
Send_me_a_report = False
# Also, always includes WARNINGS about failed transactions or insufficent walelt balance. #
# Recommended: False

# NOTIFICATIONS
Notify_slack = False
Notify_Telegram = False
Notify_Email = False
Email_subject = 'Report Terra One-Stop-Bot'
Email_address = 'you@this.com'

# GENERAL
# How much UST shall remain in your wallet, even after the deposit of your UST to Anchor Earn
safety_multiple_on_transaction_fees = 3

# NOTIFICATION SETUP
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'Your bots token here')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', 'Your chat ID here,')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', 'Your webhook here')