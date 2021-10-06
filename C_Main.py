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

# Other assets
from assets.Notifications import Notifications
from assets.Queries import Queries
from assets.Transactions import Transaction
from assets.Other import Cooldown
from assets.Logging import Logger
import B_Config as config
 
# Other imports
from datetime import datetime, timedelta
import time

#------------------------------
#---------- INITIATE ----------
#------------------------------

begin_time = time.time()

default_logger = Logger().default_logger
report_logger = Logger().report_logger

report_array = Logger().report_array

datetime_now = datetime.now()
aUST_rate = Queries().get_aUST_rate()
general_estimated_tx_fee = float(Queries().get_fee_estimation()/1e6)

#-------------------------------
#---------- MAIN DEF -----------
#-------------------------------
def keep_safe():
    try:
        Mirror_position_info = Queries().Mirror_get_position_info()
        Anchor_borrow_info = Queries().Anchor_get_borrow_info()
        cooldowns = Cooldown().read_cooldown()
        current_UST_wallet_balance = Queries().get_native_balance('uusd') # is return in humen decimals
        UST_balance_to_be_deposited_at_Anchor_Earn = 0
        status_update = False
        
        # # raise Exception(f'YOU NEED TO ACT! Your wallet balance of {current_UST_wallet_balance:.0f} UST is too low to execute any transaction.')

        if current_UST_wallet_balance < general_estimated_tx_fee:
            default_logger.warning(f'YOU NEED TO ACT! Your wallet balance of {current_UST_wallet_balance:.0f} UST is too low to execute any transaction.')
            return False

        # default_logger.debug(f'------------------------------------------\n'
        #                     f'---------- CLAIM & SELL SECTION ----------\n'
        #                     f'------------------------------------------\n')

        # Mirror: Claim & sell MIR

        if config.MIR_claim_and_sell_token \
                and current_UST_wallet_balance > general_estimated_tx_fee:
            claimable_MIR = Queries().get_claimable_MIR()
            value_of_MIR_claim = Queries().simulate_MIR_Swap(claimable_MIR)
            # ! Balance will not be checked again, if enough UST are available for tx fees
            if value_of_MIR_claim >= config.MIR_min_total_value \
                    and (value_of_MIR_claim/claimable_MIR) >= config.MIR_min_price:
                claim_MIR_tx = Transaction().claim_MIR()
                claim_MIR_tx_status = Queries().get_status_of_tx(claim_MIR_tx)

                if claim_MIR_tx_status == True:
                    default_logger.debug(f'[MIR Claim] Success TX: {claim_MIR_tx}')
                    sell_MIR_tx = Transaction().sell_MIR(claimable_MIR)
                    sell_MIR_tx_status = Queries().get_status_of_tx(sell_MIR_tx)
                    if sell_MIR_tx_status == True:
                        default_logger.debug(f'[MIR Sell] Success TX: {sell_MIR_tx}')
                        report_logger.info(
                            f'[MIR Claim & Sell] {claimable_MIR:.2f} MIR have been claimed and sold for {value_of_MIR_claim:.2f} UST total.')
                        UST_balance_to_be_deposited_at_Anchor_Earn += value_of_MIR_claim
                        default_logger.debug(
                            f'[MIR Claim & Sell] UST balance to be despoited at Anchor Earn: {UST_balance_to_be_deposited_at_Anchor_Earn:.0f} UST.')
                    else:
                        default_logger.warning(f'[MIR Sell] Failed TX: {sell_MIR_tx}.\n'
                                            f'[MIR Sell] Reason: {sell_MIR_tx_status}')
                else:
                    default_logger.warning(f'[MIR Claim] Failed TX: {claim_MIR_tx}.\n'
                                        f'[MIR Claim] Reason: {claim_MIR_tx_status}')
            else:
                default_logger.debug(
                    f'[MIR Claim & Sell] Skipped because claimable MIR value ({value_of_MIR_claim:.2f}) below limit ({config.MIR_min_total_value:.0f}) or current MIR price ({Queries().get_MIR_rate():.2f}) below limit ({config.MIR_min_price:.2f}).')
        else:
            default_logger.debug(
                f'[MIR Claim & Sell] Skipped because disabled by config ({config.MIR_claim_and_sell_token}) or insufficent funds ({(current_UST_wallet_balance - general_estimated_tx_fee):.2f}).')

        # Spectrum: Claim & sell SPEC
        if config.SPEC_claim_and_sell_token \
                and current_UST_wallet_balance > general_estimated_tx_fee:
            claimable_SPEC_list = Queries().get_claimable_SPEC()
            claimable_SPEC = claimable_SPEC_list[0]
            value_of_SPEC_claim = Queries().simulate_SPEC_Swap(claimable_SPEC)
            # ! Balance will not be checked again, if enough UST are available for tx fees
            if value_of_SPEC_claim >= config.SPEC_min_total_value \
                    and (value_of_SPEC_claim/claimable_SPEC) >= config.SPEC_min_price:
                claim_SPEC_tx = Transaction().claim_SPEC(claimable_SPEC_list)
                claim_SPEC_tx_status = Queries().get_status_of_tx(claim_SPEC_tx)

                if claim_SPEC_tx_status == True:
                    default_logger.debug(f'[MIR Claim] Success TX: {claim_SPEC_tx}')
                    sell_SPEC_tx = Transaction().sell_SPEC(claimable_SPEC)
                    sell_SPEC_tx_status = Queries().get_status_of_tx(sell_SPEC_tx)
                    if sell_SPEC_tx_status == True:
                        default_logger.debug(f'[MIR Sell] Success TX: {sell_SPEC_tx}')
                        report_logger.info(
                            f'[SPEC Claim & Sell] {claimable_SPEC:.2f} SPEC have been claimed and sold for {value_of_SPEC_claim:.2f} UST total.')
                        UST_balance_to_be_deposited_at_Anchor_Earn += value_of_SPEC_claim
                        default_logger.debug(
                            f'[SPEC Claim & Sell] UST balance to be despoited at Anchor Earn: {UST_balance_to_be_deposited_at_Anchor_Earn:.0f} UST.')
                    else:
                        default_logger.warning(f'[MIR Sell] Failed TX: {sell_SPEC_tx}.\n'
                                            f'[MIR Sell] Reason: {sell_SPEC_tx_status}')
                else:
                    default_logger.warning(f'[MIR Claim] Failed TX: {claim_SPEC_tx}.\n'
                                        f'[MIR Claim] Reason: {claim_SPEC_tx_status}')
            else:
                default_logger.debug(
                    f'[SPEC Claim & Sell] Skipped because claimable SPEC value ({value_of_SPEC_claim:.2f}) below limit ({config.SPEC_min_total_value:.0f}) or current SPEC price ({Queries().get_SPEC_rate():.2f}) below limit ({config.SPEC_min_price:.2f}).')
        else:
            default_logger.debug(
                f'[SPEC Claim & Sell] Skipped because disabled by config ({config.SPEC_claim_and_sell_token}) or insufficent funds ({(current_UST_wallet_balance - general_estimated_tx_fee):.2f}).')

        # Anchor: Claim & sell ANC
        if config.ANC_claim_and_sell_token \
                and current_UST_wallet_balance > general_estimated_tx_fee:
            claimable_ANC = Queries().get_claimable_ANC()
            value_of_ANC_claim = Queries().simulate_ANC_Swap(claimable_ANC)
            # ! Balance will not be checked again, if enough UST are available for tx fees
            if value_of_ANC_claim >= config.ANC_min_total_value \
                    and (value_of_ANC_claim/claimable_ANC) >= config.ANC_min_price:
                claim_ANC_tx = Transaction().claim_ANC()
                claim_ANC_tx_status = Queries().get_status_of_tx(claim_ANC_tx)

                if claim_ANC_tx_status == True:
                    default_logger.debug(f'[ANC Claim] Success TX: {claim_ANC_tx}')
                    sell_ANC_tx = Transaction().sell_ANC(claimable_ANC)
                    sell_ANC_tx_status = Queries().get_status_of_tx(sell_ANC_tx)
                    if sell_ANC_tx_status == True:
                        default_logger.debug(f'[ANC Sell] Success TX: {sell_ANC_tx}')
                        report_logger.info(
                            f'[ANC Claim & Sell] {claimable_ANC:.2f} ANC have been claimed and sold for {value_of_ANC_claim:.2f} UST total.')
                        UST_balance_to_be_deposited_at_Anchor_Earn += value_of_ANC_claim
                        default_logger.debug(
                            f'[ANC Claim & Sell] UST balance to be despoited at Anchor Earn: {UST_balance_to_be_deposited_at_Anchor_Earn:.0f} UST.')
                    else:
                        default_logger.warning(f'[ANC Sell] Failed TX: {sell_ANC_tx}.\n'
                                            f'[ANC Sell] Reason: {sell_ANC_tx_status}')
                else:
                    default_logger.warning(f'[ANC Claim] Failed TX: {claim_ANC_tx}.\n'
                                        f'[ANC Claim] Reason: {claim_ANC_tx_status}')
            else:
                default_logger.debug(
                    f'[ANC Claim & Sell] Skipped because claimable ANC value ({value_of_ANC_claim:.2f}) below limit ({config.ANC_min_total_value:.0f}) or current ANC price ({Queries().get_ANC_rate():.2f}) below limit ({config.ANC_min_price:.2f}).')
        else:
            default_logger.debug(
                f'[ANC Claim & Sell] Skipped because disabled by config ({config.ANC_claim_and_sell_token}) or insufficent funds ({(current_UST_wallet_balance - general_estimated_tx_fee):.2f}).')

        # Mirror: Claim un-locked UST
        if config.Mirror_claim_unlocked_UST \
                and current_UST_wallet_balance > general_estimated_tx_fee:
            claimable_UST = Queries().Mirror_get_claimable_UST(Mirror_position_info)
            # ! Balance will not be checked again, if enough UST are available for tx fees
            if claimable_UST > config.Mirror_min_amount_UST_to_claim:
                Mirror_claim_unlocked_UST_tx = Transaction().Mirror_claim_unlocked_UST(
                    Mirror_position_info)
                Mirror_claim_unlocked_UST_tx_status = Queries().get_status_of_tx(
                    Mirror_claim_unlocked_UST_tx)
                if Mirror_claim_unlocked_UST_tx_status == True:
                    default_logger.debug(
                        f'Success TX: {Mirror_claim_unlocked_UST_tx}')
                    report_logger.info(
                        f'[Mirror Claim UST] {claimable_UST:.2f} UST have been claimed from your shorts on Mirror.')
                    UST_balance_to_be_deposited_at_Anchor_Earn += claimable_UST
                    default_logger.debug(
                        f'[Mirror Claim UST] UST balance to be despoited at Anchor Earn: {UST_balance_to_be_deposited_at_Anchor_Earn:.0f} UST.')
                else:
                    default_logger.warning(f'[Mirror Claim UST] Failed TX: {Mirror_claim_unlocked_UST_tx}.\n'
                                        f'[Mirror Claim UST] Reason: {Mirror_claim_unlocked_UST_tx_status}')
            else:
                default_logger.debug(
                    f'[Mirror Claim UST] Skipped because claimable UST amount ({claimable_UST:.0f}) below limit ({config.Mirror_min_amount_UST_to_claim:.0f}).')
        else:
            default_logger.debug(
                f'[Mirror Claim UST] Skipped because disabled by config ({config.Mirror_claim_unlocked_UST}) or insufficent funds ({(current_UST_wallet_balance - general_estimated_tx_fee):.2f}).')

        # default_logger.debug(f'\n-----------------------------------------------------------\n'
        #                     f'---------- ANCHOR REPAY, BORROW, DEPOSIT SECTION ----------\n'
        #                     f'-----------------------------------------------------------\n')

        default_logger.debug(f'[Anchor] Anchor_borrow_info: {Anchor_borrow_info}')

        # Anchor: Repay loan if necesarry and repayment amount bigger than Anchor_min_repay_limit
        Anchor_amount_to_execute_in_ust = Anchor_borrow_info['amount_to_execute_in_ust']
        Anchor_action_to_be_executed = Anchor_borrow_info['action_to_be_executed']

        # Update the wallet's balance, in case some token have been sold for UST
        current_UST_wallet_balance = Queries().get_native_balance('uusd')
        current_aUST_wallet_balance = Queries().get_aUST_balance()

        if Anchor_action_to_be_executed == 'none':
            default_logger.debug(f'[Anchor] Current LTV at {(Anchor_borrow_info["cur_col_ratio"]*100):.0f} %.')

        if Anchor_action_to_be_executed == 'repay' \
                and Anchor_amount_to_execute_in_ust > config.Anchor_min_repay_limit:

            # Check if the wallet has enough UST to repay and for tx fees
            if Anchor_amount_to_execute_in_ust < (current_UST_wallet_balance - general_estimated_tx_fee):
                Anchor_repay_debt_UST_tx = Transaction().Anchor_repay_debt_UST(
                    Anchor_amount_to_execute_in_ust)
                Anchor_repay_debt_UST_tx_status = Queries().get_status_of_tx(
                    Anchor_repay_debt_UST_tx)
                if Anchor_repay_debt_UST_tx_status == True:
                    default_logger.debug(
                        f'[Anchor Repay] Success TX: {Anchor_repay_debt_UST_tx}')
                    report_logger.info(
                        f'[Anchor Repay] {Anchor_amount_to_execute_in_ust:.2f} UST have been repaid to Anchor Borrow from your wallet.')
                else:
                    default_logger.warning(f'[Anchor Repay] Failed TX: {Anchor_repay_debt_UST_tx}.\n'
                                        f'[Anchor Repay] Reason: {Anchor_repay_debt_UST_tx_status}')

            # Otherwise check if the balance in the wallet + a withdrawl of UST from Anchor Earn would be enough, and withdraw what is needed
            elif config.Anchor_enable_withdraw_of_deposited_UST \
                    and (current_aUST_wallet_balance * aUST_rate + current_UST_wallet_balance - general_estimated_tx_fee) >= Anchor_amount_to_execute_in_ust:

                Amount_to_be_withdrawn = Anchor_amount_to_execute_in_ust - \
                    current_UST_wallet_balance + general_estimated_tx_fee
                Anchor_withdraw_UST_from_Earn_tx = Transaction().Anchor_withdraw_UST_from_Earn(
                    Amount_to_be_withdrawn, 'UST')
                Anchor_withdraw_UST_from_Earn_tx_status = Queries().get_status_of_tx(
                    Anchor_withdraw_UST_from_Earn_tx)

                if Anchor_withdraw_UST_from_Earn_tx_status == True:
                    default_logger.debug(
                        f'[Anchor Withdraw] Success TX: {Anchor_withdraw_UST_from_Earn_tx}')
                    Anchor_repay_debt_UST_tx = Transaction().Anchor_repay_debt_UST(
                        Anchor_amount_to_execute_in_ust)
                    Anchor_repay_debt_UST_tx_status = Queries().get_status_of_tx(
                        Anchor_repay_debt_UST_tx)
                    if Anchor_repay_debt_UST_tx_status == True:
                        default_logger.debug(f'[Anchor Withdraw] Success TX: {Anchor_repay_debt_UST_tx}')
                        report_logger.info(f'[Anchor Withdraw] {Amount_to_be_withdrawn:.2f} UST have been withdrawn from your Anchor Earn and {Anchor_repay_debt_UST_tx} (incl. UST from your wallet) have been repaid to Anchor Borrow.')
                    else:
                        default_logger.warning(f'[Anchor Withdraw] Failed TX: {Anchor_repay_debt_UST_tx}.\n'
                                            f'[Anchor Withdraw] Reason: {Anchor_repay_debt_UST_tx_status}')
                else:
                    default_logger.warning(f'[Anchor Withdraw] Failed TX: {Anchor_withdraw_UST_from_Earn_tx}.\n'
                                        f'[Anchor Withdraw] Reason: {Anchor_withdraw_UST_from_Earn_tx_status}')

            # Otherwise (if allowed) withdraw what is available and repay what is possible if enough tx fees are available
            elif config.Anchor_enable_partially_repay_if_not_enough_UST_in_wallet \
                    and current_UST_wallet_balance > general_estimated_tx_fee:

                Anchor_withdraw_UST_from_Earn_tx = Transaction().Anchor_withdraw_UST_from_Earn(
                    current_aUST_wallet_balance, 'aUST')
                Anchor_withdraw_UST_from_Earn_tx_status = Queries().get_status_of_tx(
                    Anchor_withdraw_UST_from_Earn_tx)

                if Anchor_withdraw_UST_from_Earn_tx_status == True:
                    default_logger.debug(
                        f'[Anchor Withdraw] Success TX: {Anchor_withdraw_UST_from_Earn_tx}')

                    Anchor_repay_debt_UST_tx = Transaction().Anchor_repay_debt_UST(Queries().get_native_balance('uusd') - general_estimated_tx_fee)
                    Anchor_repay_debt_UST_tx_status = Queries().get_status_of_tx(
                        Anchor_repay_debt_UST_tx)

                    if Anchor_repay_debt_UST_tx_status == True:
                        default_logger.debug(
                            f'[Anchor Repay] Success TX: {Anchor_repay_debt_UST_tx}')
                        report_logger.warning(f'[Anchor Repay] YOU NEED TO ACT! There was not enough availabe aUST to withdraw and not enough UST in your wallet to repay your Anchor Borrow.\n'
                                            f'{current_aUST_wallet_balance:.2f} aUST has been withdrawn, and combined with your availabe UST in your wallet, {Anchor_repay_debt_UST_tx:.2f} UST have been repaid to Anchor Borrow.')
                    else:
                        default_logger.warning(f'[Anchor Repay] Failed TX: {Anchor_repay_debt_UST_tx}.\n'
                                            f'[Anchor Repay] Reason: {Anchor_repay_debt_UST_tx_status}')

                else:
                    default_logger.warning(f'[Anchor Withdraw] Failed TX: {Anchor_withdraw_UST_from_Earn_tx}.\n'
                                        f'[Anchor Withdraw] Reason: {Anchor_withdraw_UST_from_Earn_tx_status}')
            else:
                default_logger.debug(
                    f'[Anchor Repay] Skipped because disabled by config Anchor_enable_withdraw_of_deposited_UST({config.Anchor_enable_withdraw_of_deposited_UST}) or\nAnchor_enable_partially_repay_if_not_enough_UST_in_wallet ({config.Anchor_enable_partially_repay_if_not_enough_UST_in_wallet}).')
        else:
            default_logger.debug(
                f'[Anchor Repay] Skipped because disabled by config ({config.Anchor_enable_auto_repay_of_debt}), nothing to repay ({Anchor_action_to_be_executed}) or repay amount ({Anchor_amount_to_execute_in_ust:.0f}) below repay limit ({config.Anchor_min_repay_limit:.0f}).')

        # Anchor: Borrow more UST if possible, allowed, big enough and enough balance for tx fees is available
        if Anchor_action_to_be_executed == 'borrow' \
                and Anchor_amount_to_execute_in_ust > config.Anchor_min_borrow_limit \
                and current_UST_wallet_balance > general_estimated_tx_fee:

            # Check if we are in a cooldown period or if the key actually exists
            if cooldowns.get('Anchor_borrow_cooldown') is None or cooldowns['Anchor_borrow_cooldown'] <= datetime_now:

                Anchor_borrow_more_UST_tx = Transaction().Anchor_borrow_more_UST(
                    Anchor_amount_to_execute_in_ust)
                Anchor_borrow_more_UST_tx_status = Queries().get_status_of_tx(
                    Anchor_borrow_more_UST_tx)

                if Anchor_borrow_more_UST_tx_status == True:
                    default_logger.debug(
                        f'[Anchor Borrow] Success TX: {Anchor_borrow_more_UST_tx}')
                    report_logger.info(
                        f'[Anchor Borrow] {Anchor_amount_to_execute_in_ust:.2f} UST more has been borrowed from Anchor Borrow.')
                    UST_balance_to_be_deposited_at_Anchor_Earn += Anchor_amount_to_execute_in_ust
                    default_logger.debug(
                        f'[Anchor Borrow] UST balance to be despoited at Anchor Earn: {UST_balance_to_be_deposited_at_Anchor_Earn:.0f} UST.')

                    # Cooldown: Write date of today into cooldown dictionary
                    cooldowns['Anchor_borrow_cooldown'] = datetime_now + timedelta(days=config.Anchor_borrow_cooldown)
                    if config.Anchor_borrow_cooldown > 0:
                        report_logger.info(
                            f'[Anchor Borrow] Cooldown limit has been activated. Next Anchor deposit will be possible on {(datetime_now + timedelta(days=config.Anchor_borrow_cooldown)):%Y-%m-%d}.')
                else:
                    default_logger.warning(f'[Anchor Borrow] Failed TX: {Anchor_borrow_more_UST_tx}.\n'
                                            f'[Anchor Borrow] Reason: {Anchor_borrow_more_UST_tx_status}')
            else:
                try:
                    default_logger.debug(f'[Anchor Borrow] Skipped because in cooldown period until ({cooldowns["Anchor_borrow_cooldown"]}).')
                except:
                    default_logger.debug(f'[Anchor Borrow] Something is wrong with the cooldowns["Anchor_borrow_cooldown"].')

        else:
            default_logger.debug(
                f'[Anchor Borrow] Skipped because disabled by config ({config.Anchor_enable_auto_borrow_UST}), nothing to borrow ({Anchor_action_to_be_executed}), borrow amount ({Anchor_amount_to_execute_in_ust:.0f}) below repay limit ({config.Anchor_min_borrow_limit:.0f}) or not enough funds for the transaction ({(current_UST_wallet_balance - general_estimated_tx_fee):.0f}).')

        # Anchor: Deposit UST from previous claim/sale of reward tokens into Anchor to get more aUST
        if config.Anchor_enable_deposit_borrowed_UST \
                and UST_balance_to_be_deposited_at_Anchor_Earn >= config.Anchor_min_deposit_amount:

            Anchor_deposit_UST_for_Earn_tx = Transaction().Anchor_deposit_UST_for_Earn(
                UST_balance_to_be_deposited_at_Anchor_Earn)
            Anchor_deposit_UST_for_Earn_tx_status = Queries().get_status_of_tx(
                Anchor_deposit_UST_for_Earn_tx)

            if Anchor_deposit_UST_for_Earn_tx_status == True:
                default_logger.debug(
                    f'[Anchor Deposit] Success TX: {Anchor_deposit_UST_for_Earn_tx}')
                report_logger.info(
                    f'[Anchor Deposit] {UST_balance_to_be_deposited_at_Anchor_Earn:.2f} UST have been deposited to Anchor Earn.')
            else:
                default_logger.warning(f'[Anchor Deposit] Failed TX: {Anchor_deposit_UST_for_Earn_tx}.\n'
                                    f'[Anchor Deposit] Reason: {Anchor_deposit_UST_for_Earn_tx_status}')
        else:
            default_logger.debug(
                f'[Anchor Deposit] Skipped because disabled by config ({config.Anchor_enable_deposit_borrowed_UST}) or deposit amount ({UST_balance_to_be_deposited_at_Anchor_Earn:.0f}) below deposit limit ({config.Anchor_min_deposit_amount:.0f})')

        # default_logger.debug(f'\n-------------------------------------------\n'
        #                     f'---------- MIRROR SHORTS SECTION ----------\n'
        #                     f'-------------------------------------------\n')

        default_logger.debug(f'[Mirror] Mirror_position_info: {Mirror_position_info}')

        for position in Mirror_position_info:
            position_idx = position['position_idx']
            action_to_be_executed = position['action_to_be_executed']

            amount_to_execute_in_ust = position["amount_to_execute_in_ust"]
            amount_to_execute_in_kind = position['amount_to_execute_in_kind']
            collateral_token_denom = position['collateral_token_denom']
            within_market_hours = Queries().market_hours()
            # Check if position is marked for a withdraw
            if action_to_be_executed == 'withdraw':
                if within_market_hours:
                    if amount_to_execute_in_ust > config.Mirror_min_withdraw_limit_in_UST:

                        # Check if we are in a cooldown period or if the key actually exists
                        if cooldowns.get(position_idx) is None or cooldowns[position_idx] <= datetime_now:

                            Mirror_withdraw_collateral_for_position_tx = Transaction().Mirror_withdraw_collateral_for_position(
                                position_idx, amount_to_execute_in_kind, collateral_token_denom)
                            Mirror_withdraw_collateral_for_position_tx_status = Queries().get_status_of_tx(
                                Mirror_withdraw_collateral_for_position_tx)

                            if Mirror_withdraw_collateral_for_position_tx_status == True:
                                default_logger.debug(
                                    f'[Mirror Shorts Withdraw] Success TX: {Mirror_withdraw_collateral_for_position_tx}')
                                report_logger.info(
                                    f'[Mirror Shorts] {amount_to_execute_in_kind:.2f} {collateral_token_denom} with a value of {amount_to_execute_in_ust:.0f} UST of collateral have been withdrawn from your short position idx {position["position_idx"]}.')
                                
                                # Cooldown: Write date of today into cooldown dictionary
                                cooldowns[position_idx] = datetime_now + timedelta(days=config.Mirror_withdraw_cooldown)
                                if config.Mirror_withdraw_cooldown > 0:
                                    report_logger.info(
                                        f'[Mirror Shorts] Cooldown limit has been activated. Next withdraw for short position idx {position["position_idx"]} will be possible on {(datetime_now + timedelta(days=config.Mirror_withdraw_cooldown)):%Y-%m-%d}')
                            else:
                                default_logger.warning(f'[Mirror Shorts Withdraw] Failed TX: {Mirror_withdraw_collateral_for_position_tx}.\n'
                                                        f'[Mirror Shorts Withdraw] Reason: {Mirror_withdraw_collateral_for_position_tx_status}')
                        else:
                            try:
                                default_logger.debug(f'[Mirror Shorts] Skipped because in cooldown period until ({cooldowns[position_idx]}) for position ({position_idx}).')
                            except:
                                default_logger.debug(f'[Mirror Shorts] Something is wrong with the cooldowns[position_idx] for position ({position_idx}).')
                    
                    else:
                        default_logger.debug(
                        f'[Mirror Shorts] For position {position_idx} amount to be withdrawn ({amount_to_execute_in_ust:.0f}) is below limit ({config.Mirror_min_withdraw_limit_in_UST:.0f}).')
                else:
                    default_logger.warning(f'[Mirror Shorts] Withdraw was planned, but NYSE market is not open ({within_market_hours}).')

            # Check if position has a deposit pending and if the deposit amount if big enough
            elif action_to_be_executed == 'deposit':
                if amount_to_execute_in_ust > config.Mirror_min_deposit_limit_in_ust:

                    # Depending on the collateral token required, check if enough balance of the in-kind token is in your wallet
                    # and enough UST for the transaction fee
                    current_UST_wallet_balance = Queries().get_native_balance('uusd')
                    if collateral_token_denom == 'aUST':
                        available_balance = Queries().get_aUST_balance()
                        enough_balance = available_balance >= amount_to_execute_in_kind and current_UST_wallet_balance > general_estimated_tx_fee
                    elif collateral_token_denom == 'uluna':
                        available_balance = Queries().get_native_balance(
                            collateral_token_denom)
                        enough_balance = available_balance >= amount_to_execute_in_kind and current_UST_wallet_balance > general_estimated_tx_fee
                    elif collateral_token_denom == 'uusd':
                        available_balance = current_UST_wallet_balance
                        enough_balance = available_balance >= amount_to_execute_in_kind + general_estimated_tx_fee
                    else:
                        default_logger.debug(
                            f'[Mirror Shorts] You discovered a new collateral_token_denom. Congratulations! Please post this as an issue on my Github, so I can fix it. Thank you!')
                
                    if enough_balance:
                        # If you have enough balance then deposit collateral
                        Mirror_deposit_collateral_for_position_tx = Transaction().Mirror_deposit_collateral_for_position(
                            position_idx, amount_to_execute_in_kind, collateral_token_denom)
                        Mirror_deposit_collateral_for_position_tx_status = Queries().get_status_of_tx(Mirror_deposit_collateral_for_position_tx)

                        if Mirror_deposit_collateral_for_position_tx_status == True:
                            default_logger.debug(
                                f'[Mirror Shorts Deposit] Success TX: {Mirror_deposit_collateral_for_position_tx}')
                            report_logger.info(
                                f'[Mirror Shorts] {amount_to_execute_in_kind:.2f} {collateral_token_denom:.2f} with a value of {amount_to_execute_in_ust:.2f} UST of collateral have been deposited to your short position idx {position["position_idx"]}.')
                        else:
                            default_logger.warning(f'[Mirror Shorts Deposit] Failed TX: {Mirror_deposit_collateral_for_position_tx}.\n'
                                                f'[Mirror Shorts Deposit] Reason: {Mirror_deposit_collateral_for_position_tx_status}')
                    else:
                        # If you have NOT enough balance then deposit what is possible
                        Mirror_deposit_collateral_for_position_tx = Transaction().Mirror_deposit_collateral_for_position(
                            position_idx, available_balance, collateral_token_denom)
                        Mirror_deposit_collateral_for_position_tx_status = Queries().get_status_of_tx(
                            Mirror_deposit_collateral_for_position_tx)

                        if Mirror_deposit_collateral_for_position_tx_status == True:
                            default_logger.debug(
                                f'[Mirror Shorts Deposit] Success TX: {Mirror_deposit_collateral_for_position_tx}')
                            report_logger.warning(f'YOU NEED TO ACT! There was not enough availabe {collateral_token_denom:.2f} in your wallet to deposit your short position {position_idx} on Mirror.\n'
                                                f'{available_balance:.2f} {collateral_token_denom:.2f} from your wallet, has been deposited in your short position {position_idx} on Mirror.')
                        else:
                            default_logger.warning(f'[Mirror Shorts Deposit] Failed TX: {Mirror_deposit_collateral_for_position_tx}.\n'
                                                f'[Mirror Shorts Deposit] Reason: {Mirror_deposit_collateral_for_position_tx_status}')
                else:
                    default_logger.debug(f'[Mirror Shorts] For position {position_idx} amount to be deposited ({amount_to_execute_in_ust:.0f}) is below limit ({config.Mirror_min_deposit_limit_in_ust:.0f}).')
            
            elif action_to_be_executed == 'none':
                default_logger.debug(
                    f'[Mirror Shorts] Position {position_idx} is healthy. Current ratio is {position["cur_col_ratio"]:.2f}.')
            else:
                default_logger.warning(f'[Mirror Shorts] Something went wrong with position {position_idx} and action {action_to_be_executed}.')
        
        # default_logger.debug(   f'\n[CONFIG] Mirror_enable_deposit_collateral is set to ({config.Mirror_enable_deposit_collateral})\n'
        #                         f'[CONFIG] Mirror_enable_withdraw_collateral is set to ({config.Mirror_enable_withdraw_collateral})')

        # default_logger.debug(f'\n-----------------------------------------\n'
        #                     f'---------- BUREAUCRACY SECTION ----------\n'
        #                     f'-----------------------------------------\n')

        if config.Send_me_a_status_update:
            if cooldowns.get('Staus_Report_cooldown') is None or cooldowns['Staus_Report_cooldown'] <= datetime_now:
                if datetime.strptime(f'{datetime_now:%H:%M}', '%H:%M') > datetime.strptime(config.Status_update_time, '%H:%M'):

                    status_update = ""

                    if Anchor_borrow_info["loan_amount"] > 0:
                        status_update += f'-----------------------------------\n' \
                                        f'------------- ANCHOR --------------\n' \
                                        f'-----------------------------------\n' \
                                        f'bETH collateral: {Anchor_borrow_info["amount_bETH_collateral"]:.3f} bETH\n' \
                                        f'bLuna collateral: {Anchor_borrow_info["amount_bLuna_collateral"]:.0f} bLuna\n' \
                                        f'Total collateral: {Anchor_borrow_info["total_collateral_value"]:.0f} UST\n' \
                                        f'Loan amount: {Anchor_borrow_info["loan_amount"]:.0f} UST\n' \
                                        f'Borrow limit: {Anchor_borrow_info["borrow_limit"]:.0f} UST\n' \
                                        f'Current LTV: {Anchor_borrow_info["cur_col_ratio"]*100:.0f} %\n' \
                                        f'If all your collateral loses {Anchor_borrow_info["collateral_loss_to_liq"]*100:.0f}% you would get liquidated.\n' \
                                                        
                    if len(Mirror_position_info) > 0:
                        
                        status_update += f'-----------------------------------\n' \
                                        f'------------- MIRROR --------------\n' \
                                        f'-----------------------------------\n' \
                        
                        for position in Mirror_position_info:
                            
                            status_update +=  f'Position: {position["position_idx"]} - {position["mAsset_symbol"]}\n' \
                                                f'Collateral value: {position["collateral_amount_in_kind"]:.0f} {position["collateral_token_denom"]}\n' \
                                                f'Collateral value: {position["collateral_amount_in_ust"]:.0f} UST\n' \
                                                f'Shorted Value in UST: {position["shorted_asset_amount"]:.0f} UST\n' \
                                                f'Current LTV: {position["cur_col_ratio"]:.0f}00 %\n' \
                                                f'If all your collateral loses {(position["collateral_loss_to_liq"]*100):.0f}%\n' \
                                                f'or if {position["mAsset_symbol"]} raises by {(position["shorted_mAsset_gain_to_liq"]*100):.0f}% you would get liquidated.\n' \
                                                f'\n'

                    # Cooldown: Write date of today into cooldown dictionary
                    cooldowns['Staus_Report_cooldown'] = datetime_now + timedelta(hours=config.Status_update_frequency)
                    report_logger.info(f'[Status Update] Cooldown limit has been activated. Next Status Report will be send on {(datetime_now + timedelta(hours=config.Status_update_frequency)):%Y-%m-%d %H:%M}')
                else:
                    default_logger.debug(f'[Status Update] Not sent as we are before your desired time ({config.Status_update_time}).')
            else:
                try:
                    default_logger.debug(f'[Status Update] Skipped because in cooldown period until ({cooldowns["Staus_Report_cooldown"]}) or before defined time({config.Status_update_time}).')
                except:
                    default_logger.debug(f'[Status Update] Something is wrong with the cooldowns["Staus_Report_cooldown"].')
        else:
            default_logger.debug(f'[Status Update] Skipped because disabled by config ({config.Send_me_a_status_update}) or Debug Mode is on ({config.Debug_mode}).')

        
    except:
        # Todo Exception handling
        print("An exception just happended")
        default_logger.warning("An exception just happended")

    # Write cooldowns to file
    Cooldown().write_cooldown(cooldowns)
    
    # Write all from current report_logger to array
    report_content = report_array.getvalue()

    # Notify user about something that has been done
    if config.Send_me_a_report \
        and len(report_content) > 0:
        if config.Notify_Slack:
            Notifications.slack_webhook(report_content)
        if config.Notify_Telegram:
            Notifications.telegram_notification(report_content)
        if config.Notify_Gmail:
            Notifications.gmail_notification(f'{config.EMAIL_SUBJECT} Report:', report_content)
    
    # Notify user about status report
    if status_update != False:
        if config.Notify_Slack:
            Notifications.slack_webhook(status_update)
        if config.Notify_Telegram:
            Notifications.telegram_notification(status_update)
        if config.Notify_Gmail:
            Notifications.gmail_notification(f'{config.EMAIL_SUBJECT} Status:', status_update)

    default_logger.debug(f'{datetime.now():%H:%M} [Script] Run successful. Runtime: {(time.time() - begin_time):.0f}s')
    print(f'[Script] At {datetime.now():%H:%M}, ran successfully. Runtime: {(time.time() - begin_time):.0f}s')
    return True

if __name__ == '__main__':
    keep_safe = keep_safe()