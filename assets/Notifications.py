#!/usr/bin/python3

import B_Config as config
from httpx import post
from json import dumps
from os import system
from email.mime.text import MIMEText

class Notifications:
    if config.Debug_mode: print(f'Notifications Class loaded.')
    def slack_webhook(self, msg:str):
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


    def telegram_notification(self, msg:str):
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


    def email_notification(self, msg:str):

        try:
            with open('One-stop-bot-email-temp-body.txt', 'w', encoding='utf-8') as txt_file:
                txt_file.write(msg)
            system('cat One-stop-bot-email-temp-body.txt | mail -s "' +
                    config.Email_subject + config.Email_address)
        except Exception: # Todo
            pass
        
    def report_content_to_HTML(self, report_content):
        return report_content.replace('\n','\n')

    def report_contect_to_Telegram(self, report_content):
        pass

    def gmail_notification(self, format:str, subject:str, message:str):

        import smtplib
        from email.message import EmailMessage

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config.GMAIL_ACCOUNT, config.GMAIL_APP_PASSWORD)

        if format.lower() == 'html':
            message = self.report_content_to_HTML(message)
            msg = MIMEText(message, "html")
        else:
            msg = EmailMessage()
            msg.set_content(message)
        
        msg['Subject'] = subject
        msg['From'] = config.EMAIL_FROM
        msg['To'] = config.EMAIL_TO
        server.send_message(msg)

    def generate_status_report_html(
        self,
        format,
        Anchor_borrow_info, Mirror_position_info,
        claimable_MIR, claimable_SPEC, claimable_ANC, claimable_UST,
        available_MIR_LP_token_for_withdrawal, available_SPEC_LP_token_for_withdrawal, available_ANC_LP_token_for_withdrawal,
        all_rates):

            status_update = ""

            if format.lower() == 'text':
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
                    status_update += f'If your collateral would lose {Anchor_borrow_info["collateral_loss_to_liq"].__float__()*100:.0f} % you would get liquidated.\n'
                                                    
                if len(Mirror_position_info) > 0:
                    
                    status_update += f'-----------------------------------\n'
                    status_update += f'------------- MIRROR --------------\n'
                    status_update += f'-----------------------------------\n'
                    
                    for position in Mirror_position_info:
                        
                        status_update += f'Position: {position["position_idx"]} - {position["mAsset_symbol"]}\n'
                        status_update += f'Collateral value: {(position["collateral_amount_in_kind"].__float__()/1000000):.0f} {position["collateral_token_denom"]} / {(position["collateral_amount_in_ust"].__float__()/1000000):.0f} UST\n'
                        status_update += f'Shorted value: {(position["shorted_asset_amount"].__float__()/1000000):.0f} UST\n'
                        status_update += f'Current LTV: {position["cur_col_ratio"].__float__()*100:.0f} %\n'
                        status_update += f'If all your collateral loses {(position["collateral_loss_to_liq"].__float__()*100):.0f} %\n'
                        status_update += f'or if {position["mAsset_symbol"]} raises by {(position["shorted_mAsset_gain_to_liq"].__float__()*100):.0f} % you would get liquidated.\n'
                        status_update += f'\n'

                    status_update +=f'Reserve info: In order to increase your LTV by 5 % on all positions you would need assets valued {Mirror_position_info[len(Mirror_position_info)-1]["reserve_UST"].__float__()/1000000:.0f} UST. Do you have enough?'
                  
                status_update += f'-----------------------------------\n'
                status_update += f'----------- OTHER INFO ------------\n'
                status_update += f'-----------------------------------\n'

                status_update += f'Liquidity Pools:\n'
                status_update += f'MIR-UST: {available_MIR_LP_token_for_withdrawal.__float__()/1000000 * all_rates["MIR-TOKEN-PER-SHARE"].__float__():.2f} MIR ({available_MIR_LP_token_for_withdrawal.__float__()/1000000 * all_rates["MIR-TOKEN-PER-SHARE"].__float__() * all_rates["MIR"].__float__()/1000000:.2f} UST)\n'
                status_update += f'SPEC-UST: {available_SPEC_LP_token_for_withdrawal.__float__()/1000000 * all_rates["SPEC-TOKEN-PER-SHARE"].__float__():.2f} SPEC ({available_SPEC_LP_token_for_withdrawal.__float__()/1000000 * all_rates["SPEC-TOKEN-PER-SHARE"].__float__() * all_rates["SPEC"].__float__()/1000000:.2f} UST)\n'
                status_update += f'ANC-UST: {available_ANC_LP_token_for_withdrawal.__float__()/1000000 * all_rates["ANC-TOKEN-PER-SHARE"].__float__():.2f} ANC ({available_ANC_LP_token_for_withdrawal.__float__()/1000000 * all_rates["ANC-TOKEN-PER-SHARE"].__float__() * all_rates["ANC"].__float__()/1000000:.2f} UST)\n'
                status_update += f'\n'
                status_update += f'Claimable / staked:\n'
                status_update += f'MIR: {claimable_MIR.__float__()/1000000:.2f} ({claimable_MIR.__float__()/1000000 * all_rates["MIR"].__float__()/1000000:.2f} UST)\n'
                status_update += f'SPEC: {claimable_SPEC.__float__()/1000000:.2f} ({claimable_SPEC.__float__()/1000000 * all_rates["SPEC"].__float__()/1000000:.2f} UST)\n'
                status_update += f'ANC: {claimable_ANC.__float__()/1000000:.2f} ({claimable_ANC.__float__()/1000000 * all_rates["ANC"].__float__()/1000000:.2f} UST)\n'
                status_update += f'UST: {claimable_UST.__float__()/1000000:.2f}\n'
                status_update += f'\n'
                status_update += f'Current price in UST, minimum sell prices in UST, distance:\n'
                status_update += f'MIR: {all_rates["MIR"].__float__()/1000000:.2f}, {config.MIR_min_price:.2f}, {(config.MIR_min_price / all_rates["MIR"].__float__()/1000000 - 1 ) * 100:.2f} %\n'
                status_update += f'SPEC: {all_rates["SPEC"].__float__()/1000000:.2f}, {config.SPEC_min_price:.2f}, {(config.SPEC_min_price/ all_rates["SPEC"].__float__()/1000000 - 1 ) * 100:.2f} %\n'
                status_update += f'ANC: {all_rates["ANC"].__float__()/1000000:.2f}, {config.ANC_min_price:.2f}, {(config.ANC_min_price/ all_rates["ANC"].__float__()/1000000 - 1 ) * 100:.2f} %\n'
                status_update += f'\n'

                
            elif format.lower() == 'html':
                if Anchor_borrow_info["loan_amount"] > 0:
                    status_update += f'<h2>Anchor</h2>' 
                    status_update += f'bETH collateral: {(Anchor_borrow_info["amount_bETH_collateral"].__float__()/1000000):.3f} bETH<br>'
                    status_update += f'bLuna collateral: {(Anchor_borrow_info["amount_bLuna_collateral"].__float__()/1000000):.0f} bLuna<br>'
                    status_update += f'Total collateral: {(Anchor_borrow_info["total_collateral_value"].__float__()/1000000):.0f} UST<br>'
                    status_update += f'Loan amount: {(Anchor_borrow_info["loan_amount"].__float__()/1000000):.0f} UST<br>'
                    status_update += f'Borrow limit: {(Anchor_borrow_info["borrow_limit"].__float__()/1000000):.0f} UST<br>'
                    status_update += f'Current LTV: {Anchor_borrow_info["cur_col_ratio"].__float__()*100:.0f} %<br>'
                    status_update += f'If your collateral would lose {Anchor_borrow_info["collateral_loss_to_liq"].__float__()*100:.0f} % you would get liquidated.<br>'
                                                    
                if len(Mirror_position_info) > 0:
                    
                    status_update += f'<h2>Mirror</h2>' 
                    
                    for position in Mirror_position_info:
                        
                        status_update += f'<h3>Position: {position["position_idx"]} - {position["mAsset_symbol"]}</h3>'
                        status_update += f'Collateral value: {(position["collateral_amount_in_kind"].__float__()/1000000):.0f} {position["collateral_token_denom"]}<br>'
                        status_update += f'Collateral value: {(position["collateral_amount_in_ust"].__float__()/1000000):.0f} UST<br>'
                        status_update += f'Shorted value in UST: {(position["shorted_asset_amount"].__float__()/1000000):.0f} UST<br>'
                        status_update += f'Current LTV: {position["cur_col_ratio"].__float__()*100:.0f} %<br>'
                        status_update += f'If your collateral would lose {(position["collateral_loss_to_liq"].__float__()*100):.0f} %<br>'
                        status_update += f'or if {position["mAsset_symbol"]} would raise by {(position["shorted_mAsset_gain_to_liq"].__float__()*100):.0f} % you would get liquidated.<br>'
                        status_update += f'<br>'

                    status_update += f'Reserve: In order to increase your LTV by 5 % on all positions you would need assets valued at {Mirror_position_info[len(Mirror_position_info)-1]["reserve_UST"].__float__()/1000000:.0f} UST. Do you have enough?'

                status_update += f'<h2>Other Info</h2>' 

                status_update += f'Liquidity Pools:<br>'
                status_update += f'MIR-UST: {available_MIR_LP_token_for_withdrawal.__float__()/1000000 * all_rates["MIR-TOKEN-PER-SHARE"].__float__():.2f} MIR ({available_MIR_LP_token_for_withdrawal.__float__()/1000000 * all_rates["MIR-TOKEN-PER-SHARE"].__float__() * all_rates["MIR"].__float__()/1000000:.2f} UST)<br>'
                status_update += f'SPEC-UST: {available_SPEC_LP_token_for_withdrawal.__float__()/1000000 * all_rates["SPEC-TOKEN-PER-SHARE"].__float__():.2f} SPEC ({available_SPEC_LP_token_for_withdrawal.__float__()/1000000 * all_rates["SPEC-TOKEN-PER-SHARE"].__float__() * all_rates["SPEC"].__float__()/1000000:.2f} UST)<br>'
                status_update += f'ANC-UST: {available_ANC_LP_token_for_withdrawal.__float__()/1000000 * all_rates["ANC-TOKEN-PER-SHARE"].__float__():.2f} ANC ({available_ANC_LP_token_for_withdrawal.__float__()/1000000 * all_rates["ANC-TOKEN-PER-SHARE"].__float__() * all_rates["ANC"].__float__()/1000000:.2f} UST)<br>'
                status_update += f'<br>'
                status_update += f'Claimable / staked:<br>'
                status_update += f'MIR: {claimable_MIR.__float__()/1000000:.2f} ({claimable_MIR.__float__()/1000000 * all_rates["MIR"].__float__()/1000000:.2f} UST)<br>'
                status_update += f'SPEC: {claimable_SPEC.__float__()/1000000:.2f} ({claimable_SPEC.__float__()/1000000 * all_rates["SPEC"].__float__()/1000000:.2f} UST)<br>'
                status_update += f'ANC: {claimable_ANC.__float__()/1000000:.2f} ({claimable_ANC.__float__()/1000000 * all_rates["ANC"].__float__()/1000000:.2f} UST)<br>'
                status_update += f'UST: {claimable_UST.__float__()/1000000:.2f}<br>'
                status_update += f'<br>'
                status_update += f'Current price in UST, minimum sell prices in UST, distance:<br>'
                status_update += f'MIR: {all_rates["MIR"].__float__()/1000000:.2f}, {config.MIR_min_price:.2f}, {(config.MIR_min_price / (all_rates["MIR"].__float__()/1000000) - 1 ) * 100:.2f} %<br>'
                status_update += f'SPEC: {all_rates["SPEC"].__float__()/1000000:.2f}, {config.SPEC_min_price:.2f}, {(config.SPEC_min_price / (all_rates["SPEC"].__float__()/1000000) - 1 ) * 100:.2f} %<br>'
                status_update += f'ANC: {all_rates["ANC"].__float__()/1000000:.2f}, {config.ANC_min_price:.2f}, {(config.ANC_min_price / (all_rates["ANC"].__float__()/1000000) - 1 ) * 100:.2f} %<br>'
                status_update += f'<br>'

            return status_update

    
