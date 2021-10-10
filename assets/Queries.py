#!/usr/bin/python3

# Terra SDK
from terra_sdk.core.coins import Coin
from terra_sdk.core.numeric import Dec

# Other assets
from assets.Terra import Terra
import B_Config as config
 
# Other imports
from datetime import datetime
from time import mktime
import time
import requests
from decimal import Decimal

Terra_class = Terra()
account_address = Terra_class.account_address

class Queries:
    def __init__(self):

        self.all_rates = self.get_all_rates()

    def get_all_rates(self):
    
        all_rates = requests.get('https://api.extraterrestrial.money/v1/api/prices').json()
        all_rates = {**all_rates.pop('prices'), **all_rates}

        return all_rates
    
    def get_fee_estimation(self):
        estimation = Terra_class.terra.treasury.tax_cap('uusd')
        fee = int(estimation.to_data().get('amount'))
        return int(fee) # returns the gas price in satoshis - means 1490000 for 1.49 UST 

    def get_ANC_rate(self):

        if config.NETWORK == 'MAINNET':
            SPEC_rate = self.all_rates['ANC']['price']
        else:
            SPEC_rate = 1
        return SPEC_rate

    def get_MIR_rate(self):

        if config.NETWORK == 'MAINNET':
            MIR_rate = self.all_rates['MIR']['price']
        else:
            MIR_rate = 1
        return MIR_rate

    def get_SPEC_rate(self):

        if config.NETWORK == 'MAINNET':
            SPEC_rate = self.all_rates['SPEC']['price']
        else:
            SPEC_rate = 1
        return SPEC_rate

    def get_aUST_rate(self):

        if config.NETWORK == 'MAINNET':
            aUST_rate = self.all_rates['aUST']['price']
        else:
            query = {
                "epoch_state": {},
            }
            query_result = Terra_class.terra.wasm.contract_query(Terra_class.mmMarket, query)

            aUST_rate = Decimal(query_result['exchange_rate'])
        return aUST_rate


    def get_uluna_rate(self):

        if config.NETWORK == 'MAINNET':
            uluna_rate = self.all_rates['LUNA']['price']
        else:
            uluna_rate = Decimal(str(Terra_class.terra.market.swap_rate(Coin('uluna', 1000000), 'uusd')).replace('uusd', '')) / 1000000

        return uluna_rate


    def get_luna_col_multiplier(self):

        query = {
            "collateral_price": {
                "asset": "uluna"
            }
        }
        query_result = Terra_class.terra.wasm.contract_query(Terra_class.Collateral_Oracle, query)

        get_luna_col_multiplier = Decimal(query_result['multiplier'])

        return get_luna_col_multiplier


    def get_latest_block(self):
        result = Terra_class.terra.tendermint.block_info()
        height = result['block']['header']['height']
        return int(height)


    def get_native_balance(self, denom):
        native_balance = 0
        balance_native = Terra_class.terra.bank.balance(address=account_address)
        try:
            native_balance = str(balance_native[denom]).replace(denom, '')
        except:
            native_balance = 0

        return Decimal(native_balance) / 1000000


    def get_aUST_balance(self):

        query = {
            "balance": {
                "address": account_address
            },
        }
        query_result = Terra_class.terra.wasm.contract_query(Terra_class.aTerra, query)
        balance = query_result['balance']

        return Decimal(balance) / 1000000


    def get_oracle_price_and_min_col_ratio(self, mAsset):
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
        position_ids_result = Terra_class.terra.wasm.contract_query(Terra_class.Collateral_Oracle, query_oracle_price)

        # Minimal collateral ratio
        # mBABA
        # https://tequila-fcd.terra.dev/wasm/contracts/terra1s9ehcjv0dqj2gsl72xrpp0ga5fql7fj7y3kq3w/store?query_msg={"asset_config":{"asset_token":"terra15dr4ah3kha68kam7a907pje9w6z2lpjpnrkd06"}}

        query_oracle_price = {
            "asset_config": {
                "asset_token": mAsset
            },
        }
        min_col_ratio_result = Terra_class.terra.wasm.contract_query(Terra_class.Mint, query_oracle_price)

        oracle_price_and_min_col_ratio = [Decimal(position_ids_result['rate']), Decimal(min_col_ratio_result['min_collateral_ratio'])]

        return oracle_price_and_min_col_ratio


    def Mirror_get_position_info(self):
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
        position_ids_result = Terra_class.terra.wasm.contract_query(Terra_class.Mint, query_position_ids)

        for position in position_ids_result['positions']:

            # There are currently three tokens that can be used as collateral Luna, UST, aUST, so we need to find out which one is used for each position_idx.
            position_idx = position['idx']
            try:
                # for aUST = terra1hzh9vpxhsk8253se0vv5jj6etdvxu3nv8z07zu/terra1ajt556dpzvjwl0kl5tzku3fc3p3knkg9mkv8jl
                if position['collateral']['info']['token']['contract_addr'] == Terra_class.aTerra:
                    collateral_token_denom = 'aUST'
            except:
                # for uluna / uusd
                # If this throws an exception it is because your collaterial is not in UST or Luna. Ignore that exception.
                collateral_token_denom = position['collateral']['info']['native_token']['denom']

            # This value is returned from the blockchain in-kind.
            collateral_amount_in_kind = Decimal(position['collateral']['amount']) / 1000000

            # As the mAsset is valued in UST, we convert the colateral_amount also into UST here.
            if collateral_token_denom == 'aUST':
                collateral_amount_in_ust = collateral_amount_in_kind * Decimal(self.get_aUST_rate())
            elif collateral_token_denom == 'uluna':
                collateral_amount_in_ust = collateral_amount_in_kind * Decimal(self.get_uluna_rate())
            elif collateral_token_denom == 'uusd':
                collateral_amount_in_ust = collateral_amount_in_kind

            shorted_asset_qty = Decimal(position['asset']['amount']) / 1000000
            mAsset_address = position['asset']['info']['token']['contract_addr']

            try:
                mAsset_symbol = Terra_class.rev_Contract_addresses[mAsset_address]
            except:
                mAsset_symbol = 'Not in assets.Contact_addresses.py'

            oracle_price_and_min_col_ratio = self.get_oracle_price_and_min_col_ratio(mAsset_address)
            oracle_price = oracle_price_and_min_col_ratio[0]
            shorted_asset_amount = oracle_price_and_min_col_ratio[0] * shorted_asset_qty

            # If the collateral is provided in UST or aUST the min_col_ratio is as received form the query.
            # if the colalteral is Luna it is luna_col_multiplier (4/3) of the min_col_ratio
            if collateral_token_denom == 'uluna':
                min_col_ratio = oracle_price_and_min_col_ratio[1] * Decimal(self.get_luna_col_multiplier())
            else:
                min_col_ratio = oracle_price_and_min_col_ratio[1]

            cur_col_ratio = collateral_amount_in_ust / (oracle_price * shorted_asset_qty)
            lower_trigger_ratio = min_col_ratio + Decimal(config.Mirror_lower_distance)
            target_ratio = min_col_ratio + Decimal(config.Mirror_target_distance)
            upper_trigger_ratio = min_col_ratio + Decimal(config.Mirror_upper_distance)

            collateral_loss_to_liq = -(shorted_asset_amount * min_col_ratio / collateral_amount_in_ust) + 1
            shorted_mAsset_gain_to_liq = (collateral_amount_in_ust / min_col_ratio / shorted_asset_amount) - 1

            distance_to_min_col = cur_col_ratio - min_col_ratio

            if cur_col_ratio < lower_trigger_ratio \
                    and config.Mirror_enable_deposit_collateral:
                action_to_be_executed = 'deposit'
                # Calculate how much in-kind to withdraw to return to the desired ratio, even if the collaterial is not in UST
                # v This is how much collateral is already in
                amount_to_execute_in_ust = target_ratio * shorted_asset_amount - collateral_amount_in_ust
                # ^ This is how much absolut collateral in UST is required to get the desired target_ratio
                # Quick rule of three
                amount_to_execute_in_kind = (
                    collateral_amount_in_kind / collateral_amount_in_ust) * amount_to_execute_in_ust

            elif cur_col_ratio > upper_trigger_ratio \
                    and config.Mirror_enable_withdraw_collateral:
                action_to_be_executed = 'withdraw'
                # Calculate how much in-kind to withdraw to return to the desired ratio, even if the collaterial is not in UST
                # v This is how much collateral is already in
                amount_to_execute_in_ust = collateral_amount_in_ust - target_ratio * shorted_asset_amount
                # ^ This is how much absolut collateral in UST is required to get the desired target_ratio
                # Quick rule of three
                amount_to_execute_in_kind = (collateral_amount_in_kind / collateral_amount_in_ust) * amount_to_execute_in_ust

            else:
                action_to_be_executed = 'none'
                amount_to_execute_in_kind = 0
                amount_to_execute_in_ust = 0

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
                'collateral_loss_to_liq' : collateral_loss_to_liq,
                'shorted_mAsset_gain_to_liq': shorted_mAsset_gain_to_liq,
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


    def get_claimable_MIR(self):
        # Input: -
        # Output: Returns the quantity of MIR that can be claimed
        claimable = 0

        query = {
            "reward_info": {
                "staker_addr": account_address
            },
        }

        query_result = Terra_class.terra.wasm.contract_query(Terra_class.Staking, query)

        # Sum up all claimable rewards for this account_address
        for reward in query_result['reward_infos']:
            claimable += int(reward['pending_reward'])

        return Decimal(claimable) / 1000000


    def get_claimable_SPEC(self):
        # Input: -
        # Output: Returns the quantity of SPEC that can be claimed
        claimable_mirrorFarm = \
        claimable_anchorFarm = \
        claimable_specFarm = \
        claimable_pylonFarm = 0

        latest_block = self.get_latest_block()

        # Query for the Mirror related claimable SPEC
        query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }
        query_result_mirrorFarm = Terra_class.terra.wasm.contract_query(Terra_class.mirrorFarm, query)
        # print(f'mirrorFarm: {query_result_mirrorFarm}')
        # Sum up all claimable rewards for this account_address
        for reward in query_result_mirrorFarm['reward_infos']:
            claimable_mirrorFarm += int(reward['pending_spec_reward'])

        # Query for the Anchor related claimable SPEC
        query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }
        query_result_anchorFarm = Terra_class.terra.wasm.contract_query(Terra_class.anchorFarm, query)
        # print(f'anchorFarm: {query_result_anchorFarm}')
        # Sum up all claimable rewards for this account_address
        for reward in query_result_anchorFarm['reward_infos']:
            claimable_anchorFarm += int(reward['pending_spec_reward'])

        # Query for the Spec related claimable SPEC
        query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }
        query_result_specFarm = Terra_class.terra.wasm.contract_query(Terra_class.specFarm, query)
        # print(f'specFarm: {query_result_specFarm}')
        # Sum up all claimable rewards for this account_address
        for reward in query_result_specFarm['reward_infos']:
            claimable_specFarm += int(reward['pending_spec_reward'])

        # Query for the Pylon related claimable SPEC
        query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }
        query_result_pylonFarm = Terra_class.terra.wasm.contract_query(Terra_class.pylonFarm, query)
        # print(f'pylonFarm: {query_result_pylonFarm}')
        # Sum up all claimable rewards for this account_address
        for reward in query_result_pylonFarm['reward_infos']:
            claimable_pylonFarm += int(reward['pending_spec_reward'])

        # claimable_SPEC_dict = {
        #     "claimable_mirrorFarm": Decimal(claimable_mirrorFarm)/1000000,
        #     "claimable_anchorFarm": Decimal(claimable_anchorFarm)/1000000,
        #     "claimable_specFarm": Decimal(claimable_specFarm)/1000000,
        #     "claimable_pylonFarm": Decimal(claimable_pylonFarm)/1000000,
        # }

        claimable_SPEC_list = [
            Decimal(
            +claimable_mirrorFarm \
            +claimable_anchorFarm\
            +claimable_specFarm \
            +claimable_pylonFarm
            ) / 1000000,
            claimable_mirrorFarm >0,
            claimable_anchorFarm >0,
            claimable_specFarm >0,
            claimable_pylonFarm >0,
        ]

        return claimable_SPEC_list


    def get_claimable_ANC(self):
        # Input: -
        # Output: Returns the quantity of ANC that can be claimed
        claimable = 0
        latest_block = self.get_latest_block()

        query = {
            "borrower_info": {
                "borrower": account_address,
                "block_height": latest_block
            }
        }

        query_result = Terra_class.terra.wasm.contract_query(Terra_class.mmMarket, query)

        claimable = Decimal(query_result['pending_rewards']) / 1000000

        return claimable


    def Mirror_get_claimable_UST(self, Mirror_position_info):
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
                
                # Status code 500 means, that there is no unclaimed UST. If so, this exception can be ignored.             
                query_result = Terra_class.terra.wasm.contract_query(Terra_class.Lock, query)

                locked_amount = Decimal(query_result['locked_amount'])
                unlock_time = Decimal(query_result['unlock_time'])
                if unlock_time < int(datetime.utcnow().timestamp()):
                    claimable += locked_amount
                
            except:
                # If a short position has already been claimed, this query will result in an error. We catch it here.
                claimable = 0

        return Decimal(claimable) / 1000000


    def simulate_MIR_Swap(self, amount):
        # Input: Amount of MIR
        # Output: Value of input-MIR at current market price in UST
        # https://fcd.terra.dev/wasm/contracts/terra1tn8ejzw8kpuc87nu42f6qeyen4c7qy35tl8t20/store?query_msg={"simulation":{"offer_asset":{"amount":"1000000","info":{"token":{"contract_addr":"terra1s5eczhe0h0jutf46re52x5z4r03c8hupacxmdr"}}}}}

        query = {
            "simulation": {
                "offer_asset": {
                    "amount": str(int(amount * 1000000)),
                    "info": {
                        "token": {
                            "contract_addr": Terra_class.MIR_token
                        }
                    }
                }
            }
        }
        query_result = Terra_class.terra.wasm.contract_query(Terra_class.Terraswap_MIR_UST_Pair, query)
        MIR_return = Decimal(query_result['return_amount']) / 1000000

        return MIR_return


    def simulate_SPEC_Swap(self, amount):
        # Input: Amount of SPEC
        # Output: Value of input-SPEC at current market price in UST
        # https://fcd.terra.dev/wasm/contracts/terra1tn8ejzw8kpuc87nu42f6qeyen4c7qy35tl8t20/store?query_msg={"simulation":{"offer_asset":{"amount":"1000000","info":{"token":{"contract_addr":"terra1s5eczhe0h0jutf46re52x5z4r03c8hupacxmdr"}}}}}

        query = {
            "simulation": {
                "offer_asset": {
                    "amount": str(int(amount * 1000000)),
                    "info": {
                        "token": {
                            "contract_addr": Terra_class.SPEC_token
                        }
                    }
                }
            }
        }
        query_result = Terra_class.terra.wasm.contract_query(Terra_class.Spectrum_SPEC_UST_Pair, query)
        SPEC_return = Decimal(query_result['return_amount']) / 1000000

        return SPEC_return


    def simulate_ANC_Swap(self, amount):
        # Input: Amount of ANC
        # Output: Value of input-ANC at current market price in UST
        query = {
            "simulation": {
                "offer_asset": {
                    "amount": str(int(amount * 1000000)),
                    "info": {
                        "token": {
                            "contract_addr": Terra_class.ANC_token
                        }
                    }
                }
            }
        }
        query_result = Terra_class.terra.wasm.contract_query(Terra_class.Terraswap_ANC_UST_Pair, query)
        ANC_return = Decimal(query_result['return_amount']) / 1000000

        return ANC_return


    def Anchor_get_max_ltv_ratio(self):

        max_ltv_ratio = {}

        query = {
            "whitelist": {},
        }
        query_result = Terra_class.terra.wasm.contract_query(Terra_class.mmOverseer, query)

        for elem in query_result['elems']:
            max_ltv_ratio[elem['symbol']] = Decimal(elem['max_ltv'])

        return max_ltv_ratio


    def Anchor_get_borrow_info(self):
        # Input: -
        # Output: Collects, calculated all there is required to know for your Anchor debt

        max_ltv_ratio = Decimal(self.Anchor_get_max_ltv_ratio()['BETH'])

        query_msg_borrow_limit = {
            "borrow_limit": {
                "borrower": account_address
            },
        }
        borrow_limit_result = Terra_class.terra.wasm.contract_query(Terra_class.mmOverseer, query_msg_borrow_limit)

        borrow_limit = Decimal(borrow_limit_result['borrow_limit']) / 1000000

        # Check if you actually have some collateral in Anchor
        if borrow_limit > 0:
           
            query_msg_collateral = {
                "collaterals": {
                    "borrower": account_address
                },
            }
            query_msg_collateral_result = Terra_class.terra.wasm.contract_query(Terra_class.mmOverseer, query_msg_collateral)

            query_msg_loan = {
                "borrower_info": {
                    "borrower": account_address,
                    "block_height": self.get_latest_block()
                },
            }
            loan_amount_result = Terra_class.terra.wasm.contract_query(Terra_class.mmMarket, query_msg_loan)

            loan_amount = Decimal(loan_amount_result['loan_amount']) / 1000000

            collateral_dict = {}
            for collateral in query_msg_collateral_result['collaterals']:
                collateral_dict[collateral[0]] = collateral[1]

            if collateral_dict.get(Terra_class.bETH_token) is not None:
                amount_bETH_collateral = Decimal(collateral_dict[Terra_class.bETH_token]) / 1000000
            else:
                amount_bETH_collateral = 0

            if collateral_dict.get(Terra_class.bLuna_token) is not None:
                amount_bLuna_collateral = Decimal(collateral_dict[Terra_class.bLuna_token]) / 1000000
            else:
                amount_bLuna_collateral = 0

            total_collateral_value = borrow_limit / max_ltv_ratio
            cur_col_ratio = loan_amount / borrow_limit * max_ltv_ratio
            lower_trigger_ratio = max_ltv_ratio + Decimal(config.Anchor_lower_distance)
            upper_trigger_ratio = max_ltv_ratio + Decimal(config.Anchor_upper_distance)
            distance_to_max_ltv = cur_col_ratio - max_ltv_ratio

            collateral_loss_to_liq = -(loan_amount / max_ltv_ratio / total_collateral_value) + 1

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
                'amount_bETH_collateral': amount_bETH_collateral,
                'amount_bLuna_collateral': amount_bLuna_collateral,
                'total_collateral_value': total_collateral_value,
                'borrow_limit': borrow_limit,
                'cur_col_ratio': cur_col_ratio,
                'lower_trigger_ratio': lower_trigger_ratio,
                'upper_trigger_ratio': upper_trigger_ratio,
                'distance_to_max_ltv': distance_to_max_ltv,
                'collateral_loss_to_liq':collateral_loss_to_liq,
                'action_to_be_executed': action_to_be_executed,
                'amount_to_execute_in_ust': amount_to_execute_in_ust
            }
            
        else:
            Anchor_debt_info = {
                'loan_amount': 0,
                'amount_bETH_collateral': 0,
                'amount_bLuna_collateral': 0,
                'total_collateral_value': 0,
                'borrow_limit': borrow_limit,
                'cur_col_ratio': 0,
                'lower_trigger_ratio': 0,
                'upper_trigger_ratio': 0,
                'distance_to_max_ltv': 0,
                'collateral_loss_to_liq':0,
                'action_to_be_executed': 'none',
                'amount_to_execute_in_ust': 0
            }

        return Anchor_debt_info

    def get_status_of_tx(self, tx_hash):
    # Input: Transaction hash
    # Output: If the Transaction was successful returns True, otherwise the reason why it failed
    
        if config.Disable_all_transaction_defs:
            if config.Return_failed_tx:
                return "Dummy reason for failed tx"
            else:
                return True

        # Since we need to wait a bit for the transaction we add a delay here. That way we make sure that the transaction before had time to go through.
        time.sleep(15)

        try:
            status = Terra_class.terra.tx.tx_info(tx_hash).code
            if not status:
                return True
            else:
                # If status 404 cannot be found, most likely the gas fee for the transaction before was too low. So it was never executed on Terra.
                return Terra_class.terra.tx.tx_info(tx_hash).rawlog
        except:
            return 'Status query of tx failed!'

    def market_hours(self):

        # Oracle query mAPPL
        # https://fcd.terra.dev/wasm/contracts/terra1t6xe0txzywdg85n6k8c960cuwgh6l8esw6lau9/store?query_msg={"price":{"base_asset":"terra1vxtwu4ehgzz77mnfwrntyrmgl64qjs75mpwqaz","quote_asset":"uusd"}}
        # 
        # Oracle query mBTC
        # https://fcd.terra.dev/wasm/contracts/terra1t6xe0txzywdg85n6k8c960cuwgh6l8esw6lau9/store?query_msg={"price":{"base_asset":"terra1rhhvx8nzfrx5fufkuft06q5marfkucdqwq5sjw","quote_asset":"uusd"}}
        
        # If the query for mAAPL returns a last_updated_base that is older than 2min, it will assume the market is closed        
        # https://www.nasdaq.com/stock-market-trading-hours-for-nasdaq

        query = {
            "price": {
                "base_asset": Terra_class.mAAPL_token,
                "quote_asset":"uusd"
            }
        }
        query_result = Terra_class.terra.wasm.contract_query(Terra_class.Oracle, query)

        unix_last_price_update = query_result['last_updated_base']
        unix_now = mktime(datetime.now().timetuple())

        time_difference = unix_now - unix_last_price_update

        if time_difference < 120: # 2 min = 60*2 = 120 seconds
            return True
        else:
            return False