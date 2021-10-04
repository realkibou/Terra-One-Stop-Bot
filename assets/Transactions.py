# Terra SDK
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

        # https://docs.mirror.finance/contracts/mint
        self.Mint = self.contact_addresses['Mint']
        # https://docs.mirror.finance/contracts/staking
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

        self.terra = LCDClient(chain_id=self.chain_id, url=self.public_node_url)
        self.mk = MnemonicKey(mnemonic=config.mnemonic) # Desire wallet via passphrase
        self.wallet = self.terra.wallet(self.mk) # Define what wallet to use
        self.account_address = self.wallet.key.acc_address # Account Add
        self.fee = Queries().get_fee_estimation() # Fee

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

            # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
            if denom == 'aUST':
                # https://finder.terra.money/tequila-0004/tx/0B88BC73AB9E1699D710750E5F4A5F871D5D915733416975A1CA621DF4ACBB6D

                amount = int(collateral_amount_in_kind*1e6)

                send = MsgExecuteContract(
                    sender=self.wallet.key.acc_address,
                    contract=self.aTerra,
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
                ),

            else:
                # Luna and UST are natively supported
                # https://finder.terra.money/tequila-0004/tx/EC32F0598F7E589598A33E9F848140EDDE0DD8E140BF997F286EA6948A2D3536
                coin = Coin(denom, int(collateral_amount_in_kind*1e6)).to_data()
                coins = Coins.from_data([coin])

                amount = int(collateral_amount_in_kind*1e6)

                send = MsgExecuteContract(
                    sender=self.wallet.key.acc_address,
                    contract=self.Mint,
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

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def Mirror_withdraw_collateral_for_position(self, idx, collateral_amount_in_kind, denom):

            # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
            if denom == 'aUST':
                # https://finder.terra.money/tequila-0004/tx/10C1B6310DA5B16F5EE96F3535B99C9CD7DC5D696054D547C32A54F2317E930B

                amount = int(collateral_amount_in_kind*1e6)

                send = MsgExecuteContract(
                    sender=self.wallet.key.acc_address,
                    contract=self.aTerra,
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
                ),

            else:
                # https://finder.terra.money/tequila-0004/tx/164192158C99EEC5898F64029D34A0F407F7B0F946BA7408504B2A0230C605C8

                coin = Coin('uusd', int(collateral_amount_in_kind*1e6)).to_data()
                coins = Coins.from_data([coin])

                amount = int(collateral_amount_in_kind*1e6)

                send = MsgExecuteContract(
                    sender=self.wallet.key.acc_address,
                    contract=self.Mint,
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

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def Mirror_claim_unlocked_UST(self, Mirror_position_info):

            def position_idxs_to_be_claimed():
                position_idxs_to_be_claimed = []
                for position in Mirror_position_info:
                    position_idxs_to_be_claimed.append(position['position_idx'])
                return position_idxs_to_be_claimed

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.Lock,
                execute_msg={
                    "unlock_position_funds": {
                        "positions_idx": position_idxs_to_be_claimed()
                    }
                },
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def claim_MIR(self):

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.Staking,
                execute_msg={
                    "withdraw": {}
                },
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def claim_SPEC(self):

            send = [MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.specgov,
                execute_msg={
                    "mint": {}
                }
            ), MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.mirrorFarm,
                execute_msg={
                    "withdraw": {}
                }
            )]

            # Todo: Claim also SPEC from specFarm, anchroFarm, pylonFarm

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def claim_ANC(self):

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.mmMarket,
                execute_msg={
                    "claim_rewards": {}
                }
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def sell_MIR(self, amount):

            # https://docs.terraswap.io/docs/howto/swap/

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.MIR_token,
                execute_msg={
                    "send": {
                        "contract": self.Terraswap_MIR_UST_Pair,
                        "amount": str(int(amount*1e6)),
                        "msg": "eyJzd2FwIjp7fX0="
                    }
                }
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def sell_SPEC(self, amount):
            # https://docs.terraswap.io/docs/howto/swap/

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.SPEC_token,
                execute_msg={
                    "send": {
                        "contract": self.Spectrum_SPEC_UST_Pair,
                        "amount": str(int(amount*1e6)),
                        "msg": "eyJzd2FwIjp7fX0="
                    }
                }
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def sell_ANC(self, amount):
            # https://docs.terraswap.io/docs/howto/swap/

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.ANC_token,
                execute_msg={
                    "send": {
                        "contract": self.Terraswap_ANC_UST_Pair,
                        "amount": str(int(amount*1e6)),
                        "msg": "eyJzd2FwIjp7fX0="
                    }
                }
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def Anchor_deposit_UST_for_Earn(self, amount):
            amount = int(amount * 1e6)

            # Depoit a bit less, to have some UST for tx fees
            coin = Coin('uusd', amount - self.fee_estimation).to_data()
            coins = Coins.from_data([coin])

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.mmMarket,
                execute_msg={
                    "deposit_stable": {}
                },
                coins=coins
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def Anchor_withdraw_UST_from_Earn(self, amount, denom):
            # Convert amount UST into aUST for withdrawl and add a bit more for fees
            if denom == 'UST':
                amount = int(amount / self.aUST_rate)
            else:
                pass

            amount = (amount * 1e6) + self.fee_estimation

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.aTerra,
                execute_msg={
                    "send": {
                        "contract": self.mmMarket,
                        "amount": str(amount),
                        "msg": "eyJyZWRlZW1fc3RhYmxlIjp7fX0="}
                },
                coins=Coins()  # { "denom": "uusd", "amount": "6140784000" }
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def Anchor_repay_debt_UST(self, amount):
            amount = int(amount * 1000000)

            # Deduct the fee incl safety so there is still some UST left
            coin = Coin('uusd', amount - self.fee_estimation).to_data()
            coins = Coins.from_data([coin])

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.mmMarket,
                execute_msg={
                    "repay_stable": {}
                },
                coins=coins
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash


        def Anchor_borrow_more_UST(self, amount):

            amount = int((amount * 1e6) + self.fee_estimation)

            send = MsgExecuteContract(
                sender=self.wallet.key.acc_address,
                contract=self.mmMarket,
                execute_msg={
                    "borrow_stable": {
                        "borrow_amount": f'{amount}'
                    }
                },
                coins=Coins()
            ),

            sendtx = self.wallet.create_and_sign_tx(send, fee=StdFee(1000000, self.fee))
            result = self.terra.tx.broadcast(sendtx)

            return result.txhash