#!/usr/bin/python3

#-----------------------------------
#---------- HELPFUL LINKS ----------
#-----------------------------------
# https://faucet.terra.money/
# https://terra.spec.finance/
# https://docs.spec.finance/
# https://github.com/spectrumprotocol/frontend/blob/11de02569898be54abc716b5a651cbf064865db5/src/app/consts/networks.ts
# https://terra.mirror.finance/
# https://docs.mirror.finance/
# https://finder.terra.money/
# https://terra-money.github.io/terra-sdk-python/
# https://docs.anchorprotocol.com/
# https://api.extraterrestrial.money/v1/api/prices
# https://assets.terra.money/cw20/tokens.json
# https://assets.terra.money/cw20/contracts.json

# Terra SDK
from terra_sdk.core.numeric import Dec
# Other assets
from assets.Notifications import Notifications
from assets.Other import Cooldown, Prettify
from assets.Logging import Logger
from assets.Terra import Terra
from assets.Queries import Queries
from assets.Transactions import Transaction
import B_Config as config

# Other imports
from datetime import datetime, timedelta, date
from time import time
from copy import deepcopy
from traceback import format_exc
# import traceback
import asyncio

Transaction_class, Queries_class, Cooldown_class, Logger_class, Terra_class, Prettify_class, Notifications_class = Transaction(), Queries(), Cooldown(), Logger(), Terra, Prettify(), Notifications()
default_logger, report_logger, report_array = Logger_class.default_logger, Logger_class.report_logger, Logger_class.report_array

async def main():
    # Other assets

    if config.Debug_mode: print(f'main() started.')

    begin_time = time()
    err = None

    try:
        tax_rate = Terra.terra.treasury.tax_rate()

        cooldowns, \
        Mirror_position_info, \
        Anchor_borrow_info, \
        all_rates,\
        wallet_balance, \
        general_estimated_tx_fee \
            = await asyncio.gather(
        Cooldown_class.read_cooldown(),
        Queries_class.Mirror_get_position_info(),
        Queries_class.Anchor_get_borrow_info(),
        Queries_class.get_all_rates(),
        Queries_class.get_wallet_balances(),
        Queries_class.get_fee_estimation()
        )


        available_MIR_LP_token_for_withdrawal, \
        available_ANC_LP_token_for_withdrawal, \
        available_SPEC_LP_token_for_withdrawal, \
        claimable_UST = 0, 0, 0, 0

        general_estimated_tx_fee = Dec(general_estimated_tx_fee)

        if wallet_balance['uusd'] < general_estimated_tx_fee:
            report_logger.warning(f'[Script] YOU NEED TO ACT! Your wallet balance of {(wallet_balance["uusd"].__float__() / 1000000):.2f} UST is too low to execute any transaction.')
            raise Exception
        
        datetime_now = datetime.now()
        status_update = False
        action_dict = {'MIR' : 'none','SPEC' : 'none','ANC' : 'none', 'PSI' : 'none'}
        claimable_MIR = claimable_SPEC = claimable_ANC = value_of_SPEC_LP_token =available_ANC_LP_token_for_withdrawal = value_of_ANC_LP_token = 0
        wallet_balance_before = deepcopy(wallet_balance)

        default_logger.debug(f'Wallet_balance_before: {Prettify_class.dict_value_convert_dec_to_float(wallet_balance_before, True)}')

        # default_logger.debug(f'------------------------------------------\n'
        #                     f'-------- WITHDRAW FROM LP SECTION --------\n'
        #                     f'------------------------------------------\n')

        # Check if the this section for the token is enabled
        if config.MIR_withdraw_and_sell_if_min_price_is_reached:
            if cooldowns.get('withdraw_MIR_from_pool') is None or cooldowns['withdraw_MIR_from_pool'] <= datetime_now:
                # Check if there is enough UST balance in the wallet to pay the transaction fees
                if wallet_balance['uusd'] > general_estimated_tx_fee:
                    available_MIR_LP_token_for_withdrawal = Queries_class.get_available_LP_token_for_withdrawal(Terra_class.mirrorFarm, Terra_class.MIR_token)
                    value_of_MIR_LP_token = all_rates['MIR-TOKEN-PER-SHARE'] * available_MIR_LP_token_for_withdrawal * all_rates['MIR']/1000000 \
                                            + all_rates['MIR-UST-PER-SHARE'] * available_MIR_LP_token_for_withdrawal
                    # Check if the min_price for the token has been matched
                    if (all_rates['MIR']/1000000) > config.MIR_min_price:
                        # Check if there are any LP for that token available
                        if available_MIR_LP_token_for_withdrawal > 0:
                            # Check if the min_withdrawal_limit is exceeded
                            if (value_of_MIR_LP_token/1000000) > config.MIR_min_total_value:
                                # Unstake / withdrawn LP
                                withdraw_MIR_from_pool_tx = Transaction_class.withdraw_MIR_from_pool(available_MIR_LP_token_for_withdrawal)
                                withdraw_MIR_from_pool_tx_status = Queries_class.get_status_of_tx(withdraw_MIR_from_pool_tx)
                                if withdraw_MIR_from_pool_tx_status == True:
                                    default_logger.debug(f'[MIR LP Withdrawal] Success TX: {withdraw_MIR_from_pool_tx}')
                                    report_logger.info(f'[MIR LP Withdrawal] MIR & UST have been withdrawn from the LP.')
                                    # Mark for sell
                                    action_dict['MIR'] = 'sell'
                                    # Update UST balance in wallet
                                    wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                else:
                                    report_logger.warning(f'[MIR LP Withdrawal] Failed TX: {withdraw_MIR_from_pool_tx}.\n'
                                                        f'[MIR LP Withdrawal] Reason: {withdraw_MIR_from_pool_tx_status}')
                                    cooldowns['withdraw_MIR_from_pool'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                            else:
                                default_logger.debug(f'[MIR LP Withdrawal] Skipped because withdrawable LP token value ({(value_of_MIR_LP_token.__float__()/1000000):.2f}) below limit ({config.MIR_min_total_value}).')
                        else:
                            default_logger.debug(f'[MIR LP Withdrawal] Skipped because no withdrawable LP token ({(available_MIR_LP_token_for_withdrawal.__float__()/1000000):.0f}).')
                    else:
                        default_logger.debug(f'[MIR LP Withdrawal] Skipped because minimum price of MIR ({config.MIR_min_price}) not exceeded ({(all_rates["MIR"].__float__()/1000000):.2f}).')
                else:
                    report_logger.warning(f'[MIR LP Withdrawal] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                    return False
            else:
                default_logger.debug(f'[MIR LP Withdrawal] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["withdraw_MIR_from_pool"]}).')
        else:
            default_logger.debug(f'[MIR LP Withdrawal] Skipped because disabled by config ({config.MIR_withdraw_and_sell_if_min_price_is_reached}).')

        # Check if the this section for the token is enabled
        if config.SPEC_withdraw_and_sell_if_min_price_is_reached:
            if cooldowns.get('withdraw_SPEC_from_pool') is None or cooldowns['withdraw_SPEC_from_pool'] <= datetime_now:
                # Check if there is enough UST balance in the wallet to pay the transaction fees
                if wallet_balance['uusd'] > general_estimated_tx_fee:
                    available_SPEC_LP_token_for_withdrawal = Queries_class.get_available_LP_token_for_withdrawal(Terra_class.specFarm, Terra_class.SPEC_token)
                    value_of_SPEC_LP_token = all_rates['SPEC-TOKEN-PER-SHARE'] * available_SPEC_LP_token_for_withdrawal * all_rates['SPEC']/1000000 \
                                            + all_rates['SPEC-UST-PER-SHARE'] * available_SPEC_LP_token_for_withdrawal
                    # Check if the min_price for the token has been matched
                    if (all_rates['SPEC']/1000000) > config.SPEC_min_price:
                        # Check if there are any LP for that token available
                        if available_SPEC_LP_token_for_withdrawal > 0:
                            # Check if the min_withdrawal_limit is exceeded
                            if (value_of_SPEC_LP_token/1000000) > config.SPEC_min_total_value:
                                # Unstake / withdrawn LP
                                withdraw_SPEC_from_pool_tx = Transaction_class.withdraw_SPEC_from_pool(available_SPEC_LP_token_for_withdrawal)
                                withdraw_SPEC_from_pool_tx_status = Queries_class.get_status_of_tx(withdraw_SPEC_from_pool_tx)
                                if withdraw_SPEC_from_pool_tx_status == True:
                                    default_logger.debug(f'[SPEC LP Withdrawal] Success TX: {withdraw_SPEC_from_pool_tx}')
                                    report_logger.info(f'[SPEC LP Withdrawal] SPEC & UST have been withdrawn from the LP.')
                                    # Mark for sell
                                    action_dict['SPEC'] = 'sell'
                                    # Update UST balance in wallet
                                    wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                else:
                                    report_logger.warning(f'[SPEC LP Withdrawal] Failed TX: {withdraw_SPEC_from_pool_tx}.\n'
                                                        f'[SPEC LP Withdrawal] Reason: {withdraw_SPEC_from_pool_tx_status}')
                                    cooldowns['withdraw_SPEC_from_pool'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                            else:
                                default_logger.debug(f'[SPEC LP Withdrawal] Skipped because withdrawable LP token value ({(value_of_SPEC_LP_token.__float__()/1000000):.2f}) below limit ({config.SPEC_min_total_value}).')
                        else:
                            default_logger.debug(f'[SPEC LP Withdrawal] Skipped because no withdrawable LP token ({(available_SPEC_LP_token_for_withdrawal.__float__()/1000000):.0f}).')
                    else:
                        default_logger.debug(f'[SPEC LP Withdrawal] Skipped because minimum price of SPEC ({config.SPEC_min_price}) not exceeded ({(all_rates["SPEC"].__float__()/1000000):.2f}).')
                else:
                    report_logger.warning(f'[SPEC LP Withdrawal] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                    return False
            else:
                default_logger.debug(f'[SPEC LP Withdrawal] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["withdraw_SPEC_from_pool"]}).')
        else:
            default_logger.debug(f'[SPEC LP Withdrawal] Skipped because disabled by config ({config.SPEC_withdraw_and_sell_if_min_price_is_reached}).')


        # Check if the this section for the token is enabled
        if config.ANC_withdraw_and_sell_if_min_price_is_reached:
            if cooldowns.get('withdraw_ANC_from_pool') is None or cooldowns['withdraw_ANC_from_pool'] <= datetime_now:
                # Check if there is enough UST balance in the wallet to pay the transaction fees
                if wallet_balance['uusd'] > general_estimated_tx_fee:
                    available_ANC_LP_token_for_withdrawal = Queries_class.get_available_LP_token_for_withdrawal(Terra_class.anchorFarm, Terra_class.ANC_token)
                    value_of_ANC_LP_token = all_rates['ANC-TOKEN-PER-SHARE'] * available_ANC_LP_token_for_withdrawal * all_rates['ANC']/1000000 \
                                            + all_rates['ANC-UST-PER-SHARE'] * available_ANC_LP_token_for_withdrawal
                    # Check if the min_price for the token has been matched
                    if (all_rates['ANC']/1000000) > config.ANC_min_price:
                        # Check if there are any LP for that token available
                        if available_ANC_LP_token_for_withdrawal > 0:
                            # Check if the min_withdrawal_limit is exceeded
                            if (value_of_ANC_LP_token/1000000) > config.ANC_min_total_value:
                                # Unstake / withdrawn LP
                                withdraw_ANC_from_pool_tx = Transaction_class.withdraw_ANC_from_pool(available_ANC_LP_token_for_withdrawal)
                                withdraw_ANC_from_pool_tx_status = Queries_class.get_status_of_tx(withdraw_ANC_from_pool_tx)
                                if withdraw_ANC_from_pool_tx_status == True:
                                    default_logger.debug(f'[ANC LP Withdrawal] Success TX: {withdraw_ANC_from_pool_tx}')
                                    report_logger.info(f'[ANC LP Withdrawal] ANC & UST have been withdrawn from the LP.')
                                    # Mark for sell
                                    action_dict['ANC'] = 'sell'
                                    # Update UST balance in wallet
                                    wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                else:
                                    report_logger.warning(f'[ANC LP Withdrawal] Failed TX: {withdraw_ANC_from_pool_tx}.\n'
                                                        f'[ANC LP Withdrawal] Reason: {withdraw_ANC_from_pool_tx_status}')
                                    cooldowns['withdraw_ANC_from_pool'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                            else:
                                default_logger.debug(f'[ANC LP Withdrawal] Skipped because withdrawable LP token value ({(value_of_ANC_LP_token.__float__()/1000000):.2f}) below limit ({config.ANC_min_total_value}).')
                        else:
                            default_logger.debug(f'[ANC LP Withdrawal] Skipped because no withdrawable LP token ({(available_ANC_LP_token_for_withdrawal.__float__()/1000000):.0f}).')
                    else:
                        default_logger.debug(f'[ANC LP Withdrawal] Skipped because minimum price of ANC ({config.ANC_min_price}) not exceeded ({(all_rates["ANC"].__float__()/1000000):.2f}).')
                else:
                    report_logger.warning(f'[ANC LP Withdrawal] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                    return False
            else:
                default_logger.debug(f'[ANC LP Withdrawal] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["withdraw_ANC_from_pool"]}).')
        else:
            default_logger.debug(f'[ANC LP Withdrawal] Skipped because disabled by config ({config.ANC_withdraw_and_sell_if_min_price_is_reached}).')


        # default_logger.debug(f'------------------------------------------\n'
        #                     f'------------- CLAIM SECTION --------------\n'
        #                     f'------------------------------------------\n')

        # Mirror: Claim MIR
        # Check if this section is enabled
        if config.MIR_claim_and_sell_token or config.MIR_claim_and_deposit_in_LP:
            if cooldowns.get('claim_MIR') is None or cooldowns['claim_MIR'] <= datetime_now:
                # Check if there is enough UST balance in the wallet to pay the transaction fees
                if wallet_balance['uusd'] > general_estimated_tx_fee:
                    claimable_MIR = Queries_class.get_claimable_MIR()
                    # Check if there is any token claimable
                    if claimable_MIR > 0:
                        value_of_MIR_claim = Queries_class.simulate_Token_Swap(claimable_MIR, Terra_class.Mirror_MIR_UST_Pair, Terra_class.MIR_token)
                        # Check if the amount claimable is bigger than the min_amount
                        if (value_of_MIR_claim/1000000) >= config.MIR_min_total_value:
                            # Check if the min_price for a sale has been matched
                            if config.MIR_claim_and_sell_token and (all_rates['MIR']/1000000) >= config.MIR_min_price:
                                # Claim MIR
                                claim_MIR_tx = Transaction_class.claim_MIR()
                                claim_MIR_tx_status = Queries_class.get_status_of_tx(claim_MIR_tx)
                                if claim_MIR_tx_status == True:
                                    default_logger.debug(f'[MIR Claim] Success TX: {claim_MIR_tx}')
                                    report_logger.info(f'[MIR Claim] {(claimable_MIR.__float__()/1000000):.2f} MIR have been claimed to be sold.')
                                    # Mark for sale
                                    action_dict['MIR'] = 'sell'
                                    # Update UST balance in wallet
                                    wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                else:
                                    report_logger.warning(f'[MIR Claim] Failed TX: {claim_MIR_tx}.\n'
                                                        f'[MIR Claim] Reason: {claim_MIR_tx_status}')
                                    cooldowns['claim_MIR'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                            
                            # Check if deposit is enabled
                            elif config.MIR_claim_and_deposit_in_LP:
                                # Check if enough UST is available to actually deposit it later
                                UST_to_be_deposited_with_MIR = claimable_MIR * (all_rates['MIR']/1000000 + tax_rate)
                                if wallet_balance['uusd'] > UST_to_be_deposited_with_MIR:
                                    # Claim and mark for deposit
                                    claim_MIR_tx = Transaction_class.claim_MIR()
                                    claim_MIR_tx_status = Queries_class.get_status_of_tx(claim_MIR_tx)
                                    if claim_MIR_tx_status == True:
                                        default_logger.debug(f'[MIR Claim] Success TX: {claim_MIR_tx}')
                                        # Mark for deposit
                                        action_dict['MIR'] = 'deposit'
                                        report_logger.info(f'[MIR Claim] {(claimable_MIR.__float__()/1000000):.2f} MIR have been claimed to be deposited.')
                                        # Update UST balance in wallet
                                        wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                    else:
                                        report_logger.warning(f'[MIR Claim] Failed TX: {claim_MIR_tx}.\n'
                                                        f'[MIR Claim] Reason: {claim_MIR_tx_status}')
                                        cooldowns['claim_MIR'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                # Not enough UST in the wallet to deposit later. Check if allowed to take from Anchor Earn.
                                elif config.Anchor_enable_withdraw_from_Anchor_Earn_to_deposit_in_LP:
                                    # Check if enough in Anchor Earn to withdraw
                                    if (wallet_balance['aUST'] * all_rates['aUST']/1000000 + wallet_balance['uusd']) > UST_to_be_deposited_with_MIR:
                                        # Withdraw from Anchor Earn
                                        claim_Anchor_withdraw_UST_from_Earn_tx = Transaction_class.Anchor_withdraw_UST_from_Earn(UST_to_be_deposited_with_MIR - wallet_balance['uusd'], 'uusd')
                                        claim_Anchor_withdraw_UST_from_Earn_tx_status = Queries_class.get_status_of_tx(claim_Anchor_withdraw_UST_from_Earn_tx)
                                        if claim_Anchor_withdraw_UST_from_Earn_tx_status:
                                            # ! This can result in a withdraw from Anchor Earn three times (MIR, SPEC, ANC) if you balance is not enough. There is no cumulated withdraw.
                                            report_logger.info(f'[MIR Claim] No enought UST balance to depoit later with MIR, so {(UST_to_be_deposited_with_MIR.__float__()/1000000 - wallet_balance["uusd"].__float__()/1000000):.2f} UST have been withdrawn to be deposited later with.')
                                            # Claim and mark for deposit
                                            claim_MIR_tx = Transaction_class.claim_MIR()
                                            claim_MIR_tx_status = Queries_class.get_status_of_tx(claim_MIR_tx)
                                            if claim_MIR_tx_status == True:
                                                default_logger.debug(f'[MIR Claim] Success TX: {claim_MIR_tx}')
                                                # Mark for deposit
                                                action_dict['MIR'] = 'deposit'
                                                report_logger.info(f'[MIR Claim] {(claimable_MIR.__float__()/1000000):.2f} MIR have been claimed to be deposited.')
                                                # Update UST balance in wallet
                                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                            else:
                                                report_logger.warning(f'[MIR Claim] Failed TX: {claim_MIR_tx}.\n'
                                                                f'[MIR Claim] Reason: {claim_MIR_tx_status}')
                                                cooldowns['claim_MIR'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                        else:
                                            report_logger.warning(f'[MIR Claim] Failed TX: {claim_Anchor_withdraw_UST_from_Earn_tx}.\n'
                                                    f'[MIR Claim] Reason: {claim_Anchor_withdraw_UST_from_Earn_tx_status}')
                                            cooldowns['Anchor_withdraw_UST_from_Earn'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                    else:
                                        report_logger.warning(f'[MIR Claim] Skipped because not enough UST/aUST ({(wallet_balance["uusd"].__float__() / 1000000):.2f})/({(wallet_balance["aUST"].__float__() / 1000000):.2f} in wallet to be deposited with MIR later.')
                                else:
                                    report_logger.warning(f'[MIR Claim] Skipped because not enough UST ({(wallet_balance["uusd"].__float__() / 1000000):.2f}) in wallet to be deposited with MIR later and not enabled to withdraw from Anchor Earn ({config.Anchor_enable_withdraw_from_Anchor_Earn_to_deposit_in_LP}).')
                            else:
                                default_logger.debug(f'[MIR Claim] Minimum price ({config.MIR_min_price}) not exceeded for sale ({(all_rates["MIR"].__float__()/1000000):.2f}) and a deposit is not enabled ({config.MIR_claim_and_deposit_in_LP}).')
                        else:
                            default_logger.debug(f'[MIR Claim] Skipped because claimable MIR value ({(value_of_MIR_claim.__float__()/1000000):.2f}) below limit ({config.MIR_min_total_value}).')
                    else:
                        default_logger.debug(f'[MIR Claim] Skipped because no claimable MIR ({(claimable_MIR.__float__()/1000000):.0f}).')
                else:
                    report_logger.warning(f'[MIR Claim] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                    return False
            else:
                default_logger.debug(f'[MIR Claim] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["claim_MIR"]}).')
        else:
            default_logger.debug(f'[MIR Claim] Skipped because disabled by config ({config.MIR_claim_and_sell_token}).')


        # Spectrum: Claim SPEC
        # Check if this section is enabled
        if config.SPEC_claim_and_sell_token or config.SPEC_claim_and_deposit_in_LP:
            if cooldowns.get('claim_SPEC') is None or cooldowns['claim_SPEC'] <= datetime_now:
                # Check if there is enough UST balance in the wallet to pay the transaction fees
                if wallet_balance['uusd'] > general_estimated_tx_fee:
                    claimable_SPEC_list = await Queries_class.get_claimable_SPEC()
                    claimable_SPEC = claimable_SPEC_list[0]
                    # Check if there is any token claimable
                    if claimable_SPEC > 0:
                        value_of_SPEC_claim = Queries_class.simulate_Token_Swap(claimable_SPEC, Terra_class.Spectrum_SPEC_UST_Pair, Terra_class.SPEC_token)
                        # Check if the amount claimable is bigger than the min_amount
                        if (value_of_SPEC_claim/1000000) >= config.SPEC_min_total_value:
                            # Check if the min_price for a sale has been matched
                            if config.SPEC_claim_and_sell_token and (all_rates['SPEC']/1000000) >= config.SPEC_min_price:
                                # Claim SPEC
                                claim_SPEC_tx = Transaction_class.claim_SPEC(claimable_SPEC_list)
                                claim_SPEC_tx_status = Queries_class.get_status_of_tx(claim_SPEC_tx)
                                if claim_SPEC_tx_status == True:
                                    default_logger.debug(f'[SPEC Claim] Success TX: {claim_SPEC_tx}')
                                    report_logger.info(f'[SPEC Claim] {(claimable_SPEC.__float__()/1000000):.2f} SPEC have been claimed to be sold.')
                                    # Mark for sale
                                    action_dict['SPEC'] = 'sell'
                                    # Update UST balance in wallet
                                    wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                else:
                                    report_logger.warning(f'[SPEC Claim] Failed TX: {claim_SPEC_tx}.\n'
                                                        f'[SPEC Claim] Reason: {claim_SPEC_tx_status}')
                                    cooldowns['claim_SPEC'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                            # Check if deposit is enabled
                            elif config.SPEC_claim_and_deposit_in_LP:
                                # Check if enough UST is available to actually deposit it later
                                UST_to_be_deposited_with_SPEC = claimable_SPEC * (all_rates['SPEC']/1000000 + tax_rate)
                                if wallet_balance['uusd'] > UST_to_be_deposited_with_SPEC:
                                    # Claim and mark for deposit
                                    claim_SPEC_tx = Transaction_class.claim_SPEC(claimable_SPEC_list)
                                    claim_SPEC_tx_status = Queries_class.get_status_of_tx(claim_SPEC_tx)
                                    if claim_SPEC_tx_status == True:
                                        default_logger.debug(f'[SPEC Claim] Success TX: {claim_SPEC_tx}')
                                        # Mark for deposit
                                        action_dict['SPEC'] = 'deposit'
                                        report_logger.info(f'[SPEC Claim] {(claimable_SPEC.__float__()/1000000):.2f} SPEC have been claimed to be deposited.')
                                        # Update UST balance in wallet
                                        wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                    else:
                                        report_logger.warning(f'[SPEC Claim] Failed TX: {claim_SPEC_tx}.\n'
                                                        f'[SPEC Claim] Reason: {claim_SPEC_tx_status}')
                                        cooldowns['claim_SPEC'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                # Not enough UST in the wallet to deposit later. Check if allowed to take from Anchor Earn.
                                elif config.Anchor_enable_withdraw_from_Anchor_Earn_to_deposit_in_LP:
                                    # Check if enough in Anchor Earn to withdraw
                                    if (wallet_balance['aUST'] * all_rates['aUST']/1000000 + wallet_balance['uusd'])> UST_to_be_deposited_with_SPEC:
                                        # Withdraw from Anchor Earn
                                        claim_Anchor_withdraw_UST_from_Earn_tx = Transaction_class.Anchor_withdraw_UST_from_Earn(UST_to_be_deposited_with_SPEC - wallet_balance['uusd'], 'uusd')
                                        claim_Anchor_withdraw_UST_from_Earn_tx_status = Queries_class.get_status_of_tx(claim_Anchor_withdraw_UST_from_Earn_tx)
                                        if claim_Anchor_withdraw_UST_from_Earn_tx_status:
                                            # ! This can result in a withdraw from Anchor Earn three times (MIR, SPEC, ANC) if you balance is not enough. There is no cumulated withdraw.
                                            report_logger.info(f'[SPEC Claim] No enought UST balance to depoit later with SPEC, so {(UST_to_be_deposited_with_SPEC.__float__()/1000000 - wallet_balance["uusd"].__float__()/1000000):.2f} UST have been withdrawn to be deposited later with.')
                                            # Claim and mark for deposit
                                            claim_SPEC_tx = Transaction_class.claim_SPEC(claimable_SPEC_list)
                                            claim_SPEC_tx_status = Queries_class.get_status_of_tx(claim_SPEC_tx)
                                            if claim_SPEC_tx_status == True:
                                                default_logger.debug(f'[SPEC Claim] Success TX: {claim_SPEC_tx}')
                                                # Mark for deposit
                                                action_dict['SPEC'] = 'deposit'
                                                report_logger.info(f'[SPEC Claim] {(claimable_SPEC.__float__()/1000000):.2f} SPEC have been claimed to be deposited.')
                                                # Update UST balance in wallet
                                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                            else:
                                                report_logger.warning(f'[SPEC Claim] Failed TX: {claim_SPEC_tx}.\n'
                                                                f'[SPEC Claim] Reason: {claim_SPEC_tx_status}')
                                                cooldowns['claim_SPEC'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                        else:
                                            report_logger.warning(f'[SPEC Claim] Failed TX: {claim_Anchor_withdraw_UST_from_Earn_tx}.\n'
                                                    f'[SPEC Claim] Reason: {claim_Anchor_withdraw_UST_from_Earn_tx_status}')
                                            cooldowns['Anchor_withdraw_UST_from_Earn'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                    else:
                                        report_logger.warning(f'[SPEC Claim] Skipped because not enough UST/aUST ({(wallet_balance["uusd"].__float__() / 1000000):.2f})/({(wallet_balance["aUST"].__float__() / 1000000):.2f} in wallet to be deposited with SPEC later.')
                                else:
                                    report_logger.warning(f'[SPEC Claim] Skipped because not enough UST ({(wallet_balance["uusd"].__float__() / 1000000):.2f}) in wallet to be deposited with SPEC later and not enabled to withdraw from Anchor Earn ({config.Anchor_enable_withdraw_from_Anchor_Earn_to_deposit_in_LP}).')
                            else:
                                default_logger.debug(f'[SPEC Claim] Minimum price ({config.SPEC_min_price}) not exceeded for sale ({(all_rates["SPEC"].__float__()/1000000):.2f}) and a deposit is not enabled ({config.SPEC_claim_and_deposit_in_LP}).')
                        else:
                            default_logger.debug(f'[SPEC Claim] Skipped because claimable SPEC value ({(value_of_SPEC_claim.__float__()/1000000):.2f}) below limit ({config.SPEC_min_total_value}).')
                    else:
                        default_logger.debug(f'[SPEC Claim] Skipped because no claimable SPEC ({(claimable_SPEC.__float__()/1000000):.0f}).')
                else:
                    report_logger.warning(f'[SPEC Claim] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                    return False
            else:
                default_logger.debug(f'[SPEC Claim] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["claim_SPEC"]}).')

        else:
            default_logger.debug(f'[SPEC Claim] Skipped because disabled by config ({config.SPEC_claim_and_sell_token}).')

        # Anchor: Claim ANC
        # Check if this section is enabled
        if config.ANC_claim_and_sell_token or config.ANC_claim_and_deposit_in_LP:
            if cooldowns.get('claim_ANC') is None or cooldowns['claim_ANC'] <= datetime_now:
                # Check if there is enough UST balance in the wallet to pay the transaction fees
                if wallet_balance['uusd'] > general_estimated_tx_fee:
                    claimable_ANC = await Queries_class.get_claimable_ANC()
                    # Check if there is any token claimable
                    if claimable_ANC > 0:
                        value_of_ANC_claim = Queries_class.simulate_Token_Swap(claimable_ANC, Terra_class.Terraswap_ANC_UST_Pair, Terra_class.ANC_token)
                        # Check if the amount claimable is bigger than the min_amount
                        if (value_of_ANC_claim/1000000) >= config.ANC_min_total_value:
                            # Check if the min_price for a sale has been matched
                            if config.ANC_claim_and_sell_token and (all_rates['ANC']/1000000) >= config.ANC_min_price:
                                # Claim ANC
                                claim_ANC_tx = Transaction_class.claim_ANC()
                                claim_ANC_tx_status = Queries_class.get_status_of_tx(claim_ANC_tx)
                                if claim_ANC_tx_status == True:
                                    default_logger.debug(f'[ANC Claim] Success TX: {claim_ANC_tx}')
                                    report_logger.info(f'[ANC Claim] {(claimable_ANC.__float__()/1000000):.2f} ANC have been claimed to be sold.')
                                    # Mark for sale
                                    action_dict['ANC'] = 'sell'
                                    # Update UST balance in wallet
                                    wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                else:
                                    report_logger.warning(f'[ANC Claim] Failed TX: {claim_ANC_tx}.\n'
                                                        f'[ANC Claim] Reason: {claim_ANC_tx_status}')
                                    cooldowns['claim_ANC'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                            # Check if deposit is enabled
                            elif config.ANC_claim_and_deposit_in_LP:
                                # Check if enough UST is available to actually deposit it later
                                UST_to_be_deposited_with_ANC = claimable_ANC * (all_rates['ANC']/1000000 + tax_rate)
                                if wallet_balance['uusd'] > UST_to_be_deposited_with_ANC:
                                    # Claim and mark for deposit
                                    claim_ANC_tx = Transaction_class.claim_ANC()
                                    claim_ANC_tx_status = Queries_class.get_status_of_tx(claim_ANC_tx)
                                    if claim_ANC_tx_status == True:
                                        default_logger.debug(f'[ANC Claim] Success TX: {claim_ANC_tx}')
                                        # Mark for deposit
                                        action_dict['ANC'] = 'deposit'
                                        report_logger.info(f'[ANC Claim] {(claimable_ANC.__float__()/1000000):.2f} ANC have been claimed to be deposited.')
                                        # Update UST balance in wallet
                                        wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                    else:
                                        report_logger.warning(f'[ANC Claim] Failed TX: {claim_ANC_tx}.\n'
                                                        f'[ANC Claim] Reason: {claim_ANC_tx_status}')
                                        cooldowns['claim_ANC'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                # Not enough UST in the wallet to deposit later. Check if allowed to take from Anchor Earn.
                                elif config.Anchor_enable_withdraw_from_Anchor_Earn_to_deposit_in_LP:
                                    # Check if enough in Anchor Earn to withdraw
                                    if (wallet_balance['aUST'] * all_rates['aUST']/1000000 + wallet_balance['uusd']) > UST_to_be_deposited_with_ANC:
                                        # Withdraw from Anchor Earn
                                        claim_Anchor_withdraw_UST_from_Earn_tx = Transaction_class.Anchor_withdraw_UST_from_Earn(UST_to_be_deposited_with_ANC - wallet_balance['uusd'], 'uusd')
                                        claim_Anchor_withdraw_UST_from_Earn_tx_status = Queries_class.get_status_of_tx(claim_Anchor_withdraw_UST_from_Earn_tx)
                                        if claim_Anchor_withdraw_UST_from_Earn_tx_status:
                                            # ! This can result in a withdraw from Anchor Earn three times (MIR, SPEC, ANC) if you balance is not enough. There is no cumulated withdraw.
                                            report_logger.info(f'[ANC Claim] No enought UST balance to depoit later with ANC, so {(UST_to_be_deposited_with_ANC.__float__()/1000000 - wallet_balance["uusd"].__float__()/1000000):.2f} UST have been withdrawn to be deposited later with.')
                                            # Claim and mark for deposit
                                            claim_ANC_tx = Transaction_class.claim_ANC()
                                            claim_ANC_tx_status = Queries_class.get_status_of_tx(claim_ANC_tx)
                                            if claim_ANC_tx_status == True:
                                                default_logger.debug(f'[ANC Claim] Success TX: {claim_ANC_tx}')
                                                # Mark for deposit
                                                action_dict['ANC'] = 'deposit'
                                                report_logger.info(f'[ANC Claim] {(claimable_ANC.__float__()/1000000):.2f} ANC have been claimed to be deposited.')
                                                # Update UST balance in wallet
                                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                            else:
                                                report_logger.warning(f'[ANC Claim] Failed TX: {claim_ANC_tx}.\n'
                                                                f'[ANC Claim] Reason: {claim_ANC_tx_status}')
                                                cooldowns['claim_ANC'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                        else:
                                            report_logger.warning(f'[ANC Claim] Failed TX: {claim_Anchor_withdraw_UST_from_Earn_tx}.\n'
                                                    f'[ANC Claim] Reason: {claim_Anchor_withdraw_UST_from_Earn_tx_status}')
                                            cooldowns['Anchor_withdraw_UST_from_Earn'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                    else:
                                        report_logger.warning(f'[ANC Claim] Skipped because not enough UST/aUST ({(wallet_balance["uusd"].__float__() / 1000000):.2f})/({(wallet_balance["aUST"].__float__() / 1000000):.2f} in wallet to be deposited with ANC later.')
                                else:
                                    report_logger.warning(f'[ANC Claim] Skipped because not enough UST ({(wallet_balance["uusd"].__float__() / 1000000):.2f}) in wallet to be deposited with ANC later and not enabled to withdraw from Anchor Earn ({config.Anchor_enable_withdraw_from_Anchor_Earn_to_deposit_in_LP}).')
                            else:
                                default_logger.debug(f'[ANC Claim] Minimum price ({config.ANC_min_price}) not exceeded for sale ({(all_rates["ANC"].__float__()/1000000):.2f}) and a deposit is not enabled ({config.ANC_claim_and_deposit_in_LP}).')
                        else:
                            default_logger.debug(f'[ANC Claim] Skipped because claimable ANC value ({(value_of_ANC_claim.__float__()/1000000):.2f}) below limit ({config.ANC_min_total_value}).')
                    else:
                        default_logger.debug(f'[ANC Claim] Skipped because no claimable ANC ({(claimable_ANC.__float__()/1000000):.0f}).')
                else:
                    report_logger.warning(f'[ANC Claim] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                    return False
            else:
                default_logger.debug(f'[ANC Claim] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["claim_ANC"]}).')

        else:
            default_logger.debug(f'[ANC Claim] Skipped because disabled by config ({config.ANC_claim_and_sell_token}).')

        # Nexus: Claim PSI
        # Check if this section is enabled
        if config.PSI_claim_and_sell_token or config.PSI_claim_and_deposit_in_LP:
            if cooldowns.get('claim_PSI') is None or cooldowns['claim_PSI'] <= datetime_now:
                # Check if there is enough UST balance in the wallet to pay the transaction fees
                if wallet_balance['uusd'] > general_estimated_tx_fee:
                    claimable_PSI = await Queries_class.get_claimable_PSI()
                    # Check if there is any token claimable
                    if claimable_PSI > 0:
                        value_of_PSI_claim = Queries_class.simulate_Token_Swap(claimable_PSI, Terra_class.Nexus_PSI_UST_Pair, Terra_class.PSI_token)
                        # Check if the amount claimable is bigger than the min_amount
                        if (value_of_PSI_claim/1000000) >= config.PSI_min_total_value:
                            # Check if the min_price for a sale has been matched
                            if config.PSI_claim_and_sell_token and (all_rates['PSI']/1000000) >= config.PSI_min_price:
                                # Claim PSI
                                claim_PSI_tx = Transaction_class.claim_PSI()
                                claim_PSI_tx_status = Queries_class.get_status_of_tx(claim_PSI_tx)
                                if claim_PSI_tx_status == True:
                                    default_logger.debug(f'[PSI Claim] Success TX: {claim_PSI_tx}')
                                    report_logger.info(f'[PSI Claim] {(claimable_PSI.__float__()/1000000):.2f} PSI have been claimed to be sold.')
                                    # Mark for sale
                                    action_dict['PSI'] = 'sell'
                                    # Update UST balance in wallet
                                    wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                else:
                                    report_logger.warning(f'[PSI Claim] Failed TX: {claim_PSI_tx}.\n'
                                                        f'[PSI Claim] Reason: {claim_PSI_tx_status}')
                                    cooldowns['claim_PSI'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                            # Check if deposit is enabled
                            elif config.PSI_claim_and_deposit_in_LP:
                                # Check if enough UST is available to actually deposit it later
                                UST_to_be_deposited_with_PSI = claimable_PSI * (all_rates['PSI']/1000000 + tax_rate)
                                if wallet_balance['uusd'] > UST_to_be_deposited_with_PSI:
                                    # Claim and mark for deposit
                                    claim_PSI_tx = Transaction_class.claim_PSI()
                                    claim_PSI_tx_status = Queries_class.get_status_of_tx(claim_PSI_tx)
                                    if claim_PSI_tx_status == True:
                                        default_logger.debug(f'[PSI Claim] Success TX: {claim_PSI_tx}')
                                        # Mark for deposit
                                        action_dict['PSI'] = 'deposit'
                                        report_logger.info(f'[PSI Claim] {(claimable_PSI.__float__()/1000000):.2f} PSI have been claimed to be deposited.')
                                        # Update UST balance in wallet
                                        wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                    else:
                                        report_logger.warning(f'[PSI Claim] Failed TX: {claim_PSI_tx}.\n'
                                                        f'[PSI Claim] Reason: {claim_PSI_tx_status}')
                                        cooldowns['claim_PSI'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                # Not enough UST in the wallet to deposit later. Check if allowed to take from Anchor Earn.
                                elif config.Anchor_enable_withdraw_from_Anchor_Earn_to_deposit_in_LP:
                                    # Check if enough in Anchor Earn to withdraw
                                    if (wallet_balance['aUST'] * all_rates['aUST']/1000000 + wallet_balance['uusd']) > UST_to_be_deposited_with_PSI:
                                        # Withdraw from Anchor Earn
                                        claim_Anchor_withdraw_UST_from_Earn_tx = Transaction_class.Anchor_withdraw_UST_from_Earn(UST_to_be_deposited_with_PSI - wallet_balance['uusd'], 'uusd')
                                        claim_Anchor_withdraw_UST_from_Earn_tx_status = Queries_class.get_status_of_tx(claim_Anchor_withdraw_UST_from_Earn_tx)
                                        if claim_Anchor_withdraw_UST_from_Earn_tx_status:
                                            # ! This can result in a withdraw from Anchor Earn three times (MIR, SPEC, ANC, PSI) if you balance is not enough. There is no cumulated withdraw.
                                            report_logger.info(f'[PSI Claim] No enought UST balance to depoit later with PSI, so {(UST_to_be_deposited_with_ANC.__float__()/1000000 - wallet_balance["uusd"].__float__()/1000000):.2f} UST have been withdrawn to be deposited later with.')
                                            # Claim and mark for deposit
                                            claim_PSI_tx = Transaction_class.claim_PSI()
                                            claim_PSI_tx_status = Queries_class.get_status_of_tx(claim_PSI_tx)
                                            if claim_PSI_tx_status == True:
                                                default_logger.debug(f'[PSI Claim] Success TX: {claim_PSI_tx}')
                                                # Mark for deposit
                                                action_dict['PSI'] = 'deposit'
                                                report_logger.info(f'[PSI Claim] {(claimable_PSI.__float__()/1000000):.2f} PSI have been claimed to be deposited.')
                                                # Update UST balance in wallet
                                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                                            else:
                                                report_logger.warning(f'[PSI Claim] Failed TX: {claim_PSI_tx}.\n'
                                                                f'[PSI Claim] Reason: {claim_PSI_tx_status}')
                                                cooldowns['claim_PSI'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                        else:
                                            report_logger.warning(f'[PSI Claim] Failed TX: {claim_Anchor_withdraw_UST_from_Earn_tx}.\n'
                                                    f'[PSI Claim] Reason: {claim_Anchor_withdraw_UST_from_Earn_tx_status}')
                                            cooldowns['Anchor_withdraw_UST_from_Earn'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                                    else:
                                        report_logger.warning(f'[PSI Claim] Skipped because not enough UST/aUST ({(wallet_balance["uusd"].__float__() / 1000000):.2f})/({(wallet_balance["aUST"].__float__() / 1000000):.2f} in wallet to be deposited with ANC later.')
                                else:
                                    report_logger.warning(f'[PSI Claim] Skipped because not enough UST ({(wallet_balance["uusd"].__float__() / 1000000):.2f}) in wallet to be deposited with ANC later and not enabled to withdraw from Anchor Earn ({config.Anchor_enable_withdraw_from_Anchor_Earn_to_deposit_in_LP}).')
                            else:
                                default_logger.debug(f'[PSI Claim] Minimum price ({config.PSI_min_price}) not exceeded for sale ({(all_rates["ANC"].__float__()/1000000):.2f}) and a deposit is not enabled ({config.ANC_claim_and_deposit_in_LP}).')
                        else:
                            default_logger.debug(f'[PSI Claim] Skipped because claimable PSI value ({(value_of_PSI_claim.__float__()/1000000):.2f}) below limit ({config.PSI_min_total_value}).')
                    else:
                        default_logger.debug(f'[PSI Claim] Skipped because no claimable PSI ({(claimable_PSI.__float__()/1000000):.0f}).')
                else:
                    report_logger.warning(f'[PSI Claim] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                    return False
            else:
                default_logger.debug(f'[PSI Claim] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["claim_PSI"]}).')

        else:
            default_logger.debug(f'[PSI Claim] Skipped because disabled by config ({config.PSI_claim_and_sell_token}).')

            
        # Mirror: Claim un-locked UST
        # Check if this section is enabled
        if config.Mirror_claim_unlocked_UST:
            if cooldowns.get('Mirror_claim_unlocked_UST') is None or cooldowns['Mirror_claim_unlocked_UST'] <= datetime_now:
                # Check if there is enough UST balance in the wallet to pay the transaction fees
                if wallet_balance['uusd'] > general_estimated_tx_fee:
                    claimable_UST = Queries_class.Mirror_get_claimable_UST(Mirror_position_info)
                    # Check if there is any token claimable
                    if claimable_UST > 0:
                        # Check if the amount claimable is bigger than the min_amount
                        if (claimable_UST/1000000) > config.Mirror_min_amount_UST_to_claim:
                            # Claim UST
                            Mirror_claim_unlocked_UST_tx = Transaction_class.Mirror_claim_unlocked_UST(Mirror_position_info)
                            Mirror_claim_unlocked_UST_tx_status = Queries_class.get_status_of_tx(Mirror_claim_unlocked_UST_tx)
                            if Mirror_claim_unlocked_UST_tx_status == True:
                                default_logger.debug(f'[Mirror Claim UST] Success TX: {Mirror_claim_unlocked_UST_tx}')
                                report_logger.info(f'[Mirror Claim UST] {(claimable_UST.__float__()/1000000):.2f} UST have been claimed from your Mirror Shorts.')
                                # Update UST balance in wallet
                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                            else:
                                report_logger.warning(f'[Mirror Claim UST] Failed TX: {Mirror_claim_unlocked_UST_tx}.\n'
                                                    f'[Mirror Claim UST] Reason: {Mirror_claim_unlocked_UST_tx_status}')
                                cooldowns['Mirror_claim_unlocked_UST'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            default_logger.debug(f'[Mirror Claim UST] Skipped because claimable UST amount ({(claimable_UST.__float__()/1000000):.0f}) below limit ({config.Mirror_min_amount_UST_to_claim}).')
                    else:
                        default_logger.debug(f'[Mirror Claim UST] Skipped because no UST to claim ({(claimable_UST.__float__()/1000000):.0f}).')
                else:
                    report_logger.warning(f'[Mirror Claim UST] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                    return False
            else:
                default_logger.debug(f'[Mirror Claim UST] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["Mirror_claim_unlocked_UST"]}).')
        else:
            default_logger.debug(
                f'[Mirror Claim UST] Skipped because disabled by config ({config.Mirror_claim_unlocked_UST}) or insufficent funds ({(wallet_balance["uusd"].__float__()/1000000 - general_estimated_tx_fee.__float__()/1000000):.2f}).')

        # default_logger.debug(f'---------------------------------------\n'
        #                     f'------------ SELL SECTION -------------\n'
        #                     f'---------------------------------------\n')

        wallet_balance['MIR'], \
        wallet_balance['SPEC'], \
        wallet_balance['ANC'], \
        wallet_balance['PSI'] \
        = await asyncio.gather(
        Queries_class.get_non_native_balance(Terra_class.MIR_token),
        Queries_class.get_non_native_balance(Terra_class.SPEC_token),
        Queries_class.get_non_native_balance(Terra_class.ANC_token),
        Queries_class.get_non_native_balance(Terra_class.PSI_token)
        )


        # Check if section is enabled
        if config.MIR_claim_and_sell_token:
            if cooldowns.get('sell_MIR') is None or cooldowns['sell_MIR'] <= datetime_now:
                if action_dict['MIR'] == 'sell':
                    # Check if there is enough UST balance in the wallet to pay the transaction fees
                    if wallet_balance['uusd'] > general_estimated_tx_fee:
                        # Check if there is any token to sell
                        default_logger.debug(f'[MIR Sell] Updated MIR balance {(wallet_balance["MIR"].__float__()/1000000)}')
                        MIR_to_be_sold = wallet_balance['MIR'] - wallet_balance_before['MIR']
                        if MIR_to_be_sold > 0:
                            # Price and min_value has been checked before therefore sell
                            sell_MIR_tx = Transaction_class.sell_MIR(MIR_to_be_sold)
                            sell_MIR_tx_status = Queries_class.get_status_of_tx(sell_MIR_tx)
                            if sell_MIR_tx_status == True:
                                default_logger.debug(f'[MIR Sell] Success TX: {sell_MIR_tx}')
                                report_logger.info(f'[MIR Sell] {(MIR_to_be_sold.__float__()/1000000):.2f} MIR have been sold for {(MIR_to_be_sold.__float__()/1000000 * all_rates["MIR"].__float__()/1000000):.2f} UST total.')
                                # Update UST balance in wallet
                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                            else:
                                report_logger.warning(f'[MIR Sell] Failed TX: {sell_MIR_tx}.\n'
                                                f'[MIR Sell] Reason: {sell_MIR_tx_status}')
                                cooldowns['sell_MIR'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            default_logger.debug(f'[MIR Sell] Skipped because no MIR ({(MIR_to_be_sold.__float__()/1000000):.0f}) to sell.')
                    else:
                        report_logger.warning(f'[MIR Sell] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                        return False
                else:
                    default_logger.debug(f'[MIR Sell] Skipped because no MIR marked to be sold ({action_dict["MIR"]}).')
            else:
                default_logger.debug(f'[MIR Sell] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["sell_MIR"]}).')
        
        else:
            default_logger.debug(f'[MIR Sell] Skipped because disabled by config ({config.MIR_claim_and_sell_token}).')


        # Check if section is enabled
        if config.SPEC_claim_and_sell_token:
            if cooldowns.get('sell_SPEC') is None or cooldowns['sell_SPEC'] <= datetime_now:
                if action_dict['SPEC'] == 'sell':
                    # Check if there is enough UST balance in the wallet to pay the transaction fees
                    if wallet_balance['uusd'] > general_estimated_tx_fee:
                        # Check if there is any token to sell
                        default_logger.debug(f'[SPEC Sell] Updated SPEC balance {(wallet_balance["SPEC"].__float__()/1000000)}')
                        SPEC_to_be_sold = wallet_balance['SPEC'] - wallet_balance_before['SPEC']
                        if SPEC_to_be_sold > 0:
                            # Price and min_value has been checked before therefore sell
                            sell_SPEC_tx = Transaction_class.sell_SPEC(SPEC_to_be_sold)
                            sell_SPEC_tx_status = Queries_class.get_status_of_tx(sell_SPEC_tx)
                            if sell_SPEC_tx_status == True:
                                default_logger.debug(f'[SPEC Sell] Success TX: {sell_SPEC_tx}')
                                report_logger.info(f'[SPEC Sell] {(SPEC_to_be_sold.__float__()/1000000):.2f} SPEC have been sold for {(SPEC_to_be_sold.__float__() / 1000000 * all_rates["SPEC"].__float__()/1000000):.2f} UST total.')
                                # Update UST balance in wallet
                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                            else:
                                report_logger.warning(f'[SPEC Sell] Failed TX: {sell_SPEC_tx}.\n'
                                                f'[SPEC Sell] Reason: {sell_SPEC_tx_status}')
                                cooldowns['sell_SPEC'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            default_logger.debug(f'[SPEC Sell] Skipped because no SPEC ({(SPEC_to_be_sold.__float__()/1000000):.0f}) to sell.')
                    else:
                        report_logger.warning(f'[SPEC Sell] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                        return False
                else:
                    default_logger.debug(f'[SPEC Sell] Skipped because no SPEC marked to be sold ({action_dict["SPEC"]}).')
            else:
                default_logger.debug(f'[SPEC Sell] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["sell_SPEC"]}).')
        else:
            default_logger.debug(f'[SPEC Sell] Skipped because disabled by config ({config.SPEC_claim_and_sell_token}).')

        # Check if section is enabled
        if config.ANC_claim_and_sell_token:
            if cooldowns.get('sell_ANC') is None or cooldowns['sell_ANC'] <= datetime_now:
                if action_dict['ANC'] == 'sell':
                    # Check if there is enough UST balance in the wallet to pay the transaction fees
                    if wallet_balance['uusd'] > general_estimated_tx_fee:
                        # Check if there is any token to sell
                        default_logger.debug(f'[ANC Sell] Updated ANC balance {(wallet_balance["ANC"].__float__()/1000000)}')
                        ANC_to_be_sold = wallet_balance['ANC'] - wallet_balance_before['ANC']
                        if ANC_to_be_sold > 0:
                            # Price and min_value has been checked before therefore sell
                            sell_ANC_tx = Transaction_class.sell_ANC(ANC_to_be_sold)
                            sell_ANC_tx_status = Queries_class.get_status_of_tx(sell_ANC_tx)
                            if sell_ANC_tx_status == True:
                                default_logger.debug(f'[ANC Sell] Success TX: {sell_ANC_tx}')
                                report_logger.info(f'[ANC Sell] {(ANC_to_be_sold.__float__()/1000000):.2f} ANC have been sold for {(ANC_to_be_sold.__float__()/1000000 * all_rates["ANC"].__float__()/1000000):.2f} UST total.')
                                # Update UST balance in wallet
                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                            else:
                                report_logger.warning(f'[ANC Sell] Failed TX: {sell_ANC_tx}.\n'
                                                f'[ANC Sell] Reason: {sell_ANC_tx_status}')
                                cooldowns['sell_ANC'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            default_logger.debug(f'[ANC Sell] Skipped because no ANC ({(ANC_to_be_sold.__float__()/1000000):.0f}) to sell.')
                    else:
                        report_logger.warning(f'[ANC Sell] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                        return False
                else:
                    default_logger.debug(f'[ANC Sell] Skipped because no ANC marked to be sold ({action_dict["ANC"]}).')
            else:
                default_logger.debug(f'[ANC Sell] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["sell_ANC"]}).')
        else:
            default_logger.debug(f'[ANC Sell] Skipped because disabled by config ({config.ANC_claim_and_sell_token}).')
        

        # Check if section is enabled
        if config.PSI_claim_and_sell_token:
            if cooldowns.get('sell_PSI') is None or cooldowns['sell_PSI'] <= datetime_now:
                if action_dict['PSI'] == 'sell':
                    # Check if there is enough UST balance in the wallet to pay the transaction fees
                    if wallet_balance['uusd'] > general_estimated_tx_fee:
                        # Check if there is any token to sell
                        default_logger.debug(f'[PSI Sell] Updated PSI balance {(wallet_balance["PSI"].__float__()/1000000)}')
                        PSI_to_be_sold = wallet_balance['PSI'] - wallet_balance_before['PSI']
                        if PSI_to_be_sold > 0:
                            # Price and min_value has been checked before therefore sell
                            sell_PSI_tx = Transaction_class.sell_PSI(PSI_to_be_sold)
                            sell_PSI_tx_status = Queries_class.get_status_of_tx(sell_PSI_tx)
                            if sell_PSI_tx_status == True:
                                default_logger.debug(f'[PSI Sell] Success TX: {sell_PSI_tx}')
                                report_logger.info(f'[PSI Sell] {(PSI_to_be_sold.__float__()/1000000):.2f} PSI have been sold for {(PSI_to_be_sold.__float__() / 1000000 * all_rates["PSI"].__float__()/1000000):.2f} UST total.')
                                # Update UST balance in wallet
                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                            else:
                                report_logger.warning(f'[PSI Sell] Failed TX: {sell_PSI_tx}.\n'
                                                f'[PSI Sell] Reason: {sell_PSI_tx_status}')
                                cooldowns['sell_PSI'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            default_logger.debug(f'[PSI Sell] Skipped because no PSI ({(PSI_to_be_sold.__float__()/1000000):.0f}) to sell.')
                    else:
                        report_logger.warning(f'[PSI Sell] Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                        return False
                else:
                    default_logger.debug(f'[PSI Sell] Skipped because no PSI marked to be sold ({action_dict["PSI"]}).')
            else:
                default_logger.debug(f'[PSI Sell] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["sell_PSI"]}).')
        else:
            default_logger.debug(f'[PSI Sell] Skipped because disabled by config ({config.PSI_claim_and_sell_token}).')


        # default_logger.debug(f'------------------------------------------\n'
        #                     f'------------ DEPOSIT SECTION -------------\n'
        #                     f'------------------------------------------\n')   

        # Check if this section is enabled
        if config.MIR_claim_and_deposit_in_LP:
            if cooldowns.get('deposit_MIR_in_pool') is None or cooldowns['deposit_MIR_in_pool'] <= datetime_now:
                if action_dict['MIR'] == 'deposit':
                    # Check if there is enough UST balance in the wallet to pay the transaction fees
                    if wallet_balance['uusd'] > general_estimated_tx_fee:
                        # Check if there is any token to deposit
                        MIR_to_be_deposited = wallet_balance['MIR'] - wallet_balance_before['MIR']
                        if MIR_to_be_deposited > 0:
                            # Price and min_value has been checked before therefore deposit
                            UST_to_be_deposited_with_MIR = MIR_to_be_deposited * (all_rates['MIR']/1000000 + tax_rate)
                            deposit_MIR_tx = Transaction_class.deposit_MIR_in_pool(MIR_to_be_deposited, UST_to_be_deposited_with_MIR)
                            deposit_MIR_tx_status = Queries_class.get_status_of_tx(deposit_MIR_tx)
                            if deposit_MIR_tx_status == True:
                                default_logger.debug(f'[MIR LP Deposit] Success TX: {deposit_MIR_tx}')
                                report_logger.info(f'[MIR LP Deposit] {(MIR_to_be_deposited.__float__()/1000000):.2f} MIR and {(UST_to_be_deposited_with_MIR.__float__()/1000000):.2f} UST have been deposited to LP.')
                                # Update UST balance in wallet
                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                            else:
                                report_logger.warning(f'[MIR LP Deposit] Failed TX: {deposit_MIR_tx}.\n'
                                                f'[MIR LP Deposit] Reason: {deposit_MIR_tx_status}')
                                cooldowns['deposit_MIR_in_pool'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            default_logger.debug(f'[MIR LP Deposit] Skipped because no MIR ({(MIR_to_be_deposited.__float__()/1000000):.0f}) to deposit.')
                    else:
                        report_logger.warning(f'[MIR LP Deposit] YOU NEED TO ACT! Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                        return False
                else:
                    default_logger.debug(f'[MIR LP Deposit] Skipped because no MIR marked to deposited ({action_dict["MIR"]}).')
            else:
                default_logger.debug(f'[MIR LP Deposit] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["deposit_MIR_in_pool"]}).')  
        else:
            default_logger.debug(f'[MIR LP Deposit] Skipped because disabled by config ({config.MIR_claim_and_deposit_in_LP}).')

        # Check if this section is enabled
        if config.SPEC_claim_and_deposit_in_LP:
            if cooldowns.get('deposit_SPEC_in_pool') is None or cooldowns['deposit_SPEC_in_pool'] <= datetime_now:
                if action_dict['SPEC'] == 'deposit':
                    # Check if there is enough UST balance in the wallet to pay the transaction fees
                    if wallet_balance['uusd'] > general_estimated_tx_fee:
                        # Check if there is any token to deposit
                        SPEC_to_be_deposited = wallet_balance['SPEC'] - wallet_balance_before['SPEC']
                        if SPEC_to_be_deposited > 0:
                            # Price and min_value has been checked before therefore deposit
                            UST_to_be_deposited_with_SPEC = SPEC_to_be_deposited * (all_rates['SPEC']/1000000 + tax_rate)
                            deposit_SPEC_tx = Transaction_class.deposit_SPEC_in_pool(SPEC_to_be_deposited, UST_to_be_deposited_with_SPEC)
                            deposit_SPEC_tx_status = Queries_class.get_status_of_tx(deposit_SPEC_tx)
                            if deposit_SPEC_tx_status == True:
                                default_logger.debug(f'[SPEC LP Deposit] Success TX: {deposit_SPEC_tx}')
                                report_logger.info(f'[SPEC LP Deposit] {(SPEC_to_be_deposited.__float__()/1000000):.2f} SPEC and {(UST_to_be_deposited_with_SPEC.__float__()/1000000):.2f} UST have been deposited to LP.')
                                # Update UST balance in wallet
                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                            else:
                                report_logger.warning(f'[SPEC LP Deposit] Failed TX: {deposit_SPEC_tx}.\n'
                                                f'[SPEC LP Deposit] Reason: {deposit_SPEC_tx_status}')
                                cooldowns['deposit_SPEC_in_pool'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            default_logger.debug(f'[SPEC LP Deposit] Skipped because no SPEC ({(SPEC_to_be_deposited.__float__()/1000000):.0f}) to deposit.')
                    else:
                        report_logger.warning(f'[SPEC LP Deposit] YOU NEED TO ACT! Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                        return False
                else:
                    default_logger.debug(f'[SPEC LP Deposit] Skipped because no SPEC marked to deposited ({action_dict["SPEC"]}).')
            else:
                default_logger.debug(f'[SPEC LP Deposit] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["deposit_SPEC_in_pool"]}).')

        else:
            default_logger.debug(f'[SPEC LP Deposit] Skipped because disabled by config ({config.SPEC_claim_and_deposit_in_LP}).')

        # Check if this section is enabled
        if config.ANC_claim_and_deposit_in_LP:
            if cooldowns.get('deposit_ANC_in_pool') is None or cooldowns['deposit_ANC_in_pool'] <= datetime_now:
                if action_dict['ANC'] == 'deposit':
                    # Check if there is enough UST balance in the wallet to pay the transaction fees
                    if wallet_balance['uusd'] > general_estimated_tx_fee:
                        # Check if there is any token to deposit
                        ANC_to_be_deposited = wallet_balance['ANC'] - wallet_balance_before['ANC']
                        if ANC_to_be_deposited > 0:
                            # Price and min_value has been checked before therefore deposit
                            UST_to_be_deposited_with_ANC = ANC_to_be_deposited * (all_rates['ANC']/1000000 + tax_rate)
                            deposit_ANC_tx = Transaction_class.deposit_ANC_in_pool(ANC_to_be_deposited, UST_to_be_deposited_with_ANC)
                            deposit_ANC_tx_status = Queries_class.get_status_of_tx(deposit_ANC_tx)
                            if deposit_ANC_tx_status == True:
                                default_logger.debug(f'[ANC LP Deposit] Success TX: {deposit_ANC_tx}')
                                report_logger.info(f'[ANC LP Deposit] {(ANC_to_be_deposited.__float__()/1000000):.2f} ANC and {(UST_to_be_deposited_with_ANC.__float__()/1000000):.2f} UST have been deposited to LP.')
                                # Update UST balance in wallet
                                wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))
                            else:
                                report_logger.warning(f'[ANC LP Deposit] Failed TX: {deposit_ANC_tx}.\n'
                                                f'[ANC LP Deposit] Reason: {deposit_ANC_tx_status}')
                                cooldowns['deposit_ANC_in_pool'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            default_logger.debug(f'[ANC LP Deposit] Skipped because no ANC ({(ANC_to_be_deposited.__float__()/1000000):.0f}) to deposit.')
                    else:
                        report_logger.warning(f'[ANC LP Deposit] YOU NEED TO ACT! Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                        return False
                else:
                    default_logger.debug(f'[ANC LP Deposit] Skipped because no ANC marked to deposited ({action_dict["ANC"]}).')
            else:
                default_logger.debug(f'[ANC LP Deposit] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["deposit_ANC_in_pool"]}).')
        else:
            default_logger.debug(f'[ANC LP Deposit] Skipped because disabled by config ({config.ANC_claim_and_deposit_in_LP}).')

        # default_logger.debug(f'\n-----------------------------------------------------------\n'
        #                     f'---------- ANCHOR REPAY, BORROW, DEPOSIT SECTION ----------\n'
        #                     f'-----------------------------------------------------------\n')

        if Anchor_borrow_info['borrow_limit'] > 0:
            
            default_logger.debug(f'[Anchor] Anchor_borrow_info: {Prettify_class.dict_value_convert_dec_to_float(Anchor_borrow_info, True)}')

            # Anchor: Repay loan if necesarry and repayment amount bigger than Anchor_min_repay_limit
            Anchor_amount_to_execute_in_ust = Anchor_borrow_info['amount_to_execute_in_ust']
            Anchor_action_to_be_executed = Anchor_borrow_info['action_to_be_executed']
            
            if Anchor_action_to_be_executed == 'none':

                if wallet_balance['uusd'] < general_estimated_tx_fee:
                    report_logger.warning(f'[Anchor] YOU NEED TO ACT! Skipped because insufficent funds ({(wallet_balance["uusd"].__float__() / 1000000):.2f}).')
                    return False
                default_logger.debug(f'[Anchor] Anchor is healthy. Current LTV at {(Anchor_borrow_info["cur_col_ratio"].__float__()*100):.2f} %.')
                
                if not config.Anchor_enable_auto_repay_of_debt:
                    default_logger.debug(f'[Anchor Repay] Skipped because disabled by config ({config.Anchor_enable_auto_repay_of_debt}).')
                if not config.Anchor_enable_auto_borrow_UST:
                    default_logger.debug(f'[Anchor Borrow] Skipped because disabled by config ({config.Anchor_enable_auto_borrow_UST}).')
            

            elif Anchor_action_to_be_executed == 'repay':
                if cooldowns.get('Anchor_repay_debt_UST') is None or cooldowns['Anchor_repay_debt_UST'] <= datetime_now:
                    if Anchor_amount_to_execute_in_ust > config.Anchor_min_repay_limit:
                        # Check if the wallet has enough UST to repay and for tx fees
                        if Anchor_amount_to_execute_in_ust < (wallet_balance['uusd'] - general_estimated_tx_fee):
                            Anchor_repay_debt_UST_tx = Transaction_class.Anchor_repay_debt_UST(Anchor_amount_to_execute_in_ust)
                            Anchor_repay_debt_UST_tx_status = Queries_class.get_status_of_tx(Anchor_repay_debt_UST_tx)
                            if Anchor_repay_debt_UST_tx_status == True:
                                default_logger.debug(f'[Anchor Repay] Success TX: {Anchor_repay_debt_UST_tx}')
                                report_logger.info(f'[Anchor Repay] {(Anchor_amount_to_execute_in_ust.__float__()/1000000):.2f} UST have been repaid to Anchor Borrow from your wallet.')
                            else:
                                report_logger.warning(f'[Anchor Repay] Failed TX: {Anchor_repay_debt_UST_tx}.\n'
                                                    f'[Anchor Repay] Reason: {Anchor_repay_debt_UST_tx_status}')
                                cooldowns['Anchor_repay_debt_UST'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)

                        # Otherwise check if the balance in the wallet + a withdrawl of UST from Anchor Earn would be enough, and withdraw what is needed
                        elif config.Anchor_enable_withdraw_of_deposited_UST \
                                and (wallet_balance['aUST'] * all_rates['aUST']/1000000 + wallet_balance['uusd'] - general_estimated_tx_fee + Dec(config.Anchor_Earn_min_balance_to_keep_in_wallet)* 1000000) >= Anchor_amount_to_execute_in_ust:

                            Amount_to_be_withdrawn = Anchor_amount_to_execute_in_ust - wallet_balance['uusd'] + general_estimated_tx_fee + Dec(config.Anchor_Earn_min_balance_to_keep_in_wallet)* 1000000
                            Anchor_withdraw_UST_from_Earn_tx = Transaction_class.Anchor_withdraw_UST_from_Earn(Amount_to_be_withdrawn, 'uusd')
                            Anchor_withdraw_UST_from_Earn_tx_status = Queries_class.get_status_of_tx(Anchor_withdraw_UST_from_Earn_tx)

                            if Anchor_withdraw_UST_from_Earn_tx_status == True:
                                default_logger.debug(f'[Anchor Withdraw] Success TX: {Anchor_withdraw_UST_from_Earn_tx}')
                                Anchor_repay_debt_UST_tx = Transaction_class.Anchor_repay_debt_UST(Anchor_amount_to_execute_in_ust)
                                Anchor_repay_debt_UST_tx_status = Queries_class.get_status_of_tx(Anchor_repay_debt_UST_tx)
                                if Anchor_repay_debt_UST_tx_status == True:
                                    default_logger.debug(f'[Anchor Withdraw] Success TX: {Anchor_repay_debt_UST_tx}')
                                    report_logger.info(f'[Anchor Withdraw] {(Amount_to_be_withdrawn.__float__()/1000000):.2f} UST have been withdrawn from your Anchor Earn and {(Anchor_amount_to_execute_in_ust.__float__()/1000000):.0f} (incl. UST from your wallet) have been repaid to Anchor Borrow.')
                                else:
                                    report_logger.warning(f'[Anchor Withdraw] Failed TX: {Anchor_repay_debt_UST_tx}.\n'
                                                        f'[Anchor Withdraw] Reason: {Anchor_repay_debt_UST_tx_status}')
                                    cooldowns['Anchor_repay_debt_UST'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                            else:
                                report_logger.warning(f'[Anchor Withdraw] Failed TX: {Anchor_withdraw_UST_from_Earn_tx}.\n'
                                                    f'[Anchor Withdraw] Reason: {Anchor_withdraw_UST_from_Earn_tx_status}')
                                cooldowns['Anchor_withdraw_UST_from_Earn'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)

                        # Otherwise (if allowed) withdraw what is available and repay what is possible if enough tx fees are available
                        elif config.Anchor_enable_partially_repay_if_not_enough_UST_in_wallet \
                                and wallet_balance['uusd'] > general_estimated_tx_fee:

                            Anchor_withdraw_UST_from_Earn_tx = Transaction_class.Anchor_withdraw_UST_from_Earn(wallet_balance['aUST'], 'aUST')
                            Anchor_withdraw_UST_from_Earn_tx_status = Queries_class.get_status_of_tx(Anchor_withdraw_UST_from_Earn_tx)

                            if Anchor_withdraw_UST_from_Earn_tx_status == True:
                                default_logger.debug(f'[Anchor Withdraw] Success TX: {Anchor_withdraw_UST_from_Earn_tx}')
                                Anchor_repay_amount = Queries_class.get_native_balance('uusd') - general_estimated_tx_fee
                                Anchor_repay_debt_UST_tx = Transaction_class.Anchor_repay_debt_UST(Anchor_repay_amount)
                                Anchor_repay_debt_UST_tx_status = Queries_class.get_status_of_tx(Anchor_repay_debt_UST_tx)

                                if Anchor_repay_debt_UST_tx_status == True:
                                    default_logger.debug(f'[Anchor Repay] Success TX: {Anchor_repay_debt_UST_tx}')
                                    report_logger.warning(f'[Anchor Repay] YOU NEED TO ACT! There was not enough availabe aUST to withdraw and not enough UST in your wallet to repay your Anchor Borrow.\n'
                                                        f'{(wallet_balance["aUST"].__float__()/1000000):.2f} aUST has been withdrawn, and combined with your availabe UST in your wallet, {(Anchor_repay_amount.__float__()/1000000):.2f} UST have been repaid to Anchor Borrow.')
                                else:
                                    report_logger.warning(f'[Anchor Repay] Failed TX: {Anchor_repay_debt_UST_tx}.\n'
                                                        f'[Anchor Repay] Reason: {Anchor_repay_debt_UST_tx_status}')
                                    cooldowns['Anchor_repay_debt_UST'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)

                            else:
                                report_logger.warning(f'[Anchor Withdraw] Failed TX: {Anchor_withdraw_UST_from_Earn_tx}.\n'
                                                    f'[Anchor Withdraw] Reason: {Anchor_withdraw_UST_from_Earn_tx_status}')
                                cooldowns['Anchor_withdraw_UST_from_Earn'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            default_logger.debug(f'[Anchor Repay] Skipped because disabled by config Anchor_enable_withdraw_of_deposited_UST({config.Anchor_enable_withdraw_of_deposited_UST}) or\nAnchor_enable_partially_repay_if_not_enough_UST_in_wallet ({config.Anchor_enable_partially_repay_if_not_enough_UST_in_wallet}).')
                    else:
                        default_logger.debug(f'[Anchor Repay] Skipped because repay amount ({(Anchor_amount_to_execute_in_ust.__float__()/1000000):.0f}) below repay limit ({config.Anchor_min_repay_limit}).') 
                else:
                    default_logger.debug(f'[Anchor Repay] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["Anchor_repay_debt_UST"]}).')
            
            # Anchor: Borrow more UST if possible, allowed, big enough and enough balance for tx fees is available
            elif Anchor_action_to_be_executed == 'borrow' \
                    and Anchor_amount_to_execute_in_ust > config.Anchor_min_borrow_limit \
                    and wallet_balance['uusd'] > general_estimated_tx_fee:
                
                if cooldowns.get('Anchor_borrow_more_UST') is None or cooldowns['Anchor_borrow_more_UST'] <= datetime_now:
                    # Check if we are in a cooldown period or if the key actually exists
                    if cooldowns.get('Anchor_borrow_cooldown') is None or cooldowns['Anchor_borrow_cooldown'] <= datetime_now:

                        Anchor_borrow_more_UST_tx = Transaction_class.Anchor_borrow_more_UST(Anchor_amount_to_execute_in_ust)
                        Anchor_borrow_more_UST_tx_status = Queries_class.get_status_of_tx(Anchor_borrow_more_UST_tx)

                        if Anchor_borrow_more_UST_tx_status == True:
                            default_logger.debug(f'[Anchor Borrow] Success TX: {Anchor_borrow_more_UST_tx}')
                            report_logger.info(f'[Anchor Borrow] {Anchor_amount_to_execute_in_ust.__float__():.2f} UST more has been borrowed from Anchor Borrow.')

                            # Cooldown: Write date of today into cooldown dictionary
                            cooldowns['Anchor_borrow_cooldown'] = datetime_now + timedelta(days=config.Anchor_borrow_cooldown)
                            if config.Anchor_borrow_cooldown > 0:
                                report_logger.info(f'[Anchor Borrow] Cooldown limit has been activated. Next Anchor deposit will be possible on {(datetime_now + timedelta(days=config.Anchor_borrow_cooldown)):%Y-%m-%d}.')
                        else:
                            report_logger.warning(f'[Anchor Borrow] Failed TX: {Anchor_borrow_more_UST_tx}.\n'
                                                    f'[Anchor Borrow] Reason: {Anchor_borrow_more_UST_tx_status}')
                            cooldowns['Anchor_borrow_more_UST'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                    else:
                        try:
                            default_logger.debug(f'[Anchor Borrow] Skipped because in cooldown period until ({cooldowns["Anchor_borrow_cooldown"]}).')
                        except:
                            report_logger.warning(f'[Anchor Borrow] Something is wrong with the cooldowns["Anchor_borrow_cooldown"].')
                else:
                    default_logger.debug(f'[Anchor Borrow] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["Anchor_borrow_more_UST"]}).')
            else:
                report_logger.warning(f'[Anchor] Something went wrong while processing the action to execute on Anchor ({Anchor_action_to_be_executed}).')
        else:
            default_logger.debug(f'[Anchor] You do not have any collateral deposited in Anchor. You borrow limit is 0.')

        # Update wallet balances to find out what the delta is
        wallet_balance['uusd'] = Dec(Queries_class.get_native_balance('uusd'))

        # Anchor: Deposit UST from previous claim/sale of reward tokens into Anchor to get more aUST
        if config.Anchor_Earn_enable_deposit_UST:
            if cooldowns.get('Anchor_deposit_UST_for_Earn') is None or cooldowns['Anchor_deposit_UST_for_Earn'] <= datetime_now:
                default_logger.debug(f'[Anchor Deposit] Updated UST balance {(wallet_balance["uusd"].__float__()/1000000):.2f}')

                UST_wallet_difference = wallet_balance['uusd'] - wallet_balance_before['uusd']

                if wallet_balance['uusd'] > (config.Anchor_Earn_min_balance_to_keep_in_wallet * 1000000):
                    UST_to_be_deposited_at_Anchor_Earn = UST_wallet_difference
                else:
                    UST_to_be_deposited_at_Anchor_Earn = UST_wallet_difference - ((config.Anchor_Earn_min_balance_to_keep_in_wallet * 1000000) - wallet_balance['uusd'])
                
                if UST_to_be_deposited_at_Anchor_Earn >= config.Anchor_Earn_min_deposit_amount:
                    Anchor_deposit_UST_for_Earn_tx = Transaction_class.Anchor_deposit_UST_for_Earn(UST_to_be_deposited_at_Anchor_Earn)
                    Anchor_deposit_UST_for_Earn_tx_status = Queries_class.get_status_of_tx(Anchor_deposit_UST_for_Earn_tx)

                    if Anchor_deposit_UST_for_Earn_tx_status == True:
                        default_logger.debug(f'[Anchor Deposit] Success TX: {Anchor_deposit_UST_for_Earn_tx}')
                        report_logger.info(f'[Anchor Deposit] {(UST_to_be_deposited_at_Anchor_Earn.__float__()/1000000):.2f} UST have been deposited to Anchor Earn.')
                    else:
                        report_logger.warning(f'[Anchor Deposit] Failed TX: {Anchor_deposit_UST_for_Earn_tx}.\n'
                                            f'[Anchor Deposit] Reason: {Anchor_deposit_UST_for_Earn_tx_status}')
                        cooldowns['Anchor_deposit_UST_for_Earn'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                else:
                    default_logger.debug(f'[Anchor Deposit] Skipped because deposit amount ({(UST_to_be_deposited_at_Anchor_Earn.__float__()/1000000):.0f}) below deposit limit ({config.Anchor_Earn_min_deposit_amount}) with considered Anchor_Earn_min_balance_to_keep_in_wallet ({config.Anchor_Earn_min_balance_to_keep_in_wallet}).')
            else:
                default_logger.debug(f'[Anchor Deposit] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["Anchor_deposit_UST_for_Earn"]}).')
        else:
            default_logger.debug(f'[Anchor Deposit] Skipped because disabled by config ({config.Anchor_Earn_enable_deposit_UST}).')

        # default_logger.debug(f'\n-------------------------------------------\n'
        #                     f'---------- MIRROR SHORTS SECTION ----------\n'
        #                     f'-------------------------------------------\n')

        default_logger.debug(f'[Mirror] Mirror_position_info: {Prettify_class.dict_value_convert_dec_to_float(Mirror_position_info, True)}')

        for position in Mirror_position_info:
            position_idx = position['position_idx']
            action_to_be_executed = position['action_to_be_executed']

            amount_to_execute_in_ust = position["amount_to_execute_in_ust"]
            amount_to_execute_in_kind = position['amount_to_execute_in_kind']
            collateral_token_denom = position['collateral_token_denom']
            within_market_hours = Queries_class.market_hours()
            # Check if position is marked for a withdraw
            if action_to_be_executed == 'withdraw':
                if cooldowns.get('Mirror_withdraw_collateral_for_position') is None or cooldowns['Mirror_withdraw_collateral_for_position'] <= datetime_now:
                    if within_market_hours:
                        if amount_to_execute_in_ust > config.Mirror_min_withdraw_limit_in_UST:

                            # Check if we are in a cooldown period or if the key actually exists
                            if cooldowns.get(position_idx) is None or cooldowns[position_idx] <= datetime_now:

                                Mirror_withdraw_collateral_for_position_tx = Transaction_class.Mirror_withdraw_collateral_for_position(position_idx, amount_to_execute_in_kind, collateral_token_denom)
                                Mirror_withdraw_collateral_for_position_tx_status = Queries_class.get_status_of_tx(Mirror_withdraw_collateral_for_position_tx)

                                if Mirror_withdraw_collateral_for_position_tx_status == True:
                                    default_logger.debug(
                                        f'[Mirror Shorts Withdraw] Success TX: {Mirror_withdraw_collateral_for_position_tx}')
                                    report_logger.info(
                                        f'[Mirror Shorts] {(amount_to_execute_in_kind.__float__()/1000000):.2f} {collateral_token_denom} with a value of {(amount_to_execute_in_ust.__float__()/1000000):.0f} UST of collateral have been withdrawn from your short position idx {position["position_idx"]} {position["mAsset_symbol"]}.')
                                    
                                    # Cooldown: Write date of today into cooldown dictionary
                                    cooldowns[position_idx] = datetime_now + timedelta(days=config.Mirror_withdraw_cooldown)
                                    if config.Mirror_withdraw_cooldown > 0:
                                        report_logger.info(f'[Mirror Shorts] Cooldown limit has been activated. Next withdraw for short position idx {position["position_idx"]} will be possible on {(datetime_now + timedelta(days=config.Mirror_withdraw_cooldown)):%Y-%m-%d}')
                                else:
                                    report_logger.warning(f'[Mirror Shorts Withdraw] Failed TX: {Mirror_withdraw_collateral_for_position_tx}.\n'
                                                            f'[Mirror Shorts Withdraw] Reason: {Mirror_withdraw_collateral_for_position_tx_status}')
                                    # !: As of know all mirror tx will be blocked. Across all positions.
                                    cooldowns['Mirror_withdraw_collateral_for_position'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                            else:
                                try:
                                    default_logger.debug(f'[Mirror Shorts] Skipped because in cooldown period until ({cooldowns[position_idx]}) for position ({position_idx}).')
                                except:
                                    report_logger.warning(f'[Mirror Shorts] Something is wrong with the cooldowns[position_idx] for position ({position_idx}).')
                        
                        else:
                            default_logger.debug(
                            f'[Mirror Shorts] For position {position_idx} amount to be withdrawn ({(amount_to_execute_in_ust.__float__()/1000000):.0f}) is below limit ({config.Mirror_min_withdraw_limit_in_UST}).')
                    else:
                        report_logger.warning(f'[Mirror Shorts] Withdraw for {position_idx} {position["mAsset_symbol"]} was planned, but NYSE market is not open ({within_market_hours}).')
                else:
                    default_logger.debug(f'[Mirror Shorts Withdraw] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["Mirror_withdraw_collateral_for_position"]}).')

            # Check if position has a deposit pending and if the deposit amount if big enough
            elif action_to_be_executed == 'deposit':
                if cooldowns.get('Mirror_deposit_collateral_for_position') is None or cooldowns['Mirror_deposit_collateral_for_position'] <= datetime_now:
                    if amount_to_execute_in_ust > config.Mirror_min_deposit_limit_in_UST:

                        # Depending on the collateral token required, check if enough balance of the in-kind token is in your wallet
                        # and enough UST for the transaction fee
                        wallet_balance['uusd'] = Queries_class.get_native_balance('uusd')
                        if collateral_token_denom == 'aUST':
                            available_balance = await Queries_class.get_non_native_balance(Terra_class.aUST_token)
                            enough_balance = available_balance >= amount_to_execute_in_kind and wallet_balance['uusd'] > general_estimated_tx_fee
                        elif collateral_token_denom == 'uluna':
                            available_balance = Queries_class.get_native_balance('uluna')
                            enough_balance = available_balance >= amount_to_execute_in_kind and wallet_balance['uusd'] > general_estimated_tx_fee
                        elif collateral_token_denom == 'uusd':
                            available_balance = wallet_balance['uusd']
                            enough_balance = available_balance >= amount_to_execute_in_kind + general_estimated_tx_fee
                        else:
                            default_logger.debug(f'[Mirror Shorts] You discovered a new collateral_token_denom. Congratulations! Please post this as an issue on my Github, so I can fix it. Thank you!')
                    
                        if enough_balance:
                            # If you have enough balance then deposit collateral
                            Mirror_deposit_collateral_for_position_tx = Transaction_class.Mirror_deposit_collateral_for_position(
                                position_idx, amount_to_execute_in_kind, collateral_token_denom)
                            Mirror_deposit_collateral_for_position_tx_status = Queries_class.get_status_of_tx(Mirror_deposit_collateral_for_position_tx)

                            if Mirror_deposit_collateral_for_position_tx_status == True:
                                default_logger.debug(f'[Mirror Shorts Deposit] Success TX: {Mirror_deposit_collateral_for_position_tx}')
                                report_logger.info(f'[Mirror Shorts] {(amount_to_execute_in_kind.__float__()/1000000):.2f} {collateral_token_denom} with a value of {(amount_to_execute_in_ust.__float__()/1000000):.2f} UST of collateral have been deposited to your short position idx {position["position_idx"]}.')
                            else:
                                report_logger.warning(f'[Mirror Shorts Deposit] Failed TX: {Mirror_deposit_collateral_for_position_tx}.\n'
                                                    f'[Mirror Shorts Deposit] Reason: {Mirror_deposit_collateral_for_position_tx_status}')
                                cooldowns['Mirror_deposit_collateral_for_position'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                        else:
                            # If you have NOT enough balance then deposit what is possible
                            Mirror_deposit_collateral_for_position_tx = Transaction_class.Mirror_deposit_collateral_for_position(
                                position_idx, available_balance, collateral_token_denom)
                            Mirror_deposit_collateral_for_position_tx_status = Queries_class.get_status_of_tx(
                                Mirror_deposit_collateral_for_position_tx)

                            if Mirror_deposit_collateral_for_position_tx_status == True:
                                default_logger.debug(f'[Mirror Shorts Deposit] Success TX: {Mirror_deposit_collateral_for_position_tx}')
                                report_logger.warning(f'[Mirror Shorts Deposit] YOU NEED TO ACT! There was not enough availabe {collateral_token_denom} in your wallet to deposit your short position {position_idx} on Mirror.\n'
                                                    f'{(available_balance.__float__()/1000000):.2f} {collateral_token_denom} from your wallet, has been deposited in your short position {position_idx} on Mirror.')
                            else:
                                report_logger.warning(f'[Mirror Shorts Deposit] Failed TX: {Mirror_deposit_collateral_for_position_tx}.\n'
                                                    f'[Mirror Shorts Deposit] Reason: {Mirror_deposit_collateral_for_position_tx_status}')
                                cooldowns['Mirror_deposit_collateral_for_position'] = datetime_now + timedelta(hours=config.Block_failed_transaction_cooldown)
                    else:
                        default_logger.debug(f'[Mirror Shorts] For position {position_idx} amount to be deposited ({(amount_to_execute_in_ust.__float__()/1000000):.0f}) is below limit ({config.Mirror_min_deposit_limit_in_UST}).')
                else:
                    default_logger.debug(f'[Mirror Shorts Deposit] Transaction skipped, since it recently failed. Cooldown until ({cooldowns["Mirror_deposit_collateral_for_position"]}).')
            
            elif action_to_be_executed == 'none':
                default_logger.debug(
                    f'[Mirror Shorts] Position {position_idx} is healthy. Current ratio is {position["cur_col_ratio"].__float__()*100:.0f} %.')
            else:
                report_logger.warning(f'[Mirror Shorts] Something went wrong with position {position_idx} and action {action_to_be_executed}.')
        
        # default_logger.debug(f'\n-----------------------------------------\n'
        #                     f'----------- REPORTING SECTION -----------\n'
        #                     f'-----------------------------------------\n')
        if config.Send_me_a_status_update:
            if cooldowns.get('Staus_Report_cooldown') is None or cooldowns['Staus_Report_cooldown'] <= datetime_now:
                if datetime.strptime(f'{datetime_now:%H:%M}', '%H:%M') > datetime.strptime(config.Status_update_time, '%H:%M'):

                    status_update = Notifications_class.generate_status_report_html(
                        'text',
                        Anchor_borrow_info, Mirror_position_info,
                        claimable_MIR, claimable_SPEC, claimable_ANC, claimable_PSI, claimable_UST,
                        available_MIR_LP_token_for_withdrawal, available_SPEC_LP_token_for_withdrawal, available_ANC_LP_token_for_withdrawal,
                        all_rates)
                    # Notify user about status report
                    if config.Notify_Slack:
                        Notifications_class.slack_webhook(status_update)
                    if config.Notify_Telegram:
                        Notifications_class.telegram_notification(status_update)
                    if config.Notify_Gmail:
                        Notifications_class.gmail_notification(
                            config.Email_format,
                            f'{config.EMAIL_SUBJECT} Status:',
                            Notifications_class.generate_status_report_html(
                                config.Email_format,
                                Anchor_borrow_info, Mirror_position_info,
                                claimable_MIR, claimable_SPEC, claimable_ANC, claimable_PSI, claimable_UST,
                                available_MIR_LP_token_for_withdrawal, available_SPEC_LP_token_for_withdrawal, available_ANC_LP_token_for_withdrawal,
                                all_rates))

                    # Cooldown: Write date of today into cooldown dictionary
                    cooldowns['Staus_Report_cooldown'] = datetime.strptime(f'{date.today()} {config.Status_update_time}', '%Y-%m-%d %H:%M') + timedelta(hours=config.Status_update_frequency)
                    default_logger.debug(f'[Status Update] Cooldown limit has been activated. Next Status Report will be send on {(datetime.strptime(f"{date.today()} {config.Status_update_time}", "%Y-%m-%d %H:%M") + timedelta(hours=config.Status_update_frequency)):%Y-%m-%d %H:%M} server time.')
                else:
                    default_logger.debug(f'[Status Update] Not sent as we are before your desired time ({config.Status_update_time}).')
            else:
                try:
                    default_logger.debug(f'[Status Update] Skipped because in cooldown period until ({cooldowns["Staus_Report_cooldown"]}) or before defined time({config.Status_update_time}).')
                except:
                    report_logger.warning(f'[Status Update] Something is wrong with the cooldowns["Staus_Report_cooldown"].')
        else:
            default_logger.debug(f'[Status Update] Skipped because disabled by config ({config.Send_me_a_status_update}) or Debug Mode is on ({config.Debug_mode}).')

    except Exception:
        report_logger.warning(f'[Script] YOU NEED TO ACT! An error:\n {format_exc(err)}.')
        print(f'[Script] ({datetime.now():%H:%M}) Ran with an error:\n {format_exc(err)}')

        # Write cooldowns to file
        Cooldown_class.write_cooldown(cooldowns)

        # Write all from current report_logger to array
        report_content = report_array.getvalue()

        # Notify user about something that has been done, in this case an error
        if config.Send_me_a_report \
            and len(report_content) > 0:
            if config.Notify_Slack:
                Notifications_class.slack_webhook(report_content)
            if config.Notify_Telegram:
                Notifications_class.telegram_notification(report_content)
            if config.Notify_Gmail:
                Notifications_class.gmail_notification(
                    config.Email_format,
                    f'{config.EMAIL_SUBJECT} Report:',
                    report_content)
        return False

     # Write cooldowns to file
    Cooldown_class.write_cooldown(cooldowns)

    # Write all from current report_logger to array
    report_content = report_array.getvalue()

    # Notify user about something that has been done
    if config.Send_me_a_report \
        and len(report_content) > 0:
        if config.Notify_Slack:
            Notifications_class.slack_webhook(report_content)
        if config.Notify_Telegram:
            Notifications_class.telegram_notification(report_content)
        if config.Notify_Gmail:
            Notifications_class.gmail_notification(
                config.Email_format,
                f'{config.EMAIL_SUBJECT} Report:',
                report_content)
    
    default_logger.info(f'[Script] ({datetime.now():%H:%M} ) Ran successful. Runtime: {(time() - begin_time):.0f}s.')
    print(f'[Script] ({datetime.now():%H:%M}) Ran successfully. Runtime: {(time() - begin_time):.0f}s.')
    return True

if __name__ == '__main__':
    main = asyncio.run(main())
