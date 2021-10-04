# Terra SDK
from requests.sessions import default_headers
from terra_sdk.client.lcd import LCDClient
from terra_sdk.key.mnemonic import MnemonicKey
from terra_sdk.core.coins import Coins
from terra_sdk.core.coins import Coin
from terra_sdk.core.auth import StdFee
from terra_sdk.core.wasm import MsgExecuteContract

# Other assets
from assets.Contact_addresses import Contract_addresses
from assets.Queries import Queries
import B_Config as config

class Transaction:
    # https://terra-money.github.io/terra-sdk-python/guides/transactions.html
    def __init__(self):
        
        if config.NETWORK == 'MAINNET':
            self.chain_id = 'columbus-5'
            self.public_node_url = 'https://lcd.terra.dev'
            self.tx_look_up = f'https://finder.terra.money/{self.chain_id}/tx/'
            self.contact_addresses = Contract_addresses.contact_addresses(network='MAINNET')
            self.rev_Contract_addresses = Contract_addresses.rev_contact_addresses(self.contact_addresses)

        else:
            self.chain_id = 'bombay-12'
            self.public_node_url = 'https://bombay-lcd.terra.dev'
            self.tx_look_up = f'https://finder.terra.money/{self.chain_id}/tx/'
            self.contact_addresses = Contract_addresses.contact_addresses(network='bombay-12')
            self.rev_Contract_addresses = Contract_addresses.rev_contact_addresses(self.contact_addresses)

        # Contract required
        self.mmMarket = self.contact_addresses['mmMarket']
        self.aTerra = self.contact_addresses['aTerra']
        self.Mint = self.contact_addresses['Mint']
        self.Staking = self.contact_addresses['Staking']
        self.Lock = self.contact_addresses['Lock']

        self.mirrorFarm = self.contact_addresses['mirrorFarm']
        self.anchorFarm = self.contact_addresses['anchorFarm']
        self.specFarm = self.contact_addresses['specFarm']
        self.pylonFarm = self.contact_addresses['pylonFarm']
        self.specgov = self.contact_addresses['specgov']

        self.Terraswap_MIR_UST_Pair = self.contact_addresses['Terraswap MIR-UST Pair']
        self.Spectrum_SPEC_UST_Pair = self.contact_addresses['Spectrum SPEC-UST Pair']
        self.Terraswap_ANC_UST_Pair = self.contact_addresses['terraswapAncUstPair']

        self.SPEC_token = self.contact_addresses['SPEC']
        self.MIR_token = self.contact_addresses['MIR']
        self.ANC_token = self.contact_addresses['ANC']

        self.failed_tx_hash = self.contact_addresses['failed_tx_hash']
        self.success_tx_hash = self.contact_addresses['success_tx_hash']

        # self.fee_estimation =  # 0.456
        self.fee_estimation = Queries().get_fee_estimation() # 1409250

        self.terra = LCDClient(
            chain_id=self.chain_id,
            url=self.public_node_url,
            # gas_prices=Queries().get_terra_gas_prices(),
            gas_adjustment=1.6)

        self.mk = MnemonicKey(mnemonic=config.mnemonic)
        self.wallet = self.terra.wallet(self.mk)

    # For debugging only
    if config.Disable_all_transaction_defs:
        if config.Return_failed_tx:
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return self.failed_tx_hash
            def Anchor_borrow_more_UST(self, amount): return self.failed_tx_hash
            def Anchor_deposit_UST_for_Earn(self, amount): return self.failed_tx_hash
            def Anchor_repay_debt_UST(self, amount): return self.failed_tx_hash
            def Anchor_withdraw_UST_from_Earn(self, amount, denom): return self.failed_tx_hash
            def claim_ANC(self): return self.failed_tx_hash
            def claim_MIR(self): return self.failed_tx_hash
            def claim_SPEC(self): return self.failed_tx_hash
            def Mirror_claim_unlocked_UST(self, Mirror_position_info): return self.failed_tx_hash
            def Mirror_withdraw_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return self.failed_tx_hash
            def sell_ANC(self, amount): return self.failed_tx_hash
            def sell_MIR(self, amount): return self.failed_tx_hash
            def sell_SPEC(self, amount): return self.failed_tx_hash
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return self.failed_tx_hash
        else:
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return self.success_tx_hash
            def Anchor_borrow_more_UST(self, amount): return self.success_tx_hash
            def Anchor_deposit_UST_for_Earn(self, amount): return self.success_tx_hash
            def Anchor_repay_debt_UST(self, amount): return self.success_tx_hash
            def Anchor_withdraw_UST_from_Earn(self, amount, denom): return self.success_tx_hash
            def claim_ANC(self): return self.success_tx_hash
            def claim_MIR(self): return self.success_tx_hash
            def claim_SPEC(self): return self.success_tx_hash
            def Mirror_claim_unlocked_UST(self, Mirror_position_info): return self.success_tx_hash
            def Mirror_withdraw_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return self.success_tx_hash
            def sell_ANC(self, amount): return self.success_tx_hash
            def sell_MIR(self, amount): return self.success_tx_hash
            def sell_SPEC(self, amount): return self.success_tx_hash
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return self.success_tx_hash

    else:
        def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom):

            amount = int(collateral_amount_in_kind*1e6)

            # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
            if denom == 'aUST':

                contract=self.aTerra
                execute_msg={
                    "send": {
                        "amount": str(amount),
                        "contract": self.Mint,
                        "msg": {
                            "deposit": {
                                "position_idx": idx,
                                "collateral": {
                                    "amount": str(amount),
                                    "info": {
                                        "token": {
                                            "contract_addr": self.aTerra,
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                coins=Coins()

            else:
                # Luna and UST are natively supported
                coin = Coin(denom, int(collateral_amount_in_kind*1e6)).to_data()
                coins = Coins.from_data([coin])

                contract = self.Mint
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

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Mirror_withdraw_collateral_for_position(self, idx, collateral_amount_in_kind, denom):

            amount = int(collateral_amount_in_kind*1e6)

            # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
            if denom == 'aUST':
                # https://finder.terra.money/tequila-0004/tx/10C1B6310DA5B16F5EE96F3535B99C9CD7DC5D696054D547C32A54F2317E930B

                contract=self.aTerra
                execute_msg={
                    "withdraw": {
                        "position_idx": idx,
                        "collateral": {
                            "amount": str(amount),
                            "info": {
                                "token": {
                                    "contract_addr": self.aTerra
                                }
                            }
                        }
                    }
                }
                coins=Coins()

            else:
                coin = Coin('uusd', int(collateral_amount_in_kind*1e6)).to_data()
                coins = Coins.from_data([coin])

                contract=self.Mint
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

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Mirror_claim_unlocked_UST(self, Mirror_position_info):

            def position_idxs_to_be_claimed():
                position_idxs_to_be_claimed = []
                for position in Mirror_position_info:
                    position_idxs_to_be_claimed.append(position['position_idx'])
                return position_idxs_to_be_claimed

            contract=self.Lock
            execute_msg={
                "unlock_position_funds": {
                    "positions_idx": position_idxs_to_be_claimed()
                }
            }
            coins=Coins()

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def claim_MIR(self):

            contract=self.Staking
            execute_msg={
                "withdraw": {}
            }
            coins = Coins()

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def claim_SPEC(self):

            send = [MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.specgov,
                execute_msg={
                    "mint": {}
                }
            ), MsgExecuteContract( # Withdraw SPEC from your mirrorFarm
                sender=self.wallet.key.acc_address,
                contract=self.mirrorFarm,
                execute_msg={
                    "withdraw": {}
                }
            ), MsgExecuteContract( # Withdraw SPEC from your anchorFarm
                sender=self.wallet.key.acc_address,
                contract=self.anchorFarm,
                execute_msg={
                    "withdraw": {}
                }
            ), MsgExecuteContract( # Withdraw SPEC from your pylonfarm
                sender=self.wallet.key.acc_address,
                contract=self.pylonFarm,
                execute_msg={
                    "withdraw": {}
                }
            ), MsgExecuteContract( # Withdraw SPEC from your specFarm # Todo If there is nothing to claim the will fail, or if there is no farm
                sender=self.wallet.key.acc_address,
                contract=self.specFarm,
                execute_msg={
                    "withdraw": {}
                }
            )]

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(3000000, str(self.fee_estimation) + "uusd"))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def claim_ANC(self):

            contract=self.mmMarket
            execute_msg={
                "claim_rewards": {}
            }
            coins=Coins()

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def sell_MIR(self, amount):

            # https://docs.terraswap.io/docs/howto/swap/

            contract=self.MIR_token
            execute_msg={
                "send": {
                    "contract": self.Terraswap_MIR_UST_Pair,
                    "amount": str(int(amount*1e6)),
                    "msg": "eyJzd2FwIjp7fX0="
                }
            }
            coins=Coins()

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def sell_SPEC(self, amount):
            # https://docs.terraswap.io/docs/howto/swap/

            contract=self.SPEC_token
            execute_msg={
                "send": {
                    "contract": self.Spectrum_SPEC_UST_Pair,
                    "amount": str(int(amount*1e6)),
                    "msg": "eyJzd2FwIjp7fX0="
                }
            }

            coins=Coins()

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def sell_ANC(self, amount):
            # https://docs.terraswap.io/docs/howto/swap/

            contract=self.ANC_token
            execute_msg={
                "send": {
                    "contract": self.Terraswap_ANC_UST_Pair,
                    "amount": str(int(amount*1e6)),
                    "msg": "eyJzd2FwIjp7fX0="
                }
            }

            coins=Coins()

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Anchor_deposit_UST_for_Earn(self, amount):
            amount = int(amount * 1e6)

            # Depoit a bit less, to have some UST for tx fees
            coin = Coin('uusd', amount - self.fee_estimation * config.Safety_multiple_on_transaction_fees).to_data()
            coins = Coins.from_data([coin])

            contract=self.mmMarket
            execute_msg={
                "deposit_stable": {}
            },

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Anchor_withdraw_UST_from_Earn(self, amount, denom):

            # Convert amount UST into aUST for withdrawl and add a bit more for fees
            if denom == 'UST':
                amount = amount / Queries().get_aUST_rate()            

            amount = int(amount * 1e6)

            contract=self.aTerra
            execute_msg={
                    "send": {
                        "contract": self.mmMarket,
                        "amount": str(amount),
                        "msg": "eyJyZWRlZW1fc3RhYmxlIjp7fX0="}
            }
            coins = Coins()

            fee = str(self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Anchor_repay_debt_UST(self, amount):
            amount = int(amount * 1000000)

            # Deduct the fee incl safety so there is still some UST left
            coin = Coin('uusd', amount - self.fee_estimation * config.Safety_multiple_on_transaction_fees).to_data()
            coins = Coins.from_data([coin])

            contract=self.mmMarket
            execute_msg={
                "repay_stable": {}
            }

            fee = str(config.Fee_multiplier_for_expensive_transactions * self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Anchor_borrow_more_UST(self, amount):

            amount = int((amount * 1e6) + self.fee_estimation * config.Safety_multiple_on_transaction_fees)

            contract=self.mmMarket
            execute_msg={
                "borrow_stable": {
                    "borrow_amount": f'{amount}'
                }
            }
            
            coins = Coins()

            fee = str(config.Fee_multiplier_for_expensive_transactions * self.fee_estimation) + "uusd"
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash

        def execute_transaction(self, contract, execute_msg, coins, fee):

            message = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=contract,
                execute_msg=execute_msg,
                coins=coins,
            )

            transaction = self.wallet.create_and_sign_tx(
                msgs=[message], 
                fee=StdFee(1000000, fee),
                memo='One-Stop-Bot'
                )

            result = self.terra.tx.broadcast(transaction)
            return result.txhash