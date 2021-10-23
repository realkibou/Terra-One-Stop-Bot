## Summary
Tired of non-stop worrying whether you will get liquidated when the market moves? You want to get the maximum out of your Degen Delta Neutral Strategy on Mirror? You want to minimize the risk of your rewards token (SPEC, MIR) losing in value, and rather want to sell them? You want to maintain a healthy LTV on your Anchor Borrow and deposit the borrowed UST into Anchor Earn? Not sure to claim and sell your token rewards?

Then, this bot is for you!

Automatically manage all your ANC, MIR, SPEC token rewards, Mirror Delta Neutral Short Positions, UST claims after lockup, Anchor Borrow and Earn for Terra, deposits and withdraws from liquidity pools to sell.

## Thank you!
If this bot is helpful to you and helps maximize your gainz, feel free to donate a bit to `terra1xl0ww4tykjmm4vnzck0qz5luu6rxl97wuwmgfg`. This will also keep the development going and the bot up-to-date. Thank you! :)

*Special thanks to unl1k3ly as his bot taught me what I needed to know. Thanks Terra, Mirror, Spectrum, Anchor team and the Terra Community!*

## How to pick the right mAsset for your strategy!?
I found there are many calculations out there. But most are just wrong. They do not consider volatility or the most important factor hodl time.

So I made 2x overly detailed calculation that I base my decisions on. I consider this valuable for you, even if you do not run the Terra-One-Stop-Bot.

Delta Neutral Simulation & Playground: https://docs.google.com/spreadsheets/d/19WyuPtGz1SGJsCKZGskD7JAGAT9THUFy9b2GtbMR7JI 
- '3. Conclusion' shows you which mAssets current would return what APY. You can change what top mAssets you want to consider. The sheet calculates those rankings once per hour new.
- If you want to play a little bit around look at the sheet '0. Calc', and change the yellow filled cells.
- The amount you want to put in is not relevant, as all is calculated based on a percentage basis, as transaction costs are not considered.

Decision Help Min Values: https://docs.google.com/spreadsheets/d/1U9jd5rarvWwbeuGLzkuG7Hyx4B71Pkdrmoj894SGr3M
- Gives you a basis to make your decision what minimum deposits, withdraws, sell quantities, etc. to set for the Terra-One-Stop-Bot.

## What this One-Stop-Bot does
1. Withdraws your MIR, SPEC, ANC from your LP tokens
2. Claims your unclaimed MIR, SPEC, ANC tokens
3. Claims unlocked UST on Mirror
4. Sells your MIR, SPEC, ANC tokens
5. Deposits your MIR, SPEC, ANC tokens into corresponding LP
6. Repays debt at Anchor if your LTV requires it
7. Borrows more UST from Anchor if you LTV allows it
8. Deposits UST (from sale of MIR, SPEC, ANC and Borrow) in Anchor Earn to get more aUST
9. Deposits collateral in your short positions
10. Withdraws collateral from your short positions
11. Sends you an update via Slack, Telegram or Email
12. Runs at your defined intervals
13. Runs in debug mode
14. Logs information for you
15. Other stuff

*Due to the order of which the functions are executed, the priority is on a repayment of debt to Anchor rather than depositing more aUST into your shorts on Mirror, as crypto is more volatile than the legacy stock market.*

## What can be configured
I made the One-Stop-Bot as much configureable as possible. You can configure what you like in the `B_config.py`. This order here is also the logical flow of the bot.
0. Setup
    * `XXX_min_price` Define a minimum prices for SPEC, MIR, ANC to trigger a sale
    * `XXX_min_total_value` Define a minimum value (= price of token * amount to sell) for SPEC, MIR, ANC to be acted on (sale or deposit)
1. Withdraws your MIR, SPEC, ANC from your LP tokens
    * `XXX_withdraw_and_sell_if_min_price_is_reached` True/False withdraw of your token and UST from LP to sell if **BOTH** `XXX_min_price` **AND** `XXX_min_total_value` is exceeded
2. Claims your unclaimed MIR, SPEC, ANC tokens
    * `XXX_claim_and_sell_token` True/False sale of SPEC, MIR, ANC (SPEC gets claimed from all your farms Mirror, Anchor, Pylon and Spectrum) if **BOTH** `XXX_min_price` **AND** `XXX_min_total_value` is exceeded
    * `XXX_claim_and_deposit_in_LP`True/False deposit of SPEC, MIR, ANC to the corresponding LP if **ONLY** `XXX_min_total_value` is exceeded
3. Claims unlocked UST on Mirror
	* `Mirror_claim_unlocked_UST` True/False claim of unlocked UST
	* `Mirror_min_amount_UST_to_claim` Define a minimum of unlocked UST to be claimed
4. Sells your MIR, SPEC, ANC tokens
    * For each token there can be only a sell or deposit allowed.
5. Deposits your MIR, SPEC, ANC tokens into corresponding LP
    * For each token there can be only a sell or deposit allowed.
6. Repays debt at Anchor if your LTV requires it
    * `Anchor_enable_auto_repay_of_debt` True/False auto repayment of debt
    * `Anchor_enable_withdraw_of_deposited_UST` True/False allowance to withdraw UST from Anchor Earn to repay debt
    * `Anchor_enable_partially_repay_if_not_enough_UST_in_wallet` True/False of partial debt repayment (withdraw all deposited UST on Anchor Earn + all UST available in wallet)
    * `Anchor_lower_distance` Define lower_distance from maximal ltv ratio below a repayment will be executed
    * `Anchor_target_distance`Define target_distance from maximal ltv ratio that is restored when repay debt/borrow more UST
    * `Anchor_min_repay_limit` Define minimum debt repayment limit
7. Borrows more UST from Anchor if you LTV allows it
    * `Anchor_enable_auto_borrow_UST` True/False auto borrow of more UST
    * `Anchor_upper_distance`Define upper_distance from maximal ltv ratio above more UST will be borrowed
    * `Anchor_min_borrow_limit` Define minimum borrow limit
    * `Anchor_borrow_cooldown` Define cooldown period in days for the auto borrow function
8. Deposits UST (from sale of MIR, SPEC, ANC and Borrow) in Anchor Earn to get more aUST
    * `Anchor_Earn_enable_deposit_UST` True/False enable deposit of freshly gained UST (from the sale of SPEC, MIR & Mirror claim) into Anchor Earn
    * `Anchor_Earn_min_deposit_amount` Define minimum UST amount to deposit
    * `Anchor_Earn_min_balance_to_keep_in_wallet` This this bot also deposits token in LP, you should have a UST balance in your wallet. 
9. Deposits collateral in your short positions
    * `Mirror_enable_deposit_collateral` True/False deposit of collateral (Luna, UST, aUST supported)
    * `Mirror_lower_distance` Define lower_distance from minimal ratio below collateral will be deposited
    * `Mirror_target_distance` Define target_distance from minimal ratio that is restored when depoit/withdraw collateral
    * `Mirror_min_deposit_limit_in_UST` Define minimum deposit limit in UST
10. Withdraws collateral from your short positions
    * `Mirror_enable_withdraw_collateral` True/False withdraw of collateral
    * `Mirror_upper_distance` Define upper_distance from minimal ratio above collateral will be withdrawn
    * `Mirror_min_withdraw_limit_in_UST` Define minimum withdraw limit in UST
    * `Mirror_withdraw_cooldown` Define cooldown period in days for the auto withdraw function
11. Sends you a report on Telegram, Slack and/or Email if something has been done. Also writes logs into ./logs and sends you a status update if you want.
    * `Send_me_a_report` True/False prepares a summary of what has happened, if something has happened. Always includes WARNINGs and ERRORs.
    * `Notify_Slack` True/False notifications to be received on Slack
    * `Notify_Telegram` True/False notifications to be received on Telegram
    * `Notify_Gmail` True/False notifications to be send through Gmail to any email
    * `Email_format` Define to receive the report and status update in TEXT or HTML
    * `Send_me_a_status_update` True/False if you want to receive a status update anyway depending on your `Status_update_frequency` 
    * `Status_update_frequency` Define in what intervals (hours) you want to receive a status update
    * `Status_update_time` Define at what time you want to receive the status update
12. Runs the bot at your defined intervals
    * `Run_interval_for_Scheduler` Define the frequency how often the scheduler should run the bot
13. Debug
    * `Debug_mode` True/False debug mode for default.log
    * `Disable_all_transaction_defs` True/False disables all transaction functions, by returning a fake transaction hash
    * `Return_failed_tx` True/False if you want that transaction to be a failed transaction hash
14. Logging
    * `Logging_detail` Define what level of detail each log shall show
15. Other stuff
    * `Safety_multiple_on_transaction_fees` Safety multiple on transaction fees
    * `Block_failed_transaction_cooldown` If case a transaction fails, you can set it to NOT be tried again for a period of hours.

## What the One-Stop-Bot does NOT do:
- Withdraws any UST from Anchor Borrow to deposit that new UST collateral on Mirror.
- Deposits any UST to Anchor Earn to deposit that new aUST as collateral on Mirror.
- Sells, buys, swaps any Luna to deposit it as collateral on Mirror.
- Uses withdrawn aUST or UST from Mirror to repay your Anchor Borrow debt (if you run the One-Stop-Bot often enough of course it will loop and eventually repay that debt).
- If you withdraw pool rewards, sell them, claim UST etc. and it is still not enough UST to exceed the `config.Anchor_Earn_min_deposit_amount` that UST will just remain in your wallet. They will NOT be "remembered" for the next run of the One-Stop-Bot.
- The bot currently only supports UST, aUST and Luna as collateral on Mirror (you really should only use aUST anyway).

## ⚠️ Very important remarks!
- It's recommended to run this code in a contained environment at maximum security.
- Do not run the bot in too short intervals. I implemented async def for the most part, so the current runtime is around 10-30 sec depending on your internet connection.
- Watch your UST balance, as this bot is doing transactions, hence drains your UST balance.
- Use this bot at your own risk. I have done my best to check it, but program bugs & human bugs happen and I am not financial advisor.
- This bot can be used with the Testnet. I strongly recommend playing on the Testnet or with `Disable_all_transaction_defs` set to True first, before letting it manage your funds for real. Here you can get free UST, LUNA etc: https://faucet.terra.money/.
- Since the LTV/min ratios on Mirror and Anchor are defined exactly opposite each other, it may gets confusing to set the `lower_distance`, `target_distance`, `upper_distance`. I wrote some explanations, but make sure you take time to understand it.
- For your own safety all functions are set to False by default. Enable them one by one.
- Deposits / withdrawals of collateral as well as repayments / borrowing of debt are limited by an amount. So if your collateral loses lots of value in one day, there will be multiple deposits / repayments per day to keep your funds safe.
- If however, your collateral gains in value and you withdraw aUST from Mirror or borrow more UST from Anchor a time cooldown (which you can define) will act as a limit. If you set the cooldown to 3, only once every 3 days collateral will be withdrawn from Mirror / more UST will be borrowed from Anchor. This decreases the risk / transaction fees when one day your collateral value spikes, just to crash the next day.
- Since a wallet seed is required, ensure you protect it and know what you're doing while using this automation.
- If you don't want to pass secrets into the B_Config.py file, make sure you declare it as a system variable.
- **Everything** will be logged into the `./logs` folder. Make sure you check those from time to time!

## How to install it
1. `git clone` this repository.
2. Rename `B_Config.py.sample` to `B_Config.py`.
3. Change `B_Config.py` as you desire and feed your seed *(a dedicated wallet is recommended)*.
*  *I strongly recommend to add your seed, API keys, passwords as an environment variable. You can find out how to set this up here: https://dev.to/biplov/handling-passwords-and-secret-keys-using-environment-variables-2ei0*.
4. Run  `pip3 install -r A_Requirements.txt`.
5. Run the One-Stop-Bot with a crontab directly or with `python D_Scheduler.py`.
6. Make yourself familiar with the bot by using the TESTNET first (Get free UST/LUNA here: https://faucet.terra.money/) by enabling features step-by-step.
7. Then use your real wallet on the MAINNET but with `Disable_all_transaction_defs` set to True.
8. If you feel comfortable set `Disable_all_transaction_defs` to False and let the bot work for you. 

## Slack Notification Setup
If you use more Slack, it might be simpler to be notified there using Slack Webhooks.
1. Create a Slack APP.
2. Add the APP to a channel and get a webhook URL to feed the `B_Config.py`.
More information can be found via this link https://api.slack.com/incoming-webhooks.

## Telegram Notification Setup
If you want to be notified via Telegram, you'd need to get `TELEGRAM_TOKEN` and your `TELEGRAM_CHAT_ID` from your Telegram bot.
1. On Telegram, find `@BotFather` and open a DM.
2. Use `/newbot` to create a new bot for yourself.
3. Then, name the bot as you wish, ie: `MyCoolBot`.
4. Now, choose whatever username you desire for your bot, ie: `MyCool_bot`.
5. Done! You should see a "Congratulations" message from BotFather.
6. To get your own `chat_id`, simply send a message in the group with your bot and run the following command below: `curl -s https://api.telegram.org/botACCESSTOKEN/getUpdates` (replace `ACCESSTOKEN` with an actual token you just got from item #5).
7. You should get something like this `{"ok":true .... "from":{"id":1386432285 ...."text":"Hello"}}]}` We are looking for the "id" as this is the `chat_id`.
8. Write your `access_token` and `chat_id` in the `B_Config.py` file.

## Gmail Notification Setup
To send emails from your Google account you need to get a `GMAIL_APP_PASSWORD`.
1. Go to manage my Google account (https://myaccount.google.com/security).
2. Under "Signing in to Google" confirm that "2-Step Verification" is "On" for the account.
3. Under "Signing in to Google" select "App passwords".
4. Select the app as "Mail" and the device as "Other (Custom name)" and name it (for example: One-Stop-Bot-Terra).
5. Copy the app password, it will be in a yellow box and looks like: "cjut fanq prdo diby".

## Under development (in desc priority)
- Run Mirror withdrawals before repay of Anchor Borrow to make use of that available aUST
- Build a front end.

## Similar projects
- https://github.com/unl1k3ly/AnchorHODL