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
