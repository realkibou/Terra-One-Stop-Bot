#!/usr/bin/python3

# Terra SKD
from terra_sdk.core.numeric import Dec


# Other assets
from assets.Logging import Logger
import B_Config as config

# Other imports
from json import dump, load
from os import path
from datetime import datetime

class Cooldown:
    if config.Debug_mode: print(f'Cooldown Class loaded.')
    default_logger = Logger().default_logger

    def write_cooldown(self, cooldowns):
        with open('X_Cooldowns.json', 'w') as fp:
            # Stringify dates otherwise cannot be written into json
            for index in cooldowns:
                cooldowns[index] = f'{cooldowns[index]:%Y-%m-%d %H:%M}'
            self.default_logger.debug(f'[Script] {cooldowns} has been written to X_Cooldowns.json')
            dump(cooldowns, fp)
        fp.close
        pass

    def read_cooldown(self):

        # If file does not exists create one and fill it with data
        if not path.isfile('X_Cooldowns.json'):
            with open('X_Cooldowns.json', 'w') as fp:
                self.default_logger.debug(f'[Script] X_Cooldowns.json did not exist, so it was created.')
            fp.close
            return {}
        
        try:
            f = open('X_Cooldowns.json')
            cooldowns = load(f)
            self.default_logger.debug(f'[Script] X_Cooldowns.json existed and has been read: {cooldowns}')
            f.close

            for index in cooldowns:
                cooldowns[index] = datetime.strptime(cooldowns[index], '%Y-%m-%d %H:%M')
        
            return cooldowns
        except:
            # If there is anything wrong with the X_Cooldowns.json, it will just give an empty dict.
            return {}

class Prettify:
    if config.Debug_mode: print(f'Prettify Class loaded.')
    def email_text_to_html(self):
        # Todo
        pass

    def value_convert_dec_to_float(self, input_value, human):

        if type(input_value) == Dec:
            # If you need a bigger number than 1000000, then you are way too rich lol
            if input_value > 1000000:
                if human:
                    output_value = f'{float(input_value / 1000000):.2f}'
                else:
                    output_value = input_value.__int__()
            else:
                output_value = f'{input_value.__float__():.2f}'
            
            return output_value
        else:    
            return input_value

    def dict_value_convert_dec_to_float(self, input_value, human=False):

        # Maybe its a list of dict
        if type(input_value) is list:
            output_value = []
            for item in input_value:
                output_value.append(dict((k, self.value_convert_dec_to_float(v, human)) for k, v in item.items()))
            return output_value

        # If it is just a plain dict
        elif type(input_value) is dict:
            return dict((k, self.value_convert_dec_to_float(v, human)) for k, v in input_value.items())

    def generate_status_report(self, Anchor_borrow_info, Mirror_position_info):

            status_update = ""            

            if config.Email_format == 'text' or 'TEXT' or 'TXT':
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
                    status_update += f'If all your collateral loses {Anchor_borrow_info["collateral_loss_to_liq"].__float__()*100:.0f}% you would get liquidated.\n'
                                                    
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
                
            elif config.Email_format == 'html' or 'HTML':
                if Anchor_borrow_info["loan_amount"] > 0:
                    status_update += f'<h2>Anchor</h2>' 
                    status_update += f'bETH collateral: {(Anchor_borrow_info["amount_bETH_collateral"].__float__()/1000000):.3f} bETH</br>'
                    status_update += f'bLuna collateral: {(Anchor_borrow_info["amount_bLuna_collateral"].__float__()/1000000):.0f} bLuna</br>'
                    status_update += f'Total collateral: {(Anchor_borrow_info["total_collateral_value"].__float__()/1000000):.0f} UST</br>'
                    status_update += f'Loan amount: {(Anchor_borrow_info["loan_amount"].__float__()/1000000):.0f} UST</br>'
                    status_update += f'Borrow limit: {(Anchor_borrow_info["borrow_limit"].__float__()/1000000):.0f} UST</br>'
                    status_update += f'Current LTV: {Anchor_borrow_info["cur_col_ratio"].__float__()*100:.0f} %</br>'
                    status_update += f'If all your collateral loses {Anchor_borrow_info["collateral_loss_to_liq"].__float__()*100:.0f}% you would get liquidated.</br>'
                                                    
                if len(Mirror_position_info) > 0:
                    
                    status_update += f'<h2>Mirror</h2>' 
                    
                    for position in Mirror_position_info:
                        
                        status_update += f'<h3>Position: {position["position_idx"]} - {position["mAsset_symbol"]}</h3>'
                        status_update += f'Collateral value: {(position["collateral_amount_in_kind"].__float__()/1000000):.0f} {position["collateral_token_denom"]}</br>'
                        status_update += f'Collateral value: {(position["collateral_amount_in_ust"].__float__()/1000000):.0f} UST</br>'
                        status_update += f'Shorted Value in UST: {(position["shorted_asset_amount"].__float__()/1000000):.0f} UST</br>'
                        status_update += f'Current LTV: {position["cur_col_ratio"].__float__():.0f}00 %</br>'
                        status_update += f'If all your collateral loses {(position["collateral_loss_to_liq"].__float__()*100):.0f}%</br>'
                        status_update += f'or if {position["mAsset_symbol"]} raises by {(position["shorted_mAsset_gain_to_liq"].__float__()*100):.0f}% you would get liquidated.</br>'
                        status_update += f'</br>'
            
            return status_update