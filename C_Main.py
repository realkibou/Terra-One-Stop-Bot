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

from terra_sdk.client.lcd import LCDClient
from terra_sdk.key.mnemonic import MnemonicKey
from terra_sdk.core.coins import Coins
from terra_sdk.core.coins import Coin
from terra_sdk.core.auth import StdFee
from terra_sdk.core.wasm import MsgExecuteContract
from terra_sdk.exceptions import LCDResponseError

import B_Logging_config as logging_config
from B_Contact_addresses import contact_addresses, rev_contact_addresses
import B_Config as config
from K_Send_notification import slack_webhook, telegram_notification, email_notification

from time import sleep
from datetime import datetime, date, timedelta
import os
import io
import json
import logging.config

#------------------------------
#---------- INITIATE ----------
#------------------------------

# Create log path if it does not exist
if not os.path.exists('./logs'):
    os.makedirs('logs')

logging.config.dictConfig(logging_config.LOGGING_CONFIG)
default_logger = logging.getLogger('default_logger')
report_logger = logging.getLogger('report_logger')

report_array = io.StringIO()
report_handler = logging.StreamHandler(report_array)
report_logger.addHandler(report_handler)
default_logger.addHandler(report_handler)

# Initiate network
if config.NETWORK == 'MAINNET':
    chain_id = 'columbus-4'
    public_node_url = 'https://lcd.terra.dev'
    contact_addresses = contact_addresses(network='MAINNET')
    rev_contact_addresses = rev_contact_addresses(contact_addresses)
    tx_look_up = f'https://finder.terra.money/{chain_id}/tx/'

else:
    chain_id = 'tequila-0004'
    public_node_url = 'https://tequila-fcd.terra.dev'
    contact_addresses = contact_addresses(network='TESTNET')
    rev_contact_addresses = rev_contact_addresses(contact_addresses)
    tx_look_up = f'https://finder.terra.money/{chain_id}/tx/'

# Initiale contracts required
mmMarket = contact_addresses['mmMarket']
mmOverseer = contact_addresses['mmOverseer']
aTerra = contact_addresses['aTerra']

Mint = contact_addresses['Mint']  # https://docs.mirror.finance/contracts/mint
# https://docs.mirror.finance/contracts/collateral-oracle
Collateral_Oracle = contact_addresses['Collateral Oracle']
# https://docs.mirror.finance/contracts/staking
Staking = contact_addresses['Staking']
Lock = contact_addresses['Lock']

mirrorFarm = contact_addresses['mirrorFarm']
anchorFarm = contact_addresses['anchorFarm']
specFarm = contact_addresses['specFarm']
pylonFarm = contact_addresses['pylonFarm']
specgov = contact_addresses['specgov']

Terraswap_MIR_UST_Pair = contact_addresses['Terraswap MIR-UST Pair']
Spectrum_SPEC_UST_Pair = contact_addresses['Spectrum SPEC-UST Pair']
Terraswap_ANC_UST_Pair = contact_addresses['terraswapAncUstPair']

SPEC_token = contact_addresses['SPEC']
MIR_token = contact_addresses['MIR']
ANC_token = contact_addresses['ANC']

# Connect to Testnet
terra = LCDClient(chain_id=chain_id, url=public_node_url)

# Desire wallet via passphrase
mk = MnemonicKey(mnemonic=config.mnemonic)

# Define what wallet to use
wallet = terra.wallet(mk)

# Account Add
account_address = wallet.key.acc_address

# Date of Today
date_today = date.today()

#----------------------------------
#---------- SUPPORT DEF -----------
#----------------------------------


def get_fee_estimation():
    estimation = terra.treasury.tax_cap('uusd')
    fee = int(estimation.to_data().get('amount')) * \
        config.safety_multiple_on_transaction_fees
    return int(fee)


def get_status_of_tx(tx_hash):
    # Input: Transaction hash
    # Output: If the Transaction was successful returns True, otherwise the reeason why it failed
    try:
        status = terra.tx.tx_info(tx_hash).code
        if not status:
            return True
        else:
            return terra.tx.tx_info(tx_hash).rawlog

    except LCDResponseError as err:
        default_logger.error(err)
        pass


def write_cooldown(cooldowns):
    # Input: -
    # Output: -
    # Action: Creates a file in the root folder, containing the last incl. date of the cooldown periode
    with open('X_Cooldowns.json', 'w') as fp:
        json.dump(cooldowns, fp)
    fp.close
    pass


def read_cooldown():
    empty = {}
    # If file does not exists create one
    if not os.path.isfile('X_Cooldowns.json'):
        with open('X_Cooldowns.json', 'w') as fp:
            pass
        fp.close
    try:
        f = open('X_Cooldowns.json',)
        cooldowns = json.load(f)
        f.close
        return cooldowns
    except:
        return empty

#------------------------------
#---------- QUERIES -----------
#------------------------------
# https://terra-money.github.io/terra-sdk-python/core_modules/wasm.html


def get_aUST_rate():

    query = {
        "epoch_state": {},
    }
    query_result = terra.wasm.contract_query(mmMarket, query)

    aUST_rate = float(query_result['exchange_rate'])
    return aUST_rate


def get_uluna_rate():

    uluna_rate = float(int(str(terra.market.swap_rate(
        Coin('uluna', 1000000), 'uusd')).replace('uusd', ''))/1e6)
    return uluna_rate


def get_luna_col_multiplier():

    query = {
        "collateral_price": {
            "asset": "uluna"
        }
    }
    query_result = terra.wasm.contract_query(Collateral_Oracle, query)

    get_luna_col_multiplier = float(query_result['multiplier'])

    return get_luna_col_multiplier


def get_latest_block():
    result = terra.tendermint.block_info()
    height = result['block']['header']['height']
    return int(height)


def get_native_balance(denom):
    native_balance = 0
    balance_native = terra.bank.balance(address=account_address)
    try:
        native_balance = str(balance_native[denom]).replace(denom, '')
    except:
        native_balance = 0

    return float(int(native_balance)/1e6)


def get_aUST_balance():

    query = {
        "balance": {
            "address": account_address
        },
    }
    query_result = terra.wasm.contract_query(aTerra, query)
    balance = query_result['balance']

    return float(int(balance)/1e6)


def get_oracle_price_and_min_col_ratio(mAsset):
    # Input: mAssets as List
    # Outputs: Prices for mAssets as List

    # for mAsset in mAssets:
    # Oracle Price
    # https://tequila-fcd.terra.dev/wasm/contracts/terra1q3ls6u2glsazdeu7dxggk8d04elnvmsg0ung6n/store?query_msg={%22collateral_price%22:{%22asset%22:%22terra104tgj4gc3pp5s240a0mzqkhd3jzkn8v0u07hlf%22}}
    query_oracle_price = {
        "collateral_price": {
            "asset": mAsset
        },
    }
    position_ids_result = terra.wasm.contract_query(
        Collateral_Oracle, query_oracle_price)

    # Minimal collateral ratio
    # mBABA
    # https://tequila-fcd.terra.dev/wasm/contracts/terra1s9ehcjv0dqj2gsl72xrpp0ga5fql7fj7y3kq3w/store?query_msg={"asset_config":{"asset_token":"terra15dr4ah3kha68kam7a907pje9w6z2lpjpnrkd06"}}

    query_oracle_price = {
        "asset_config": {
            "asset_token": mAsset
        },
    }
    min_col_ratio_result = terra.wasm.contract_query(Mint, query_oracle_price)

    oracle_price_and_min_col_ratio = [
        position_ids_result['rate'], min_col_ratio_result['min_collateral_ratio']]

    return oracle_price_and_min_col_ratio


def Mirror_get_position_info():
    # Input: -
    # Output: List of all short positions incl.
    # [[position_idx, collateral_amount_in_ust, shorted_asset_qty, mAsset_address, oracle_price, min_col_ratio, cur_col_ratio], [....]]

    # [position_idx, collateral_price, mAsset,
    # https://tequila-fcd.terra.dev/wasm/contracts/terra1s9ehcjv0dqj2gsl72xrpp0ga5fql7fj7y3kq3w/store?query_msg={%22positions%22:{%22owner_addr%22:%20%22terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma%22}}
    Mirror_position_info = []
    query_position_ids = {
        "positions": {
            "owner_addr": account_address
        },
    }
    position_ids_result = terra.wasm.contract_query(Mint, query_position_ids)

    for position in position_ids_result['positions']:

        # There are currently three tokens that can be used as collateral Luna, UST, aUST, so we need to find out which one is used for each position_idx.
        position_idx = position['idx']
        try:
            # for uluna / uusd
            collateral_token_denom = position['collateral']['info']['native_token']['denom']
        except:
            # for aUST = terra1hzh9vpxhsk8253se0vv5jj6etdvxu3nv8z07zu/terra1ajt556dpzvjwl0kl5tzku3fc3p3knkg9mkv8jl
            if position['collateral']['info']['token']['contract_addr'] == aTerra:
                collateral_token_denom = 'aUST'

        # This value is returned from the blockchain in-kind.
        collateral_amount_in_kind = int(position['collateral']['amount']) / 1e6

        # As the mAsset is valued in UST, we convert the colateral_amount also into UST here.
        if collateral_token_denom == 'aUST':
            collateral_amount_in_ust = collateral_amount_in_kind * aUST_rate
        elif collateral_token_denom == 'uluna':
            collateral_amount_in_ust = collateral_amount_in_kind * uluna_rate
        elif collateral_token_denom == 'uusd':
            collateral_amount_in_ust = collateral_amount_in_kind

        shorted_asset_qty = int(position['asset']['amount']) / 1e6
        mAsset_address = position['asset']['info']['token']['contract_addr']

        try:
            mAsset_symbol = rev_contact_addresses[mAsset_address]
        except:
            mAsset_symbol = 'Not available'

        oracle_price_and_min_col_ratio = get_oracle_price_and_min_col_ratio(
            mAsset_address)
        oracle_price = float(oracle_price_and_min_col_ratio[0])
        shorted_asset_amount = float(
            oracle_price_and_min_col_ratio[0]) * shorted_asset_qty

        # If the collateral is provided in UST or aUST the min_col_ratio is as received form the query.
        # if the colalteral is Luna it is luna_col_multiplier (4/3) of the min_col_ratio
        if collateral_token_denom == 'uluna':
            min_col_ratio = float(
                oracle_price_and_min_col_ratio[1]) * luna_col_multiplier
        else:
            min_col_ratio = float(oracle_price_and_min_col_ratio[1])

        cur_col_ratio = collateral_amount_in_ust / \
            (oracle_price * shorted_asset_qty)
        lower_trigger_ratio = min_col_ratio + config.Mirror_lower_distance
        target_ratio = min_col_ratio + config.Mirror_target_distance
        upper_trigger_ratio = min_col_ratio + config.Mirror_upper_distance
        distance_to_min_col = cur_col_ratio - min_col_ratio

        if cur_col_ratio < lower_trigger_ratio \
                and config.Mirror_enable_deposit_collateral:
            action_to_be_executed = 'deposit'
            # Calculate how much in-kind to withdraw to return to the desired ratio, even if the collaterial is not in UST
            # v This is how much collateral is already in
            amount_to_execute_in_ust = target_ratio * \
                shorted_asset_amount - collateral_amount_in_ust
            # ^ This is how much absolut collateral in UST is required to get the desired target_ratio
            # Quick rule of three
            amount_to_execute_in_kind = (
                collateral_amount_in_kind / collateral_amount_in_ust) * amount_to_execute_in_ust

        elif cur_col_ratio > upper_trigger_ratio \
                and config.Mirror_enable_withdraw_collateral:
            action_to_be_executed = 'withdraw'
            # Calculate how much in-kind to withdraw to return to the desired ratio, even if the collaterial is not in UST
            # v This is how much collateral is already in
            amount_to_execute_in_ust = collateral_amount_in_ust - \
                target_ratio * shorted_asset_amount
            # ^ This is how much absolut collateral in UST is required to get the desired target_ratio
            # Quick rule of three
            amount_to_execute_in_kind = (
                collateral_amount_in_kind / collateral_amount_in_ust) * amount_to_execute_in_ust

        else:
            action_to_be_executed = 'none'
            amount_to_execute_in_kind = 0

        # # Calculate the amount_to_execute also in UST
        # if collateral_token_denom == 'aUST':
        #     amount_to_execute_in_ust = amount_to_execute_in_kind * aUST_rate
        # elif collateral_token_denom == 'uluna':
        #     amount_to_execute_in_ust = amount_to_execute_in_kind * uluna_rate
        # elif collateral_token_denom == 'uusd':
        #     amount_to_execute_in_ust = amount_to_execute_in_kind

        Mirror_position_info.append({
            'position_idx': position_idx,
            'mAsset_symbol': mAsset_symbol,
            'mAsset_address': mAsset_address,
            'collateral_token_denom': collateral_token_denom,
            'collateral_amount_in_kind': collateral_amount_in_kind,
            'collateral_amount_in_ust': collateral_amount_in_ust,
            'shorted_asset_qty': shorted_asset_qty,
            'oracle_price': oracle_price,
            'shorted_asset_amount': shorted_asset_amount,
            'min_col_ratio': min_col_ratio,
            'cur_col_ratio': cur_col_ratio,
            'lower_trigger_ratio': lower_trigger_ratio,
            'target_ratio': target_ratio,
            'upper_trigger_ratio': upper_trigger_ratio,
            'action_to_be_executed': action_to_be_executed,
            'amount_to_execute_in_kind': amount_to_execute_in_kind,
            'amount_to_execute_in_ust': amount_to_execute_in_ust,
            'distance_to_min_col': distance_to_min_col
        })

    # Sort positions by distance_to_min_col (lowest first)
    def sort_by_distance(elem):
        return elem['distance_to_min_col']

    # Sort positions by action (withdrawls first)
    def sort_by_action(elem):
        return elem['action_to_be_executed']

    Mirror_position_info.sort(key=sort_by_distance)
    Mirror_position_info.sort(key=sort_by_action, reverse=True)

    return Mirror_position_info


def get_claimable_MIR():
    # Input: -
    # Output: Returns the quantity of MIR that can be claimed
    claimable = 0

    query = {
        "reward_info": {
            "staker_addr": account_address
        },
    }

    query_result = terra.wasm.contract_query(Staking, query)

    # Sum up all claimable rewards for this account_address
    for reward in query_result['reward_infos']:
        claimable += int(reward['pending_reward'])

    return float(claimable/1e6)


def get_claimable_SPEC():
    # Input: -
    # Output: Returns the quantity of SPEC that can be claimed
    claimable = 0
    latest_block = get_latest_block()

    # Query for the Mirror related claimable SPEC
    query = {
        "reward_info": {
            "staker_addr": account_address,
            "height": latest_block
        },
    }
    query_result = terra.wasm.contract_query(mirrorFarm, query)
    # Sum up all claimable rewards for this account_address
    for reward in query_result['reward_infos']:
        claimable += int(reward['pending_spec_reward'])

    # Query for the Anchor realted claimable SPEC
    query = {
        "reward_info": {
            "staker_addr": account_address,
            "height": latest_block
        },
    }
    query_result = terra.wasm.contract_query(anchorFarm, query)
    # Sum up all claimable rewards for this account_address
    for reward in query_result['reward_infos']:
        claimable += int(reward['pending_spec_reward'])

    # Query for the Spec related claimable SPEC
    query = {
        "reward_info": {
            "staker_addr": account_address,
            "height": latest_block
        },
    }
    query_result = terra.wasm.contract_query(specFarm, query)
    # Sum up all claimable rewards for this account_address
    for reward in query_result['reward_infos']:
        claimable += int(reward['pending_spec_reward'])

    # Query for the Pylon realted claimable SPEC
    query = {
        "reward_info": {
            "staker_addr": account_address,
            "height": latest_block
        },
    }
    query_result = terra.wasm.contract_query(pylonFarm, query)
    # Sum up all claimable rewards for this account_address
    for reward in query_result['reward_infos']:
        claimable += int(reward['pending_spec_reward'])

    return float(claimable/1e6)


def get_claimable_ANC():
    # Input: -
    # Output: Returns the quantity of ANC that can be claimed
    claimable = 0
    latest_block = get_latest_block()

    query = {
        "borrower_info": {
            "borrower": account_address,
            "block_height": latest_block
        }
    }

    query_result = terra.wasm.contract_query(mmMarket, query)

    claimable = float(query_result['pending_rewards']) / 1e6

    return claimable


def Mirror_get_claimable_UST(Mirror_position_info):
    # Input: Mirror_position_info
    # Output: Returns the quantity of UST that can be claimed
    # https://docs.mirror.finance/contracts/lock#positionlockinfo

    claimable = 0

    for position in Mirror_position_info:

        query = {
            "position_lock_info": {
                "position_idx": position['position_idx']
            }
        }

        try:
            query_result = terra.wasm.contract_query(Lock, query)

            locked_amount = float(query_result['locked_amount'])
            unlock_time = float(query_result['unlock_time'])
            if unlock_time < int(datetime.utcnow().timestamp()):
                claimable += locked_amount
        except:
            # If a short position has already been claimed, this query will result in an error. We catch it here.
            claimable = 0

    return float(claimable/1e6)


def simulate_MIR_Swap(amount):
    # Input: Amount of MIR
    # Output: Value of input-MIR at current market price in UST
    # https://fcd.terra.dev/wasm/contracts/terra1tn8ejzw8kpuc87nu42f6qeyen4c7qy35tl8t20/store?query_msg={"simulation":{"offer_asset":{"amount":"1000000","info":{"token":{"contract_addr":"terra1s5eczhe0h0jutf46re52x5z4r03c8hupacxmdr"}}}}}

    query = {
        "simulation": {
            "offer_asset": {
                "amount": str(int(amount * 1e6)),
                "info": {
                    "token": {
                        "contract_addr": MIR_token
                    }
                }
            }
        }
    }
    query_result = terra.wasm.contract_query(Terraswap_MIR_UST_Pair, query)
    MIR_return = float(int(query_result['return_amount'])/1e6)

    return MIR_return


def simulate_SPEC_Swap(amount):
    # Input: Amount of SPEC
    # Output: Value of input-SPEC at current market price in UST
    # https://fcd.terra.dev/wasm/contracts/terra1tn8ejzw8kpuc87nu42f6qeyen4c7qy35tl8t20/store?query_msg={"simulation":{"offer_asset":{"amount":"1000000","info":{"token":{"contract_addr":"terra1s5eczhe0h0jutf46re52x5z4r03c8hupacxmdr"}}}}}

    query = {
        "simulation": {
            "offer_asset": {
                "amount": str(int(amount*1e6)),
                "info": {
                    "token": {
                        "contract_addr": SPEC_token
                    }
                }
            }
        }
    }
    query_result = terra.wasm.contract_query(Spectrum_SPEC_UST_Pair, query)
    SPEC_return = float(int(query_result['return_amount'])/1e6)

    return SPEC_return


def simulate_ANC_Swap(amount):
    # Input: Amount of ANC
    # Output: Value of input-ANC at current market price in UST
    query = {
        "simulation": {
            "offer_asset": {
                "amount": str(int(amount*1e6)),
                "info": {
                    "token": {
                        "contract_addr": ANC_token
                    }
                }
            }
        }
    }
    query_result = terra.wasm.contract_query(Terraswap_ANC_UST_Pair, query)
    ANC_return = float(int(query_result['return_amount'])/1e6)

    return ANC_return


def Anchor_get_max_ltv_ratio():

    max_ltv_ratio = {}

    query = {
        "whitelist": {},
    }
    query_result = terra.wasm.contract_query(mmOverseer, query)

    for elem in query_result['elems']:
        max_ltv_ratio[elem['symbol']] = float(elem['max_ltv'])

    return max_ltv_ratio


def Anchor_get_borrow_info():
    # Input: -
    # Output: Collects, calculated all there is required to know for your Anchor debt

    max_ltv_ratio = Anchor_get_max_ltv_ratio()['BETH']

    query_msg_borrow_limit = {
        "borrow_limit": {
            "borrower": account_address
        },
    }
    borrow_limit_result = terra.wasm.contract_query(
        mmOverseer, query_msg_borrow_limit)

    query_msg_loan = {
        "borrower_info": {
            "borrower": account_address,
            "block_height": get_latest_block()
        },
    }
    loan_amount_result = terra.wasm.contract_query(mmMarket, query_msg_loan)

    query_msg_anchor_deposited = {
        "balance": {
            "address": account_address,
        },
    }
    total_deposited_amount = terra.wasm.contract_query(
        aTerra, query_msg_anchor_deposited)

    loan_amount = int(loan_amount_result['loan_amount']) / 1e6
    borrow_limit = int(borrow_limit_result['borrow_limit']) / 1e6
    total_deposited_amount = int(total_deposited_amount['balance']) / 1e6
    cur_col_ratio = loan_amount / borrow_limit * max_ltv_ratio
    lower_trigger_ratio = max_ltv_ratio + config.Anchor_lower_distance
    upper_trigger_ratio = max_ltv_ratio + config.Anchor_upper_distance
    distance_to_max_ltv = cur_col_ratio - max_ltv_ratio

    if cur_col_ratio > lower_trigger_ratio and \
            config.Anchor_enable_auto_repay_of_debt:
        action_to_be_executed = 'repay'
        # Calculate how much aUST to deposite to return to the desired ratio
        amount_to_execute_in_ust = loan_amount - \
            (borrow_limit * (max_ltv_ratio +
             config.Anchor_target_distance) / max_ltv_ratio)
    elif cur_col_ratio < upper_trigger_ratio and \
            config.Anchor_enable_auto_borrow_UST:
        action_to_be_executed = 'borrow'
        # Calculate how much aUST to withdraw to return to the desired ratio
        amount_to_execute_in_ust = (
            borrow_limit * (max_ltv_ratio + config.Anchor_target_distance) / max_ltv_ratio) - loan_amount
    else:
        action_to_be_executed = 'none'
        amount_to_execute_in_ust = 0

    Anchor_debt_info = {
        'loan_amount': loan_amount,
        'borrow_limit': borrow_limit,
        'cur_col_ratio': cur_col_ratio,
        'lower_trigger_ratio': lower_trigger_ratio,
        'upper_trigger_ratio': upper_trigger_ratio,
        'distance_to_max_ltv': distance_to_max_ltv,
        'action_to_be_executed': action_to_be_executed,
        'amount_to_execute_in_ust': amount_to_execute_in_ust
    }

    return Anchor_debt_info
#------------------------------------------------
#---------- TRANSACTIONS ON THE CHAIN -----------
#------------------------------------------------
# https://terra-money.github.io/terra-sdk-python/guides/transactions.html


def Mirror_deposit_collateral_for_position(idx, collateral_amount_in_kind, denom):

    # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
    if denom == 'aUST':
        # https://finder.terra.money/tequila-0004/tx/0B88BC73AB9E1699D710750E5F4A5F871D5D915733416975A1CA621DF4ACBB6D

        amount = int(collateral_amount_in_kind*1e6)

        send = MsgExecuteContract(
            sender=wallet.key.acc_address,
            contract=aTerra,
            execute_msg={
                "send": {
                    "amount": str(amount),
                    "contract": Mint,
                    "msg": {
                        "deposit": {
                            "position_idx": idx,
                            "collateral": {
                                "amount": str(amount),
                                "info": {
                                    "token": {
                                        "contract_addr": aTerra,
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ),

    else:
        # Luna and UST are natively supported
        # https://finder.terra.money/tequila-0004/tx/EC32F0598F7E589598A33E9F848140EDDE0DD8E140BF997F286EA6948A2D3536
        coin = Coin(denom, int(collateral_amount_in_kind*1e6)).to_data()
        coins = Coins.from_data([coin])

        amount = int(collateral_amount_in_kind*1e6)

        send = MsgExecuteContract(
            sender=wallet.key.acc_address,
            contract=Mint,
            execute_msg={
                "deposit": {
                    "position_idx": idx,
                    "collateral": {
                        "amount": str(amount),
                        "info": {
                            "native_token": {
                                "denom": denom
                            }
                        }
                    }
                }
            },
            coins=coins
        ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def Mirror_withdraw_collateral_for_position(idx, collateral_amount_in_kind, denom):

    # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
    if denom == 'aUST':
        # https://finder.terra.money/tequila-0004/tx/10C1B6310DA5B16F5EE96F3535B99C9CD7DC5D696054D547C32A54F2317E930B

        amount = int(collateral_amount_in_kind*1e6)

        send = MsgExecuteContract(
            sender=wallet.key.acc_address,
            contract=aTerra,
            execute_msg={
                "withdraw": {
                    "position_idx": idx,
                    "collateral": {
                        "amount": str(amount),
                        "info": {
                            "token": {
                                "contract_addr": aTerra
                            }
                        }
                    }
                }
            }
        ),

    else:
        # https://finder.terra.money/tequila-0004/tx/164192158C99EEC5898F64029D34A0F407F7B0F946BA7408504B2A0230C605C8

        coin = Coin('uusd', int(collateral_amount_in_kind*1e6)).to_data()
        coins = Coins.from_data([coin])

        amount = int(collateral_amount_in_kind*1e6)

        send = MsgExecuteContract(
            sender=wallet.key.acc_address,
            contract=Mint,
            execute_msg={
                "withdraw": {
                    "position_idx": idx,
                    "collateral": {
                        "amount": str(amount),
                        "info": {
                            "native_token": {
                                "denom": "uusd"
                            }
                        }
                    }
                }
            },
            coins=coins
        ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def Mirror_claim_unlocked_UST(Mirror_position_info):
    # Input: Mirror_position_info
    # Output:
    # https://finder.terra.money/tequila-0004/tx/968436B83C3556FDD9AC7F590E05194F6B8E2B45BF5456291D0DB818C622E8E0

    def position_idxs_to_be_claimed():
        position_idxs_to_be_claimed = []
        for position in Mirror_position_info:
            position_idxs_to_be_claimed.append(position['position_idx'])
        return position_idxs_to_be_claimed

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=Lock,
        execute_msg={
            "unlock_position_funds": {
                "positions_idx": position_idxs_to_be_claimed()
            }
        },
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def claim_MIR():
    # Input:
    # Output:

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=Staking,
        execute_msg={
            "withdraw": {}
        },
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def claim_SPEC():
    # Input:
    # Output:
    # https://finder.terra.money/tequila-0004/tx/B42BE209EEBF3F4D3A2ED9F37A04651CAA5431A0DB6239E4D46D17FE65F44891

    send = [MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=specgov,
        execute_msg={
            "mint": {}
        }
    ), MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=mirrorFarm,
        execute_msg={
            "withdraw": {}
        }
    )]

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def claim_ANC():
    # Input:
    # Output:
    # https://finder.terra.money/tequila-0004/tx/EA2499249A738429320370E3380C2C50BABED25C0F3E2BD15F7CFDA37E4AA93F

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=mmMarket,
        execute_msg={
            "claim_rewards": {}
        }
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def sell_MIR(amount):
    # Input: Amount of MIR to sell
    # https://finder.terra.money/tequila-0004/tx/50EFF091BECDAA44FE8654F8977AD62645D8C2DCA7CC7C5B87C96435BE345E7A
    # https://docs.terraswap.io/docs/howto/swap/

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=MIR_token,
        execute_msg={
            "send": {
                "contract": Terraswap_MIR_UST_Pair,
                "amount": str(int(amount*1e6)),
                "msg": "eyJzd2FwIjp7fX0="
            }
        }
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def sell_SPEC(amount):
    # Input: Amount of SPEC to sell
    # https://finder.terra.money/tequila-0004/tx/B2303E42ABA1E66F7466ACD7C87871013C9305DA73AC9FEADB7C5D81912C2706
    # https://docs.terraswap.io/docs/howto/swap/

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=SPEC_token,
        execute_msg={
            "send": {
                "contract": Spectrum_SPEC_UST_Pair,
                "amount": str(int(amount*1e6)),
                "msg": "eyJzd2FwIjp7fX0="
            }
        }
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def sell_ANC(amount):
    # Input: Amount of ANC to sell
    # Output:
    # https://docs.terraswap.io/docs/howto/swap/

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=ANC_token,
        execute_msg={
            "send": {
                "contract": Terraswap_ANC_UST_Pair,
                "amount": str(int(amount*1e6)),
                "msg": "eyJzd2FwIjp7fX0="
            }
        }
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def Anchor_deposit_UST_for_Earn(amount):

    # Input: amount of UST to deposit on Anchor Earn
    # Output:

    amount = int(amount * 1e6)

    # Depoit a bit less, to have some UST for tx fees
    coin = Coin('uusd', amount - fee_estimation).to_data()
    coins = Coins.from_data([coin])

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=mmMarket,
        execute_msg={
            "deposit_stable": {}
        },
        coins=coins
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def Anchor_withdraw_UST_from_Earn(amount, denom):
    # Input: Amount of UST to withdraw
    # Output:

    # Convert amount UST into aUST for withdrawl and add a bit more for fees
    if denom == 'UST':
        amount = int(amount / aUST_rate)
    else:
        pass

    amount = (amount * 1e6) + fee_estimation

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=aTerra,
        execute_msg={
            "send": {
                "contract": mmMarket,
                "amount": str(amount),
                "msg": "eyJyZWRlZW1fc3RhYmxlIjp7fX0="}
        },
        coins=Coins()  # { "denom": "uusd", "amount": "6140784000" }
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def Anchor_repay_debt_UST(amount):
    # Input: Amount of UST to repay
    # Output:
    # https://finder.terra.money/tequila-0004/tx/7FDB09CC930C8529ABFF8111631A3A9B389AFC61A1EBAC10F6CB5D2FABD622B7

    amount = int(amount * 1000000)

    # Deduct the fee incl safety so there is still some UST left
    coin = Coin('uusd', amount - fee_estimation).to_data()
    coins = Coins.from_data([coin])

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=mmMarket,
        execute_msg={
            "repay_stable": {}
        },
        coins=coins
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


def Anchor_borrow_more_UST(amount):

    amount = int((amount * 1e6) + fee_estimation)

    send = MsgExecuteContract(
        sender=wallet.key.acc_address,
        contract=mmMarket,
        execute_msg={
            "borrow_stable": {
                "borrow_amount": f'{amount}'
            }
        },
        coins=Coins()
    ),

    sendtx = wallet.create_and_sign_tx(send, fee=StdFee(1000000, fee))
    result = terra.tx.broadcast(sendtx)

    return result.txhash


#----------------------------------
#---------- INITIATE DEF ----------
#----------------------------------

if __name__ == '__main__':
    global luna_col_multiplier, aUST_rate, uluna_rate, fee_estimation, fee

    luna_col_multiplier = get_luna_col_multiplier()
    aUST_rate = get_aUST_rate()
    uluna_rate = get_uluna_rate()
    fee_estimation = get_fee_estimation()
    fee = str(fee_estimation + 500000) + 'uusd'

#-------------------------------
#---------- MAIN DEF -----------
#-------------------------------


def keep_safe():
    try:
        default_logger.debug("---- Start of keep_safe() ----")

    #------------------------------------------
    #---------- GENERAL SECTION ----------
    #------------------------------------------

        Mirror_position_info = Mirror_get_position_info()
        Anchor_borrow_info = Anchor_get_borrow_info()
        cooldowns = read_cooldown()
        general_estimated_tx_fee = fee_estimation / 1e6
        current_UST_wallet_balance = get_native_balance('uusd')
        UST_balance_to_be_deposited_at_Anchor_Earn = 0

        if current_UST_wallet_balance < general_estimated_tx_fee:
            default_logger.warning(
                'YOU NEED TO ACT! Your wallet balance of {current_UST_wallet_balance} UST is too low to execute any transaction.')
            return False

    #------------------------------------------
    #---------- CLAIM & SELL SECTION ----------
    #------------------------------------------

        # Mirror: Claim & sell MIR
        default_logger.debug("---- Mirror: Claim & sell MIR ----")
        if config.MIR_claim_and_sell_token \
                and current_UST_wallet_balance > general_estimated_tx_fee:
            claimable_MIR = get_claimable_MIR()
            value_of_MIR_claim = simulate_MIR_Swap(claimable_MIR)
            # ! Balance will not be checked again, if enough UST are available for tx fees
            if value_of_MIR_claim >= config.MIR_min_total_value \
                    and (value_of_MIR_claim/claimable_MIR) >= config.MIR_min_price:
                claim_MIR_tx = claim_MIR()
                claim_MIR_tx_status = get_status_of_tx(claim_MIR_tx)

                if claim_MIR_tx_status:
                    default_logger.debug(f'Success TX: {claim_MIR_tx}.')
                    sell_MIR_tx = sell_MIR(claimable_MIR)
                    sell_MIR_tx_status = get_status_of_tx(sell_MIR_tx)
                    if sell_MIR_tx_status:
                        default_logger.debug(f'Success TX: {sell_MIR_tx}.')
                        report_logger.info(
                            f'{claimable_MIR:.2f} MIR have been claimed and sold for {value_of_MIR_claim:.2f} UST total.')
                        UST_balance_to_be_deposited_at_Anchor_Earn += value_of_MIR_claim
                        default_logger.debug(
                            f'UST_balance_to_be_deposited_at_Anchor_Earn: {UST_balance_to_be_deposited_at_Anchor_Earn}.')
                    else:
                        default_logger.warning(f'Failed TX: {sell_MIR_tx}.\n'
                                               f'Reason: {sell_MIR_tx_status}')
                else:
                    default_logger.warning(f'Failed TX: {claim_MIR_tx}.\n'
                                           f'Reason: {claim_MIR_tx_status}')
            else:
                default_logger.debug(
                    f'Skipped because claimable MIR value ({value_of_MIR_claim:.2f}) below limit ({config.MIR_min_total_value:.2f}) or MIR price ({(value_of_MIR_claim/claimable_MIR):.2f}) below limit ({config.MIR_min_price:.2f}).')
        else:
            default_logger.debug(
                f'Skipped because disabled by config ({config.MIR_claim_and_sell_token}) or insufficent funds ({(current_UST_wallet_balance - general_estimated_tx_fee):.2f}).')

        # Spectrum: Claim & sell SPEC
        default_logger.debug("---- Mirror: Claim & sell SPEC ----")
        if config.SPEC_claim_and_sell_token \
                and current_UST_wallet_balance > general_estimated_tx_fee:
            claimable_SPEC = get_claimable_SPEC()
            value_of_SPEC_claim = simulate_SPEC_Swap(claimable_SPEC)
            # ! Balance will not be checked again, if enough UST are available for tx fees
            if value_of_SPEC_claim >= config.SPEC_min_total_value \
                    and (value_of_SPEC_claim/claimable_SPEC) >= config.SPEC_min_price:
                claim_SPEC_tx = claim_SPEC()
                claim_SPEC_tx_status = get_status_of_tx(claim_SPEC_tx)

                if claim_SPEC_tx_status:
                    default_logger.debug(f'Success TX: {claim_SPEC_tx}.')
                    sell_SPEC_tx = sell_SPEC(claimable_SPEC)
                    sell_SPEC_tx_status = get_status_of_tx(sell_SPEC_tx)
                    if sell_SPEC_tx_status:
                        default_logger.debug(f'Success TX: {sell_SPEC_tx}.')
                        report_logger.info(
                            f'{claimable_SPEC:.2f} SPEC have been claimed and sold for {value_of_SPEC_claim:.2f} UST total.')
                        UST_balance_to_be_deposited_at_Anchor_Earn += value_of_SPEC_claim
                        default_logger.debug(
                            f'UST_balance_to_be_deposited_at_Anchor_Earn: {UST_balance_to_be_deposited_at_Anchor_Earn}.')
                    else:
                        default_logger.warning(f'Failed TX: {sell_SPEC_tx}.\n'
                                               f'Reason: {sell_SPEC_tx_status}')
                else:
                    default_logger.warning(f'Failed TX: {claim_SPEC_tx}.\n'
                                           f'Reason: {claim_SPEC_tx_status}')
            else:
                default_logger.debug(
                    f'Skipped because claimable SPEC value ({value_of_SPEC_claim:.2f}) below limit ({config.SPEC_min_total_value:.2f}) or SPEC price ({(value_of_SPEC_claim/claimable_SPEC):.2f}) below limit ({config.SPEC_min_price:.2f}).')
        else:
            default_logger.debug(
                f'Skipped because disabled by config ({config.SPEC_claim_and_sell_token}) or insufficent funds ({(current_UST_wallet_balance - general_estimated_tx_fee):.2f}).')

        # Anchor: Claim & sell ANC
        default_logger.debug("---- Mirror: Claim & sell ANC ----")
        if config.ANC_claim_and_sell_token \
                and current_UST_wallet_balance > general_estimated_tx_fee:
            claimable_ANC = get_claimable_ANC()
            value_of_ANC_claim = simulate_ANC_Swap(claimable_ANC)
            # ! Balance will not be checked again, if enough UST are available for tx fees
            if value_of_ANC_claim >= config.ANC_min_total_value \
                    and (value_of_ANC_claim/claimable_ANC) >= config.ANC_min_price:
                claim_ANC_tx = claim_ANC()
                claim_ANC_tx_status = get_status_of_tx(claim_ANC_tx)

                if claim_ANC_tx_status:
                    default_logger.debug(f'Success TX: {claim_ANC_tx}.')
                    sell_ANC_tx = sell_ANC(claimable_ANC)
                    sell_ANC_tx_status = get_status_of_tx(sell_ANC_tx)
                    if sell_ANC_tx_status:
                        default_logger.debug(f'Success TX: {sell_ANC_tx}.')
                        report_logger.info(
                            f'{claimable_ANC:.2f} ANC have been claimed and sold for {value_of_ANC_claim:.2f} UST total.')
                        UST_balance_to_be_deposited_at_Anchor_Earn += value_of_ANC_claim
                        default_logger.debug(
                            f'UST_balance_to_be_deposited_at_Anchor_Earn: {UST_balance_to_be_deposited_at_Anchor_Earn}.')
                    else:
                        default_logger.warning(f'Failed TX: {sell_ANC_tx}.\n'
                                               f'Reason: {sell_ANC_tx_status}')
                else:
                    default_logger.warning(f'Failed TX: {claim_ANC_tx}.\n'
                                           f'Reason: {claim_ANC_tx_status}')
            else:
                default_logger.debug(
                    f'Skipped because claimable ANC value ({value_of_ANC_claim:.2f}) below limit ({config.ANC_min_total_value:.2f}) or ANC price ({(value_of_ANC_claim/claimable_SPEC):.2f}) below limit ({config.ANC_min_price:.2f}).')
        else:
            default_logger.debug(
                f'Skipped because disabled by config ({config.ANC_claim_and_sell_token}) or insufficent funds ({(current_UST_wallet_balance - general_estimated_tx_fee):.2f}).')

        # Mirror: Claim un-locked UST
        default_logger.debug("---- Mirror: Claim un-locked UST ----")
        if config.Mirror_claim_unlocked_UST \
                and current_UST_wallet_balance > general_estimated_tx_fee:
            claimable_UST = Mirror_get_claimable_UST(Mirror_position_info)
            # ! Balance will not be checked again, if enough UST are available for tx fees
            if claimable_UST > config.Mirror_min_amount_UST_to_claim:
                Mirror_claim_unlocked_UST_tx = Mirror_claim_unlocked_UST(
                    Mirror_position_info)
                Mirror_claim_unlocked_UST_tx_status = get_status_of_tx(
                    Mirror_claim_unlocked_UST_tx)
                if Mirror_claim_unlocked_UST_tx_status:
                    default_logger.debug(
                        f'Success TX: {Mirror_claim_unlocked_UST_tx}.')
                    report_logger.info(
                        f'{claimable_UST:.2f} UST have been claimed from your shorts on Mirror.')
                    UST_balance_to_be_deposited_at_Anchor_Earn += claimable_UST
                    default_logger.debug(
                        f'UST_balance_to_be_deposited_at_Anchor_Earn: {UST_balance_to_be_deposited_at_Anchor_Earn}.')
                else:
                    default_logger.warning(f'Failed TX: {Mirror_claim_unlocked_UST_tx}.\n'
                                           f'Reason: {Mirror_claim_unlocked_UST_tx_status}')
            else:
                default_logger.debug(
                    f'Skipped because claimable UST amount ({claimable_UST:.2f}) below limit ({config.Mirror_min_amount_UST_to_claim:.2f}).')
        else:
            default_logger.debug(
                f'Skipped because disabled by config ({config.Mirror_claim_unlocked_UST}) or insufficent funds ({(current_UST_wallet_balance - general_estimated_tx_fee):.2f}).')

    #-----------------------------------------------------------
    #---------- ANCHOR REPAY, BORROW, DEPOSIT SECTION ----------
    #-----------------------------------------------------------

        # Anchor: Repay loan if necesarry and repayment amount bigger than Anchor_min_repay_limit
        Anchor_amount_to_execute_in_ust = Anchor_borrow_info['amount_to_execute_in_ust']
        Anchor_action_to_be_executed = Anchor_borrow_info['action_to_be_executed']

        # Update the wallet's balance, in case some token have been sold for UST
        current_UST_wallet_balance = get_native_balance('uusd')
        current_aUST_wallet_balance = get_aUST_balance()

        default_logger.debug("---- Anchor: Repay ----")
        if Anchor_action_to_be_executed == 'repay' \
                and Anchor_amount_to_execute_in_ust > config.Anchor_min_repay_limit:

            # Check if the wallet has enough UST to repay and for tx fees
            if Anchor_amount_to_execute_in_ust > (current_UST_wallet_balance - general_estimated_tx_fee):
                Anchor_repay_debt_UST_tx = Anchor_repay_debt_UST(
                    Anchor_amount_to_execute_in_ust)
                Anchor_repay_debt_UST_tx_status = get_status_of_tx(
                    Anchor_repay_debt_UST_tx)
                if Anchor_repay_debt_UST_tx_status:
                    default_logger.debug(
                        f'Success TX: {Anchor_repay_debt_UST_tx}.')
                    report_logger.info(
                        f'{Anchor_amount_to_execute_in_ust:.2f} UST have been repaid to Anchor Borrow from your wallet.')
                else:
                    default_logger.warning(f'Failed TX: {Anchor_repay_debt_UST_tx}.\n'
                                           f'Reason: {Anchor_repay_debt_UST_tx_status}')

            # Otherwise check if the balance in the wallet + a withdrawl of UST from Anchor Earn would be enough, and withdraw what is needed
            elif config.Anchor_enable_withdraw_of_deposited_UST \
                    and (current_aUST_wallet_balance * aUST_rate() + current_UST_wallet_balance - general_estimated_tx_fee) >= Anchor_amount_to_execute_in_ust:

                Amount_to_be_withdrawn = Anchor_amount_to_execute_in_ust - \
                    current_UST_wallet_balance + general_estimated_tx_fee
                Anchor_withdraw_UST_from_Earn_tx = Anchor_withdraw_UST_from_Earn(
                    Amount_to_be_withdrawn, 'UST')
                Anchor_withdraw_UST_from_Earn_tx_status = get_status_of_tx(
                    Anchor_withdraw_UST_from_Earn_tx)

                if Anchor_withdraw_UST_from_Earn_tx_status:
                    default_logger.debug(
                        f'Success TX: {Anchor_withdraw_UST_from_Earn_tx}.')
                    Anchor_repay_debt_UST_tx = Anchor_repay_debt_UST(
                        Anchor_amount_to_execute_in_ust)
                    Anchor_repay_debt_UST_tx_status = get_status_of_tx(
                        Anchor_repay_debt_UST_tx)
                    if Anchor_repay_debt_UST_tx_status:
                        default_logger.debug(
                            f'Success TX: {Anchor_repay_debt_UST_tx}.')
                        report_logger.info(
                            f'{Amount_to_be_withdrawn:.2f} UST have been withdrawn from your Anchor Earn and {Anchor_repay_debt_UST_tx:.2f} (incl. UST from your wallet) have been repaid to Anchor Borrow.')
                    else:
                        default_logger.warning(f'Failed TX: {Anchor_repay_debt_UST_tx}.\n'
                                               f'Reason: {Anchor_repay_debt_UST_tx_status}')
                else:
                    default_logger.warning(f'Failed TX: {Anchor_withdraw_UST_from_Earn_tx}.\n'
                                           f'Reason: {Anchor_withdraw_UST_from_Earn_tx_status}')

            # Otherwise (if allowed) withdraw what is available and repay what is possible if enough tx fees are available
            elif config.Anchor_enable_partially_repay_if_not_enough_UST_in_wallet \
                    and current_UST_wallet_balance > general_estimated_tx_fee:

                Anchor_withdraw_UST_from_Earn_tx = Anchor_withdraw_UST_from_Earn(
                    current_aUST_wallet_balance, 'aUST')
                Anchor_withdraw_UST_from_Earn_tx_status = get_status_of_tx(
                    Anchor_withdraw_UST_from_Earn_tx)

                if Anchor_withdraw_UST_from_Earn_tx_status:
                    default_logger.debug(
                        f'Success TX: {Anchor_withdraw_UST_from_Earn_tx}.')

                    Anchor_repay_debt_UST_tx = Anchor_repay_debt_UST(
                        get_native_balance('uusd') - general_estimated_tx_fee)
                    Anchor_repay_debt_UST_tx_status = get_status_of_tx(
                        Anchor_repay_debt_UST_tx)

                    if Anchor_repay_debt_UST_tx_status:
                        default_logger.debug(
                            f'Success TX: {Anchor_repay_debt_UST_tx}.')
                        report_logger.warning(f'YOU NEED TO ACT! There was not enough availabe aUST to withdraw and not enough UST in your wallet to repay your Anchor Borrow.\n'
                                              f'{current_aUST_wallet_balance:.2f} aUST has been withdrawn, and combined with your availabe UST in your wallet, {Anchor_repay_debt_UST_tx:.2f} UST have been repaid to Anchor Borrow.')
                    else:
                        default_logger.warning(f'Failed TX: {Anchor_repay_debt_UST_tx}.\n'
                                               f'Reason: {Anchor_repay_debt_UST_tx_status}')

                else:
                    default_logger.warning(f'Failed TX: {Anchor_withdraw_UST_from_Earn_tx}.\n'
                                           f'Reason: {Anchor_withdraw_UST_from_Earn_tx_status}')
            else:
                default_logger.debug(
                    f'Skipped because disabled by config Anchor_enable_withdraw_of_deposited_UST({config.Anchor_enable_withdraw_of_deposited_UST}) or Anchor_enable_partially_repay_if_not_enough_UST_in_wallet ({config.Anchor_enable_partially_repay_if_not_enough_UST_in_wallet}).')
        else:
            default_logger.debug(
                f'Skipped because nothing to repay ({Anchor_action_to_be_executed}) or repay amount ({Anchor_amount_to_execute_in_ust:.2f}) below repay limit ({config.Anchor_min_repay_limit:.2f}).')

        # Anchor: Borrow more UST if possible, allowed, big enough and enough balance for tx fees is available
        default_logger.debug("---- Anchor Borrow more ----")
        if Anchor_action_to_be_executed == 'borrow' \
                and Anchor_amount_to_execute_in_ust > config.Anchor_min_borrow_limit \
                and current_UST_wallet_balance > general_estimated_tx_fee:
            # Check if we are in a cooldown period
            if cooldowns['Anchor_borrow_cooldown'] <= date_today:

                Anchor_borrow_more_UST_tx = Anchor_borrow_more_UST(
                    Anchor_amount_to_execute_in_ust)
                Anchor_borrow_more_UST_tx_status = get_status_of_tx(
                    Anchor_borrow_more_UST_tx)

                if Anchor_borrow_more_UST_tx_status:
                    default_logger.debug(
                        f'Success TX: {Anchor_borrow_more_UST_tx}.')
                    report_logger.info(
                        f'{Anchor_amount_to_execute_in_ust:.2f} UST more has been borrowed from Anchor Borrow.')
                    UST_balance_to_be_deposited_at_Anchor_Earn += Anchor_amount_to_execute_in_ust
                    default_logger.debug(
                        f'UST_balance_to_be_deposited_at_Anchor_Earn: {UST_balance_to_be_deposited_at_Anchor_Earn}.')

                    # Write date of today into cooldown dictionary
                    cooldowns['Anchor_borrow_cooldown'] = date_today + \
                        timedelta(days=config.Anchor_borrow_cooldown)
                    if config.Anchor_borrow_cooldown > 0:
                        report_logger.info(
                            f'Cooldown limit has been activated. Next Anchor deposit will be possible on {date_today + timedelta(days=config.Anchor_borrow_cooldown)}')

                else:
                    default_logger.warning(f'Failed TX: {Anchor_borrow_more_UST_tx}.\n'
                                           f'Reason: {Anchor_borrow_more_UST_tx_status}')
            else:
                default_logger.debug(
                    f'Skipped as we are in a cooldown period until ({cooldowns["Anchor_borrow_cooldown"]}).')
        else:
            default_logger.debug(
                f'Skipped because nothing to borrow ({Anchor_action_to_be_executed}), borrow amount ({Anchor_amount_to_execute_in_ust:.2f}) below repay limit ({config.Anchor_min_borrow_limit:.2f}) or not enough funds for the transaction ({(current_UST_wallet_balance - general_estimated_tx_fee):.2d}).')

        # Anchor: Deposit UST from previous claim/sale of reward tokens into Anchor to get more aUST
        default_logger.debug("---- Anchor Deposit UST ----")
        if config.Anchor_enable_deposit_borrowed_UST \
                and UST_balance_to_be_deposited_at_Anchor_Earn >= config.Anchor_min_deposit_amount:

            Anchor_deposit_UST_for_Earn_tx = Anchor_deposit_UST_for_Earn(
                UST_balance_to_be_deposited_at_Anchor_Earn)
            Anchor_deposit_UST_for_Earn_tx_status = get_status_of_tx(
                Anchor_deposit_UST_for_Earn_tx)

            if Anchor_deposit_UST_for_Earn_tx_status:
                default_logger.debug(
                    f'Success TX: {Anchor_deposit_UST_for_Earn_tx}.')
                report_logger.info(
                    f'{UST_balance_to_be_deposited_at_Anchor_Earn:.2f} UST have been deposited to Anchor Earn.')
            else:
                default_logger.warning(f'Failed TX: {Anchor_deposit_UST_for_Earn_tx}.\n'
                                       f'Reason: {Anchor_deposit_UST_for_Earn_tx_status}')
        else:
            default_logger.debug(
                f'Skipped because disabled by config ({config.Anchor_enable_deposit_borrowed_UST} or deposit amount ({UST_balance_to_be_deposited_at_Anchor_Earn:.2f}) below deposit limit ({config.Anchor_min_deposit_amount:.2f})')
    #-------------------------------------------
    #---------- MIRROR SHORTS SECTION ----------
    #-------------------------------------------

        default_logger.debug("---- Mirror Short Section ----")
        for position in Mirror_position_info:
            action_to_be_executed = position['action_to_be_executed']
            # Check if position is marked for a withdraw
            if (action_to_be_executed == 'withdraw'):
                position_idx = position['position_idx']
                amount_to_execute_in_ust = position["amount_to_execute_in_ust"]
                amount_to_execute_in_kind = position['amount_to_execute_in_kind']
                collateral_token_denom = position['collateral_token_denom']

                # Check if a cooldown is in the cooldowns and if it is still relevant
                if cooldowns[position_idx] <= date_today:

                    Mirror_withdraw_collateral_for_position_tx = Mirror_withdraw_collateral_for_position(
                        position_idx, amount_to_execute_in_kind, collateral_token_denom)
                    Mirror_withdraw_collateral_for_position_tx_status = get_status_of_tx(
                        Mirror_withdraw_collateral_for_position_tx)

                    if Mirror_withdraw_collateral_for_position_tx_status:
                        default_logger.debug(
                            f'Success TX: {Mirror_withdraw_collateral_for_position_tx}.')
                        report_logger.info(
                            f'{amount_to_execute_in_kind:.2f} {collateral_token_denom:.2f} with a value of {amount_to_execute_in_ust:.2f} UST of collateral have been withdrawn from your short position idx {position["position_idx"]}.')
                        # Write date of today into cooldown dictionary
                        cooldowns[position_idx] = date_today + \
                            timedelta(days=config.Mirror_withdraw_cooldown)
                        if config.Mirror_withdraw_cooldown > 0:
                            report_logger.info(
                                f'Cooldown limit has been activated. Next withdraw for short position idx {position["position_idx"]} will be possible on {date_today + timedelta(days=config.Mirror_withdraw_cooldown)}')
                    else:
                        default_logger.warning(f'Failed TX: {Mirror_withdraw_collateral_for_position_tx}.\n'
                                               f'Reason: {Mirror_withdraw_collateral_for_position_tx_status}')
                else:
                    default_logger.debug(
                        f'Skipped as we are in a cooldown period until ({cooldowns[position_idx]}) for position idx ({position_idx}).')
            # Check if position has a deposit pending and if the deposit amount if big enough
            elif action_to_be_executed == 'deposit' \
                    and amount_to_execute_in_kind > config.Mirror_min_deposit_limit:

                # Depending on the collateral token required, check if enough balance of the in-kind token is in your wallet
                # and enough UST for the transaction fee
                current_UST_wallet_balance = get_native_balance('uusd')
                if collateral_token_denom == 'aUST':
                    available_balance = get_aUST_balance()
                    enough_balance = available_balance >= amount_to_execute_in_kind and current_UST_wallet_balance > fee_estimation
                elif collateral_token_denom == 'uluna':
                    available_balance = get_native_balance(
                        collateral_token_denom)
                    enough_balance = available_balance >= amount_to_execute_in_kind and current_UST_wallet_balance > fee_estimation
                elif collateral_token_denom == 'uusd':
                    available_balance = current_UST_wallet_balance
                    enough_balance = available_balance >= amount_to_execute_in_kind + fee_estimation
                else:
                    default_logger.debug(
                        f'You discovered a new collateral_token_denom. Congratulations! Please post this as an issue on my Github, so I can fix it. Thank you!')

                if enough_balance:
                    # If you have enough balance then deposit collateral
                    Mirror_deposit_collateral_for_position_tx = Mirror_deposit_collateral_for_position(
                        position_idx, amount_to_execute_in_kind, collateral_token_denom)
                    Mirror_deposit_collateral_for_position_tx_status = get_status_of_tx(
                        Mirror_deposit_collateral_for_position_tx)

                    if Mirror_deposit_collateral_for_position_tx_status:
                        default_logger.debug(
                            f'Success TX: {Mirror_deposit_collateral_for_position_tx}.')
                        report_logger.info(
                            f'{amount_to_execute_in_kind:.2f} {collateral_token_denom:.2f} with a value of {amount_to_execute_in_ust:.2f} UST of collateral have been deposited to your short position idx {position["position_idx"]}.')
                    else:
                        default_logger.warning(f'Failed TX: {Mirror_deposit_collateral_for_position_tx}.\n'
                                               f'Reason: {Mirror_deposit_collateral_for_position_tx_status}')
                else:
                    # If you have NOT enough balance then deposit what is possible
                    Mirror_deposit_collateral_for_position_tx = Mirror_deposit_collateral_for_position(
                        position_idx, available_balance, collateral_token_denom)
                    Mirror_deposit_collateral_for_position_tx_status = get_status_of_tx(
                        Mirror_deposit_collateral_for_position_tx)

                    if Mirror_deposit_collateral_for_position_tx_status:
                        default_logger.debug(
                            f'Success TX: {Mirror_deposit_collateral_for_position_tx}.')
                        report_logger.warning(f'YOU NEED TO ACT! There was not enough availabe {collateral_token_denom:.2f} in your wallet to deposit your short position {position_idx} on Mirror.\n'
                                              f'{available_balance:.2f} {collateral_token_denom:.2f} from your wallet, has been deposited in your short position {position_idx} on Mirror.')
                    else:
                        default_logger.warning(f'Failed TX: {Mirror_deposit_collateral_for_position_tx}.\n'
                                               f'Reason: {Mirror_deposit_collateral_for_position_tx_status}')

            elif action_to_be_executed == 'none':
                default_logger.debug(
                    f'There was nothing to do with position {position_idx}. Good :).')
            else:
                default_logger.warning(
                    f'Something went wrong with position {position_idx} and action {action_to_be_executed}.')

        # Write cooldowns to file
        write_cooldown(cooldowns)

    except LCDResponseError as err:
        default_logger.error(err)

    # Notify user
        report_content = report_array.getvalue()
        print(report_array.getvalue())
        if config.Send_me_a_report and not config.Debug_mode:
            if config.Notify_slack:
                slack_webhook(report_content)
            if config.Notify_Telegram:
                telegram_notification(report_content)
            if config.Notify_Email:
                email_notification(config.email_subject, report_content)


if __name__ == '__main__':
    keep_safe = keep_safe()
    if not keep_safe:
        print('Oh no!!! Something went wrong!')
        default_logger.error(
            'Something went wrong! - keep_safe() returned empty.')
    else:
        print(f'Script ran perfectly!')