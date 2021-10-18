#!/usr/bin/python3

# Terra SDK
from terra_sdk.core.coins import Coin
from terra_sdk.core.numeric import Dec
from terra_sdk.exceptions import LCDResponseError

# Other assets
from assets.Terra import Terra
from assets.Logging import Logger
import B_Config as config
 
# Other imports
from datetime import datetime
from time import mktime, sleep
from requests import get
from re import search

account_address = Terra.account_address

class Queries:
    if config.Debug_mode: print(f'Queries Class loaded.')
    default_logger = Logger().default_logger

    def __init__(self):
        self.all_rates = self.get_all_rates()

        
    def get_all_rates(self):

        all_rates:dict
        all_rates = {}
        
        all_rates['LUNA'] = Dec(str(Terra.terra.market.swap_rate(Coin('uluna', 1000000), 'uusd')).replace('uusd', ''))

        query = {
            "epoch_state": {},
        }
        query_result = Terra.terra.wasm.contract_query(Terra.mmMarket, query)
        
        all_rates['aUST'] = Dec(query_result['exchange_rate']) * 1000000

        # Update ANC, MIR, SPEC as those prices are critical to be up-to-date
        all_rates['MIR'] = Dec(self.get_swap_price(Terra.Mirror_MIR_UST_Pair) * 1000000)
        all_rates['SPEC'] = Dec(self.get_swap_price(Terra.Spectrum_SPEC_UST_Pair) * 1000000)
        all_rates['ANC'] = Dec(self.get_swap_price(Terra.Terraswap_ANC_UST_Pair) * 1000000)
        return all_rates

    def get_fee_estimation(self):

        estimation = Terra.terra.treasury.tax_cap('uusd')
        fee = estimation.to_data().get('amount')
        return Dec(fee)

    def get_swap_price(self, token_UST_pair_address:str):

        # Get the terra swap price from the pool
        # https://bombay-lcd.terra.dev/wasm/contracts/terra15cjce08zcmempedxwtce2y44y2ayup8gww3txr/store?query_msg={"pool":{}}

        query = {
            "pool": {}
        }

        query_result = Terra.terra.wasm.contract_query(token_UST_pair_address, query)
        for asset in query_result['assets']:
            # If ['info']['token'] does not exists, the current asset is uusd
            if asset['info'].get('token') is None:
                UST_in_pool = Dec(asset['amount'])

            # Otherwise it is the token
            else:
                token_in_pool = Dec(asset['amount'])
        Swap_price = UST_in_pool / token_in_pool

        return Dec(Swap_price)



    def get_luna_col_multiplier(self):

        query = {
            "collateral_price": {
                "asset": "uluna"
            }
        }
        query_result = Terra.terra.wasm.contract_query(Terra.Collateral_Oracle, query)

        get_luna_col_multiplier = query_result['multiplier']

        return Dec(get_luna_col_multiplier)


    def get_latest_block(self):
        result = Terra.terra.tendermint.block_info()
        height = result['block']['header']['height']
        return int(height)

    def get_oracle_price_and_min_col_ratio(self, mAsset:str):
        oracle_price_and_min_col_ratio:list
        query_oracle_price = {
            "collateral_price": {
                "asset": mAsset
            },
        }
        position_ids_result = Terra.terra.wasm.contract_query(Terra.Collateral_Oracle, query_oracle_price)

        query_oracle_price = {
            "asset_config": {
                "asset_token": mAsset
            },
        }
        min_col_ratio_result = Terra.terra.wasm.contract_query(Terra.Mint, query_oracle_price)

        oracle_price_and_min_col_ratio = [Dec(position_ids_result['rate']), Dec(min_col_ratio_result['min_collateral_ratio'])]

        return oracle_price_and_min_col_ratio


    def Mirror_get_position_info(self):
        Mirror_position_info:list
        Mirror_position_info= []

        query_position_ids = {
            "positions": {
                "owner_addr": account_address
            },
        }
        position_ids_result = Terra.terra.wasm.contract_query(Terra.Mint, query_position_ids)

        for position in position_ids_result['positions']:

            # There are currently three tokens that can be used as collateral Luna, UST, aUST, so we need to find out which one is used for each position_idx.
            position_idx = position['idx']
            
            # if denom exists, its means the collateral_token is either uusd or uluna
            if 'native_token' in position['collateral']['info']:
                collateral_token_denom = position['collateral']['info']['native_token']['denom']
            else:
                if position['collateral']['info']['token']['contract_addr'] == Terra.aTerra:
                    collateral_token_denom = 'aUST'
                else:
                    self.default_logger.warning(f'[Script] The collateral you have here is none of those: UST, aUST, LUNA. The bot cannot handle that.')
            
            # This value is returned from the blockchain in-kind.
            collateral_amount_in_kind = Dec(position['collateral']['amount'])

            # As the mAsset is valued in UST, we convert the colateral_amount also into UST here.
            if collateral_token_denom == 'aUST':
                collateral_amount_in_ust = collateral_amount_in_kind * self.all_rates['aUST'] / 1000000
            elif collateral_token_denom == 'uluna':
                collateral_amount_in_ust = collateral_amount_in_kind * self.all_rates['LUNAs'] / 1000000
            elif collateral_token_denom == 'uusd':
                collateral_amount_in_ust = collateral_amount_in_kind

            shorted_asset_qty = Dec(position['asset']['amount'])
            mAsset_address = position['asset']['info']['token']['contract_addr']

            if mAsset_address in Terra.rev_Contract_addresses.keys():
                mAsset_symbol = Terra.rev_Contract_addresses[mAsset_address]
            else:
                mAsset_symbol = 'Not in assets.Contact_addresses.py'

            oracle_price_and_min_col_ratio = self.get_oracle_price_and_min_col_ratio(mAsset_address)
            oracle_price = oracle_price_and_min_col_ratio[0]
            shorted_asset_amount = oracle_price_and_min_col_ratio[0] * shorted_asset_qty

            # If the collateral is provided in UST or aUST the min_col_ratio is as received form the query.
            # if the colalteral is Luna it is luna_col_multiplier (4/3) of the min_col_ratio
            if collateral_token_denom == 'uluna':
                min_col_ratio = oracle_price_and_min_col_ratio[1] * Dec(self.get_luna_col_multiplier())
            else:
                min_col_ratio = oracle_price_and_min_col_ratio[1]

            cur_col_ratio = collateral_amount_in_ust / (oracle_price * shorted_asset_qty)
            lower_trigger_ratio = min_col_ratio + Dec(config.Mirror_lower_distance)
            target_ratio = min_col_ratio + Dec(config.Mirror_target_distance)
            upper_trigger_ratio = min_col_ratio + Dec(config.Mirror_upper_distance)

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

        # Sort positions by action (withdrawals first)
        def sort_by_action(elem):
            return elem['action_to_be_executed']

        Mirror_position_info.sort(key=sort_by_distance)
        Mirror_position_info.sort(key=sort_by_action, reverse=True)

        return Mirror_position_info


    def get_claimable_MIR(self):
        claimable = 0

        query = {
            "reward_info": {
                "staker_addr": account_address
            },
        }

        query_result = Terra.terra.wasm.contract_query(Terra.MirrorStaking, query)

        # Sum up all claimable rewards for this account_address
        for reward in query_result['reward_infos']:
            claimable += Dec(reward['pending_reward'])

        return Dec(claimable)


    def get_claimable_SPEC(self):
        claimable_SPEC_list:list
        claimable_mirrorFarm = 0
        claimable_anchorFarm = 0
        claimable_specFarm = 0
        claimable_pylonFarm = 0

        latest_block = self.get_latest_block()

        # Query for the Mirror related claimable SPEC
        query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }
        query_result_mirrorFarm = Terra.terra.wasm.contract_query(Terra.mirrorFarm, query)
        # print(f'mirrorFarm: {query_result_mirrorFarm}')
        # Sum up all claimable rewards for this account_address
        for reward in query_result_mirrorFarm['reward_infos']:
            claimable_mirrorFarm += Dec(reward['pending_spec_reward'])

        # Query for the Anchor related claimable SPEC
        query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }
        query_result_anchorFarm = Terra.terra.wasm.contract_query(Terra.anchorFarm, query)
        # print(f'anchorFarm: {query_result_anchorFarm}')
        # Sum up all claimable rewards for this account_address
        for reward in query_result_anchorFarm['reward_infos']:
            claimable_anchorFarm += Dec(reward['pending_spec_reward'])

        # Query for the Spec related claimable SPEC
        query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }
        query_result_specFarm = Terra.terra.wasm.contract_query(Terra.specFarm, query)
        # print(f'specFarm: {query_result_specFarm}')
        # Sum up all claimable rewards for this account_address
        for reward in query_result_specFarm['reward_infos']:
            claimable_specFarm += Dec(reward['pending_spec_reward'])

        # Query for the Pylon related claimable SPEC
        query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }
        query_result_pylonFarm = Terra.terra.wasm.contract_query(Terra.pylonFarm, query)
        # print(f'pylonFarm: {query_result_pylonFarm}')
        # Sum up all claimable rewards for this account_address
        for reward in query_result_pylonFarm['reward_infos']:
            claimable_pylonFarm += Dec(reward['pending_spec_reward'])

        # claimable_SPEC_dict = {
        #     "claimable_mirrorFarm": Dec(claimable_mirrorFarm)/1000000,
        #     "claimable_anchorFarm": Dec(claimable_anchorFarm)/1000000,
        #     "claimable_specFarm": Dec(claimable_specFarm)/1000000,
        #     "claimable_pylonFarm": Dec(claimable_pylonFarm)/1000000,
        # }

        claimable_SPEC_list = [
            +Dec(claimable_mirrorFarm) \
            +Dec(claimable_anchorFarm) \
            +Dec(claimable_specFarm) \
            +Dec(claimable_pylonFarm),
            claimable_mirrorFarm >0,
            claimable_anchorFarm >0,
            claimable_specFarm >0,
            claimable_pylonFarm >0,
        ]

        return claimable_SPEC_list


    def get_claimable_ANC(self):

        latest_block = self.get_latest_block()

        query = {
            "borrower_info": {
                "borrower": account_address,
                "block_height": latest_block
            }
        }

        query_result = Terra.terra.wasm.contract_query(Terra.mmMarket, query)

        claimable = query_result['pending_rewards']

        return Dec(claimable)


    def Mirror_get_claimable_UST(self, Mirror_position_info:list):

        claimable = 0

        # Input: Mirror_position_info
        # Output: Returns the quantity of UST that can be claimed
        # https://docs.mirror.finance/contracts/lock#positionlockinfo

        for position in Mirror_position_info:

            query = {
                "position_lock_info": {
                    "position_idx": position['position_idx']
                }
            }

            try:                                
                query_result = Terra.terra.wasm.contract_query(Terra.Lock, query)
                locked_amount = Dec(query_result['locked_amount'])
                unlock_time = Dec(query_result['unlock_time'])
                now_time = Dec(datetime.now().timestamp())
                if unlock_time < now_time:
                    claimable += locked_amount
            
            except LCDResponseError as err:
                # Status code 500 means, that there is no unclaimed UST. If so, this exception can be ignored
                if err.response.status == 500:
                    pass
                else:
                    raise err

        return Dec(claimable)


    def simulate_Token_Swap(self, token_amount:Dec, token_UST_pair_address:str, token_address:str):

        query = {
            "simulation": {
                "offer_asset": {
                    "amount": str(int(token_amount)),
                    "info": {
                        "token": {
                            "contract_addr": token_address
                        }
                    }
                }
            }
        }
        query_result = Terra.terra.wasm.contract_query(token_UST_pair_address, query)
        UST_return = query_result['return_amount']

        return Dec(UST_return)

    def get_available_LP_token_for_withdrawal(self, token_farm_address:str, token_address:str):
       
        LP_token_available = 0

        query = {
            "reward_info": {
                "staker_addr": account_address, 
            }
        }
        query_result = Terra.terra.wasm.contract_query(token_farm_address, query)

        if not query_result == []:
            for reward_info in query_result['reward_infos']:
                if reward_info['asset_token'] == token_address:
                    LP_token_available = reward_info['bond_amount']        

        return Dec(LP_token_available)

    def get_UST_amount_for_LP_deposit(self, token_amount:Dec, token_UST_pair_address:str):

        Swap_price = self.get_swap_price(token_UST_pair_address)
        tax_rate = Terra.terra.treasury.tax_rate()
        UST_amount = token_amount * (Swap_price + tax_rate)

        return Dec(UST_amount)


    def Anchor_get_max_ltv_ratio(self):
        
        max_ltv_ratio:dict
        max_ltv_ratio = {}

        query = {
            "whitelist": {},
        }
        query_result = Terra.terra.wasm.contract_query(Terra.mmOverseer, query)

        for elem in query_result['elems']:
            max_ltv_ratio[elem['symbol']] = Dec(elem['max_ltv'])

        return max_ltv_ratio


    def Anchor_get_borrow_info(self):
        Anchor_debt_info:dict

        max_ltv_ratio = self.Anchor_get_max_ltv_ratio()['BETH']

        query_msg_borrow_limit = {
            "borrow_limit": {
                "borrower": account_address
            },
        }
        borrow_limit_result = Terra.terra.wasm.contract_query(Terra.mmOverseer, query_msg_borrow_limit)

        borrow_limit = Dec(borrow_limit_result['borrow_limit'])

        # Check if you actually have some collateral in Anchor
        if borrow_limit > 0:
           
            query_msg_collateral = {
                "collaterals": {
                    "borrower": account_address
                },
            }
            query_msg_collateral_result = Terra.terra.wasm.contract_query(Terra.mmOverseer, query_msg_collateral)

            query_msg_loan = {
                "borrower_info": {
                    "borrower": account_address
                },
            }
            loan_amount_result = Terra.terra.wasm.contract_query(Terra.mmMarket, query_msg_loan)

            loan_amount = Dec(loan_amount_result['loan_amount'])

            collateral_dict = {}
            for collateral in query_msg_collateral_result['collaterals']:
                collateral_dict[collateral[0]] = Dec(collateral[1])

            if collateral_dict.get(Terra.bETH_token) is not None:
                amount_bETH_collateral = collateral_dict[Terra.bETH_token]
            else:
                amount_bETH_collateral = 0

            if collateral_dict.get(Terra.bLuna_token) is not None:
                amount_bLuna_collateral = collateral_dict[Terra.bLuna_token]
            else:
                amount_bLuna_collateral = 0

            total_collateral_value = borrow_limit / max_ltv_ratio
            cur_col_ratio = loan_amount / borrow_limit * max_ltv_ratio
            lower_trigger_ratio = max_ltv_ratio + Dec(config.Anchor_lower_distance)
            upper_trigger_ratio = max_ltv_ratio + Dec(config.Anchor_upper_distance)
            distance_to_max_ltv = cur_col_ratio - max_ltv_ratio

            collateral_loss_to_liq = -(loan_amount / max_ltv_ratio / total_collateral_value) + 1

            if cur_col_ratio > lower_trigger_ratio and config.Anchor_enable_auto_repay_of_debt:
                action_to_be_executed = 'repay'
                # Calculate how much aUST to deposite to return to the desired ratio
                amount_to_execute_in_ust = loan_amount - (borrow_limit * (max_ltv_ratio + Dec(config.Anchor_target_distance)) / max_ltv_ratio)
            elif cur_col_ratio < upper_trigger_ratio and config.Anchor_enable_auto_borrow_UST:
                action_to_be_executed = 'borrow'
                # Calculate how much aUST to withdraw to return to the desired ratio
                amount_to_execute_in_ust = (borrow_limit * (max_ltv_ratio + Dec(config.Anchor_target_distance)) / max_ltv_ratio) - loan_amount
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

    def get_status_of_tx(self, tx_hash, retry=0):

        if search("[A-F0-9]{64}", tx_hash) is None:
            return tx_hash

        if config.Disable_all_transaction_defs:
            if config.Return_failed_tx:
                return "Dummy reason for failed tx"
            else:
                return True

        sleep(5)

        try:
            status = Terra.terra.tx.tx_info(tx_hash)
            if status.code is None:
                # Transaction successful
                return True
            else:
                # Transaction failed
                return status.rawlog
        except LCDResponseError as err:
            if err.response.status == 404 and retry < 3:
                retry +=1
                self.get_status_of_tx(tx_hash, retry)
            else:
                return f'Transaction hash could not be found even after multiple retries.'

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
                "base_asset": Terra.mAAPL_token,
                "quote_asset":"uusd"
            }
        }
        query_result = Terra.terra.wasm.contract_query(Terra.Oracle, query)

        unix_last_price_update = query_result['last_updated_base']
        unix_now = mktime(datetime.now().timetuple())

        time_difference = unix_now - unix_last_price_update

        if time_difference < 120: # 2 min = 60*2 = 120 seconds
            return True
        else:
            return False

    def get_native_balance(self, denom:str):
        # Todo: Return a dict with all natives to be incl in the wallet_balance dict provided

        balance_native = Terra.terra.bank.balance(address=account_address).to_data()
        for item in balance_native:
            if item['denom'] == denom:
                return Dec(item['amount'])
        return 0

    def get_non_native_balance(self, token_address):
        # Todo: Return a dict with all natives to be incl in the wallet_balance dict provided
        # curl 'https://bombay-mantle.terra.dev/' -H 'Accept-Encoding: gzip, deflate, br' -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'Connection: keep-alive' -H 'DNT: 1' -H 'Origin: https://bombay-mantle.terra.dev' --data-binary '{"query":"# Write your query or mutation here\n{\n  terra1v000amr8a59r88p33ec2kk9xqe047g7zzqqaf4: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1v000amr8a59r88p33ec2kk9xqe047g7zzqqaf4\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1u0t35drzyy0mujj8rkdyzhe264uls4ug3wdp3x: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1u0t35drzyy0mujj8rkdyzhe264uls4ug3wdp3x\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra19mkj9nec6e3y5754tlnuz4vem7lzh4n0lc2s3l: WasmContractsContractAddressStore(\n    ContractAddress: \"terra19mkj9nec6e3y5754tlnuz4vem7lzh4n0lc2s3l\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1ajt556dpzvjwl0kl5tzku3fc3p3knkg9mkv8jl: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1ajt556dpzvjwl0kl5tzku3fc3p3knkg9mkv8jl\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1747mad58h0w4y589y3sk84r5efqdev9q4r02pc: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1747mad58h0w4y589y3sk84r5efqdev9q4r02pc\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra10llyp6v3j3her8u3ce66ragytu45kcmd9asj3u: WasmContractsContractAddressStore(\n    ContractAddress: \"terra10llyp6v3j3her8u3ce66ragytu45kcmd9asj3u\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra16vfxm98rxlc8erj4g0sj5932dvylgmdufnugk0: WasmContractsContractAddressStore(\n    ContractAddress: \"terra16vfxm98rxlc8erj4g0sj5932dvylgmdufnugk0\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1avryzxnsn2denq7p2d7ukm6nkck9s0rz2llgnc: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1avryzxnsn2denq7p2d7ukm6nkck9s0rz2llgnc\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1zeyfhurlrun6sgytqfue555e6vw2ndxt2j7jhd: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1zeyfhurlrun6sgytqfue555e6vw2ndxt2j7jhd\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra12saaecsqwxj04fn0jsv4jmdyp6gylptf5tksge: WasmContractsContractAddressStore(\n    ContractAddress: \"terra12saaecsqwxj04fn0jsv4jmdyp6gylptf5tksge\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1qk0cd8576fqf33paf40xy3rt82p7yluwtxz7qx: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1qk0cd8576fqf33paf40xy3rt82p7yluwtxz7qx\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra15dr4ah3kha68kam7a907pje9w6z2lpjpnrkd06: WasmContractsContractAddressStore(\n    ContractAddress: \"terra15dr4ah3kha68kam7a907pje9w6z2lpjpnrkd06\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1csr22xvxs6r3gkjsl7pmjkmpt39mwjsrm0e2r8: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1csr22xvxs6r3gkjsl7pmjkmpt39mwjsrm0e2r8\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1qre9crlfnulcg0m68qqywqqstplgvrzywsg3am: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1qre9crlfnulcg0m68qqywqqstplgvrzywsg3am\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1ys4dwwzaenjg2gy02mslmc96f267xvpsjat7gx: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1ys4dwwzaenjg2gy02mslmc96f267xvpsjat7gx\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra14gq9wj0tt6vu0m4ec2tkkv4ln3qrtl58lgdl2c: WasmContractsContractAddressStore(\n    ContractAddress: \"terra14gq9wj0tt6vu0m4ec2tkkv4ln3qrtl58lgdl2c\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra104tgj4gc3pp5s240a0mzqkhd3jzkn8v0u07hlf: WasmContractsContractAddressStore(\n    ContractAddress: \"terra104tgj4gc3pp5s240a0mzqkhd3jzkn8v0u07hlf\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1qg9ugndl25567u03jrr79xur2yk9d632fke3h2: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1qg9ugndl25567u03jrr79xur2yk9d632fke3h2\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra13myzfjdmvqkama2tt3v5f7quh75rv78w8kq6u6: WasmContractsContractAddressStore(\n    ContractAddress: \"terra13myzfjdmvqkama2tt3v5f7quh75rv78w8kq6u6\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra19dl29dpykvzej8rg86mjqg8h63s9cqvkknpclr: WasmContractsContractAddressStore(\n    ContractAddress: \"terra19dl29dpykvzej8rg86mjqg8h63s9cqvkknpclr\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1p50j2k5vyw3q2tgywqvxyz59z8csh9p7x8dk5m: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1p50j2k5vyw3q2tgywqvxyz59z8csh9p7x8dk5m\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1qhkjjlqq2lyf2evzserdaqx55nugksjqdpxvru: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1qhkjjlqq2lyf2evzserdaqx55nugksjqdpxvru\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1374w7fkm7tqhd9dt2r5shjk8ly2kum443uennt: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1374w7fkm7tqhd9dt2r5shjk8ly2kum443uennt\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1anw5z9u5l35vxhhqljuygmkupwmafcv0m86kum: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1anw5z9u5l35vxhhqljuygmkupwmafcv0m86kum\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra19jdmle3zl99gugmptx8auckc9c2xw7nspyxjvx: WasmContractsContractAddressStore(\n    ContractAddress: \"terra19jdmle3zl99gugmptx8auckc9c2xw7nspyxjvx\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra12s2h8vlztjwu440khpc0063p34vm7nhu25w4p9: WasmContractsContractAddressStore(\n    ContractAddress: \"terra12s2h8vlztjwu440khpc0063p34vm7nhu25w4p9\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1djnlav60utj06kk9dl7defsv8xql5qpryzvm3h: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1djnlav60utj06kk9dl7defsv8xql5qpryzvm3h\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra18yx7ff8knc98p07pdkhm3u36wufaeacv47fuha: WasmContractsContractAddressStore(\n    ContractAddress: \"terra18yx7ff8knc98p07pdkhm3u36wufaeacv47fuha\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra14vmf4tzg23fxnt9q5wavlp4wtvzzap82hdq402: WasmContractsContractAddressStore(\n    ContractAddress: \"terra14vmf4tzg23fxnt9q5wavlp4wtvzzap82hdq402\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1hvmzhnhxnyhjfnctntnn49a35w6hvygmxvjt7q: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1hvmzhnhxnyhjfnctntnn49a35w6hvygmxvjt7q\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1fdkfhgk433tar72t4edh6p6y9rmjulzc83ljuw: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1fdkfhgk433tar72t4edh6p6y9rmjulzc83ljuw\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra15t9afkpj0wnh8m74n8n2f8tspkn7r65vnru45s: WasmContractsContractAddressStore(\n    ContractAddress: \"terra15t9afkpj0wnh8m74n8n2f8tspkn7r65vnru45s\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1nslem9lgwx53rvgqwd8hgq7pepsry6yr3wsen4: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1nslem9lgwx53rvgqwd8hgq7pepsry6yr3wsen4\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1ax7mhqahj6vcqnnl675nqq2g9wghzuecy923vy: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1ax7mhqahj6vcqnnl675nqq2g9wghzuecy923vy\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1fucmfp8x4mpzsydjaxyv26hrkdg4vpdzdvf647: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1fucmfp8x4mpzsydjaxyv26hrkdg4vpdzdvf647\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1z0k7nx0vl85hwpv3e3hu2cyfkwq07fl7nqchvd: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1z0k7nx0vl85hwpv3e3hu2cyfkwq07fl7nqchvd\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra18gphn8r437p2xmjpw7a79hgsglf5y4t0x7s5ee: WasmContractsContractAddressStore(\n    ContractAddress: \"terra18gphn8r437p2xmjpw7a79hgsglf5y4t0x7s5ee\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra18py95akdje8q8aaukhx65dplh9342m0j884wt4: WasmContractsContractAddressStore(\n    ContractAddress: \"terra18py95akdje8q8aaukhx65dplh9342m0j884wt4\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1090l5p5v794dpyzr07da72cyexhuc4zag5cuer: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1090l5p5v794dpyzr07da72cyexhuc4zag5cuer\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1jr9s6cx4j637fctkvglrclvrr824vu3r2rrvj7: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1jr9s6cx4j637fctkvglrclvrr824vu3r2rrvj7\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1jyunclt6juv6g7rw0dltlr0kgaqtpq4quvyvu3: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1jyunclt6juv6g7rw0dltlr0kgaqtpq4quvyvu3\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1lqm5tutr5xcw9d5vc4457exa3ghd4sr9mzwdex: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1lqm5tutr5xcw9d5vc4457exa3ghd4sr9mzwdex\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1kvsxd94ue6f4rtchv2l6me5k07uh26s7637cza: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1kvsxd94ue6f4rtchv2l6me5k07uh26s7637cza\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1s8s39cnse493rzkmyr95esa44chc6vgztdm7gh: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1s8s39cnse493rzkmyr95esa44chc6vgztdm7gh\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1ykagvyzdmj3jcxkhavy7l84qs66haf7akqfrkc: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1ykagvyzdmj3jcxkhavy7l84qs66haf7akqfrkc\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1juwtwk5qymhz7s3hn0vx6tkqst54ud6wfjknvp: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1juwtwk5qymhz7s3hn0vx6tkqst54ud6wfjknvp\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra18xfqhtfaz2su55zmurmh02ng9lnhw0xnyplvln: WasmContractsContractAddressStore(\n    ContractAddress: \"terra18xfqhtfaz2su55zmurmh02ng9lnhw0xnyplvln\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1eq0xqc88ceuvw2ztz2a08200he8lrgvnplrcst: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1eq0xqc88ceuvw2ztz2a08200he8lrgvnplrcst\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n  terra1dy9kmlm4anr92e42mrkjwzyvfqwz66un00rwr5: WasmContractsContractAddressStore(\n    ContractAddress: \"terra1dy9kmlm4anr92e42mrkjwzyvfqwz66un00rwr5\"\n    QueryMsg: \"{\\\"balance\\\":{\\\"address\\\":\\\"terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma\\\"}}\"\n  ) {\n    Height\n    Result\n    __typename\n  }\n}\n"}' --compressed
        # https://bombay-fcd.terra.dev/wasm/contracts/terra10llyp6v3j3her8u3ce66ragytu45kcmd9asj3u/store?query_msg={%22balance%22:{%22address%22:%22terra1h0ujhwfx9wxt9lgpk5vrzutctt3k2cue9z3qma%22}}
        
        query = {
            "balance": {
                "address": account_address
            }
        }
        query_result = Terra.terra.wasm.contract_query(token_address, query)
        non_native_balance = Dec(query_result['balance'])

        return non_native_balance
    

    def get_wallet_balances(self):
        wallet_balances:dict
        wallet_balances = {
            'UST' :  Dec(self.get_native_balance('uusd')),
            'aUST' : Dec(self.get_non_native_balance(Terra.aUST_token)),
            'LUNA' : Dec(self.get_native_balance('uluna')),
            'MIR' :  Dec(self.get_non_native_balance(Terra.MIR_token)),
            'SPEC' : Dec(self.get_non_native_balance(Terra.SPEC_token)),
            'ANC' :  Dec(self.get_non_native_balance(Terra.ANC_token)),
        }

        return wallet_balances