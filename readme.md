## Summary
Tired of non-stop worring whether you will get liquidated when the market moves? You want to get the maximum out of your Degen Delta Neutral Strategy on Mirror? You want to minimize the risk of your rewards token (SPEC, MIR) losing in value, and rather want to sell them? You want to maintain a healthy LTV on your Anchor Borrow and deposit the borrowed UST into Anchor Earn?

Then, this bot is for you!

Automatically manage all your ANC, MIR, SPEC token rewards, Mirror Delta Neutral Short Positions, UST claims after lockup, Anchor Borrow and Earn for Terra.

## Thank you!
If this script is helpful to you and helps maximize your gainz, feel free to donate a bit to **terra1xl0ww4tykjmm4vnzck0qz5luu6rxl97wuwmgfg**. This will also keep the development going and the script up-to-date. Thank you! :)

*Special thanks to unl1k3ly as his bot taught me what I needed to know. Thanks Terra, Mirror, Spectrum, Anchor team and the Terra Community!*

## What this script does
1. Claims and sells your un-claimed MIR, SPEC, ANC tokens
2. Claims unlocked UST on Mirror
3. Repays debt at Anchor if your LTV requires it
4. Borrows more UST from Anchor if you LTV allows it
5. Deposits UST (from sale of MIR, SPEC, ANC and Borrow) in Anchor Earn to get more aUST
6. Checks each of your shorted positions whether they are below or above your defined limits.
    * If above: It will withdraw aUST to return to your defined ratio
    * If below: It will deposit more aUST to return to your defined ratio
7. Sends you an update via Slack, Telegram or Email

*Due to the order of which the functions are exectuted, the priority is on a repayment of debt to Anchor rather than depositing more aUST into your shorts on Mirror. As crypto is more volatile than the legacy stock market.*

## What can be configured
*Almost* **everything** can be configered in the `B_config.py`.
1. Sells your un-claimed MIR, SPEC tokens
    * `XXX_claim_and_sell_token` True/False sale of SPEC, MIR, ANC
    * `XXX_min_price` Define a minimum price for MIR/SPEC
    * `XXX_min_total_value` Define a minimum  sales value (= price of token * amount to sell) for MIR/SPEC
2. Claims unlocked UST on Mirror
	* `Mirror_claim_unlocked_UST` True/False claim of unlocked UST
	* `Mirror_min_amount_UST_to_claim` Define a minimum of unlocked UST to be claimed
3. Repays debt at Anchor if your LTV requires it
    * `Anchor_enable_auto_repay_of_debt` True/False auto repayment of debt
    * `Anchor_enable_withdraw_of_deposited_UST` True/False allowance to withdraw UST from Anchor Earn to repay debt
    * `Anchor_enable_partially_repay_if_not_enough_UST_in_wallet` True/False of partial debt repayment (withdraw all deposited UST on Anchor Earn + all UST available in wallet)
    * `Anchor_lower_distance` Define lower_distance from maximal ltv ratio below a repayment will be executed
    * `Anchor_target_distance`Define target_distance from maximal ltv ratio that is restored when repay debt/borrow more UST
    * `Anchor_min_repay_limit` Define minimum debt repayment limit
4. Borrows more UST from Anchor if you LTV allows it
    * `Anchor_enable_deposit_borrowed_UST` True/False auto borrow of more UST
    * `Anchor_upper_distance`Define upper_distance from maximal ltv ratio above more UST will be borrowed
    * `Anchor_borrow_cooldown` Define cooldown period in days for the auto borrow function
    * `Anchor_min_borrow_limit` Define minimum borrow limit
5. Deposits UST (from sale of MIR, SPEC, ANC and Borrow) in Anchor Earn to get more aUST
    * `Anchor_enable_deposit_borrowed_UST` True/False enable deposit of freshly gained UST (from the sale of SPEC, MIR & Mirror claim) into Anchor Earn
    * `Anchor_min_deposit_amount` Define minimum UST amount to deposit
6. Checks each of your shorted positions
    * `Mirror_enable_deposit_collateral` True/False deposit of collateral (Luna, UST, aUST supported)
    * `Mirror_lower_distance` Define lower_distance from minimal ratio below collateral will be deposited
    * `Mirror_target_distance` Define target_distance from minimal ratio that is restored when depoit/withdraw collateral
    * `Mirror_min_deposit_limit` Define minimum deposit limit
    * `Mirror_enable_withdraw_collateral` True/False withdraw of collateral
    * `Mirror_upper_distance` Define upper_distance from minimal ratio above collateral will be withdrawn
    * `Mirror_withdraw_cooldown` Define cooldown period in days for the auto withdraw function
7. Sends you a report on Telegram, Slack, Email, write log into ./logs
    * `Debug_mod` True/False debug mode for default.log
    * `Logging_detail` Define what level of detail each log shall show
    * `Send_me_a_report` True/False prepares an summary of what has happend, if something has happend. Always includes WARNINGs and ERRORs.
    * `Notify_Telegram` True/False notifications to be recieved on Slack
    * `Notify_Email` True/False notifications to be recieved on Telegram
    * `Email_subject` True/False notifications to be recieved as an Email
8. Other
    * `safety_multiple_on_transaction_fees` Safety multiple on transaction fees

## What the script does NOT do:
- Withdraws any UST from Anchor Borrow to deposit that new UST collateral on Mirror
- Deposits any UST to Anchor Earn to desposit that new aUST as collateral on Mirror
- Sells, buy, swap any Luna to deposit it as collateral on Mirror
- Uses withdrawn aUST or UST from Mirror to repay your Anchor Borrow debt (if you run the script often enough of course it will loop and eventually repay that debt.)
- If you withdraw pool rewards, sell them, claim UST etc. and it is still not enough UST to exceed the `config.Anchor_min_deposit_amount` that UST will just remain in your wallet. They will NOT be "remembere" for the next run of the script.

## Very important remarks!
- This script is quite heavy, so do not run it too short intervals. It currently runs at around 30 sec to 1 min. Depending on your internet connection.
- Use this bot on your own risk. I have done my best to check it, but program bugs & human bugs happen.
- This bot can be used with the Testnet. I strongly recommend to play on the Testnet first, before letting it manage your funds.
- Since the LTV/min ratios on Mirror and Anchor are defined excatly opposite it each other, it may get confusing to set the `lower_distance`, `target_distance`, `upper_distance`. I wrote some explanations, but make sure you take time to understand it
- All functions are set to False by default. Enable then one by one.
- It's recommended to run this code in a contained environment at maximum security.
- Deposits of collateral / repayments of debt are are limited by an amount. So if your collateral loses lots of value in one day, there will be multiple depoits / repayments per day to keep your funds safe.
- If however, you collateral gains in value and you withdraw aUST from Mirror or borrow more UST form Anchor a time cooldown (which you can define) will act as a limit. If you set the cooldown to 3. Only once every 3 days collateral will be withdrawn / more UST will be borrowed.
- Since a wallet seed is required, ensure you protect it and know what you're doing while using this automation
- If you don't want to pass secrets into the B_Config.py file, make sure you declare as a system variable.
- **Everything** will be logged into the `./logs` folder. Make sure you check those from time to time!

## How to install it
1. `git clone` this repository
2. Rename `B_Config_.py` to  `B_Config.py`
3. Change `B_Config.py` as you desire and feed your seed *(a dedicated wallet is recommended)*
4. Run  `pip3  install -r A_Requirements.txt`
5. Run the script with a crontab *more options are in the development*

## Slack Notification 
If you use more Slack, it might be simpler to be notified in there using Slack Webhooks.
1. Create a Slack APP
2. Add the APP to a channel and get a webhook URL to feed the `B_Config.py`
More information can be found via this link https://api.slack.com/incoming-webhooks

## Telegram Notification
If you want to be notified via Telegram, you'd need to get `access_token` and your `chat_id` from your Telegram bot.
If you are not familiarized creating a Telegram bot, please follow steps below:
1. On Telegram, find `@BotFather` and open a DM.
2. Use `/newbot` to create a new bot for yourself.
3. Then, name the bot as you wish, ie: `MyCoolBot`
4. Now, choose whatever username you desire for your bot, ie: `MyCool_bot` 
5. Done! You should see a "Congratulations" message from BotFather.
6. Add `MyCool_bot` to a group.
7. To get your own `chat_id`, simply send a message in the group with your bot and run the following command below: `curl -s  https://api.telegram.org/botACCESSTOKEN/getUpdates` (replace `ACCESSTOKEN` with an actual token you just got from item #5).
8. With  `access_token` and `chat_id` just feed the `B_Config.py` file.

## Under development (in desc priority)
- Email Notifications
- Bundle of queries as this script is spaming queries like crazy
- Bundle transactions (for example Swaps) to save fees
- Run Mirror withdrawls before repay of Anchor Borrow to make use of that available aUST

## Similar projects
- https://github.com/unl1k3ly/AnchorHODL