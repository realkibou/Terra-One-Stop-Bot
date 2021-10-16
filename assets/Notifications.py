#!/usr/bin/python3

import B_Config as config
from requests import post
from json import dumps
from os import system
from email.mime.text import MIMEText

class Notifications:
    if config.Debug_mode: print(f'Notifications Class loaded.')
    def slack_webhook(msg:str):
        slack_data = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": msg
                    }
                }
            ]
        }

        try:
            response = post(
                config.SLACK_WEBHOOK_URL, data=dumps(slack_data),
                headers={'Content-Type': 'application/json'}, timeout=5
            )
            if response.status_code != 200:
                raise ValueError(
                    'Request to slack returned an error %s, the response is:\n%s'
                    % (response.status_code, response.text)
                )
        except Exception: # Todo
            pass


    def telegram_notification(msg:str):
        tg_data = {"chat_id": str(config.TELEGRAM_CHAT_ID),
                "text": msg, "parse_mode": 'Markdown'}

        try:
            response = post('https://api.telegram.org/bot' + config.TELEGRAM_TOKEN + '/sendMessage', data=dumps(tg_data),
                                    headers={'Content-Type': 'application/json'}, timeout=5
                                    )
            if response.status_code != 200:
                raise ValueError(
                    'Request to slack returned an error %s, the response is:\n%s'
                    % (response.status_code, response.text)
                )
        except Exception: # Todo
            pass


    def email_notification(msg:str):

        try:
            with open('One-stop-bot-email-temp-body.txt', 'w', encoding='utf-8') as txt_file:
                txt_file.write(msg)
            system('cat One-stop-bot-email-temp-body.txt | mail -s "' +
                    config.Email_subject + config.Email_address)
        except Exception: # Todo
            pass

    def gmail_notification(format:str, subject:str, message:str):

        import smtplib
        from email.message import EmailMessage

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config.GMAIL_ACCOUNT, config.GMAIL_APP_PASSWORD)

        if format == 'HTML':
            msg = MIMEText(message, "html")
        else:
            msg = EmailMessage()
            msg.set_content(message)
        
        msg['Subject'] = subject
        msg['From'] = config.EMAIL_FROM
        msg['To'] = config.EMAIL_TO
        server.send_message(msg)

    def generate_status_report(Anchor_borrow_info, Mirror_position_info):

            status_update = ""

            if config.Email_format.lower() == 'text' or config.Email_format.lower() == 'txt':
                if Anchor_borrow_info["loan_amount"] > 0:
                    status_update += f'-----------------------------------\n'
                    status_update += f'------------- ANCHOR --------------\n'
                    status_update += f'-----------------------------------\n'
                    status_update += f'bETH collateral: {(Anchor_borrow_info["amount_bETH_collateral"].__float__()/1000000):.3f} bETH\n'
                    status_update += f'bLuna collateral: {(Anchor_borrow_info["amount_bLuna_collateral"].__float__()/1000000):.0f} bLuna\n'
                    status_update += f'Total collateral: {(Anchor_borrow_info["total_collateral_value"].__float__()/1000000):.0f} UST\n'
                    status_update += f'Loan amount: {(Anchor_borrow_info["loan_amount"].__float__()/1000000):.0f} UST\n'
                    status_update += f'Borrow limit: {(Anchor_borrow_info["borrow_limit"].__float__()/1000000):.0f} UST\n'
                    status_update += f'Current LTV: {Anchor_borrow_info["cur_col_ratio"].__float__()*100:.0f} %\n'
                    status_update += f'If your collateral would lose {Anchor_borrow_info["collateral_loss_to_liq"].__float__()*100:.0f}% you would get liquidated.\n'
                                                    
                if len(Mirror_position_info) > 0:
                    
                    status_update += f'-----------------------------------\n'
                    status_update += f'------------- MIRROR --------------\n'
                    status_update += f'-----------------------------------\n'
                    
                    for position in Mirror_position_info:
                        
                        status_update += f'Position: {position["position_idx"]} - {position["mAsset_symbol"]}\n'
                        status_update += f'Collateral value: {(position["collateral_amount_in_kind"].__float__()/1000000):.0f} {position["collateral_token_denom"]}\n'
                        status_update += f'Collateral value: {(position["collateral_amount_in_ust"].__float__()/1000000):.0f} UST\n'
                        status_update += f'Shorted Value in UST: {(position["shorted_asset_amount"].__float__()/1000000):.0f} UST\n'
                        status_update += f'Current LTV: {position["cur_col_ratio"].__float__():.0f}00 %\n'
                        status_update += f'If all your collateral loses {(position["collateral_loss_to_liq"].__float__()*100):.0f}%\n'
                        status_update += f'or if {position["mAsset_symbol"]} raises by {(position["shorted_mAsset_gain_to_liq"].__float__()*100):.0f}% you would get liquidated.\n'
                        status_update += f'\n'
                
            elif config.Email_format == 'html' or config.Email_format =='HTML':
                if Anchor_borrow_info["loan_amount"] > 0:
                    status_update += f'<h2>Anchor</h2>' 
                    status_update += f'bETH collateral: {(Anchor_borrow_info["amount_bETH_collateral"].__float__()/1000000):.3f} bETH<br>'
                    status_update += f'bLuna collateral: {(Anchor_borrow_info["amount_bLuna_collateral"].__float__()/1000000):.0f} bLuna<br>'
                    status_update += f'Total collateral: {(Anchor_borrow_info["total_collateral_value"].__float__()/1000000):.0f} UST<br>'
                    status_update += f'Loan amount: {(Anchor_borrow_info["loan_amount"].__float__()/1000000):.0f} UST<br>'
                    status_update += f'Borrow limit: {(Anchor_borrow_info["borrow_limit"].__float__()/1000000):.0f} UST<br>'
                    status_update += f'Current LTV: {Anchor_borrow_info["cur_col_ratio"].__float__()*100:.0f} %<br>'
                    status_update += f'If your collateral would lose {Anchor_borrow_info["collateral_loss_to_liq"].__float__()*100:.0f}% you would get liquidated.<br>'
                                                    
                if len(Mirror_position_info) > 0:
                    
                    status_update += f'<h2>Mirror</h2>' 
                    
                    for position in Mirror_position_info:
                        
                        status_update += f'<h3>Position: {position["position_idx"]} - {position["mAsset_symbol"]}</h3>'
                        status_update += f'Collateral value: {(position["collateral_amount_in_kind"].__float__()/1000000):.0f} {position["collateral_token_denom"]}<br>'
                        status_update += f'Collateral value: {(position["collateral_amount_in_ust"].__float__()/1000000):.0f} UST<br>'
                        status_update += f'Shorted Value in UST: {(position["shorted_asset_amount"].__float__()/1000000):.0f} UST<br>'
                        status_update += f'Current LTV: {position["cur_col_ratio"].__float__():.0f}00 %<br>'
                        status_update += f'If your collateral would lose {(position["collateral_loss_to_liq"].__float__()*100):.0f}%<br>'
                        status_update += f'or if {position["mAsset_symbol"]} would raise by {(position["shorted_mAsset_gain_to_liq"].__float__()*100):.0f}% you would get liquidated.<br>'
                        status_update += f'<br>'
            
            return status_update

    def report_content_to_HTML(report_content):
        return report_content.replace('\n','<br>')
