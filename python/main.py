from bitcoinrpc.authproxy import AuthServiceProxy
import time
import os

RPC_URL = "http://alice:password@127.0.0.1:18443"

def main():
    try:
        client = AuthServiceProxy(RPC_URL)

        # Create or load wallets
        for wallet_name in ["Miner", "Trader"]:
            try:
                client.createwallet(wallet_name)
                print("Wallet '{}' created.".format(wallet_name))
            except Exception as e:
                if "already exists" in str(e):
                    print("Wallet '{}' already exists.".format(wallet_name))
            finally:
                if wallet_name == "Miner":
                    miner_wallet = AuthServiceProxy("{}/wallet/Miner".format(RPC_URL))
                else:
                    trader_wallet = AuthServiceProxy("{}/wallet/Trader".format(RPC_URL))

        # 1. Generate address for mining reward
        mining_address = miner_wallet.getnewaddress("Mining Reward")
        print("Mining to address:", mining_address)

        # 2. Mine blocks until balance is positive (need 101 blocks for coinbase maturity)
        blocks_mined = 0
        while miner_wallet.getbalance() == 0:
            client.generatetoaddress(1, mining_address)
            blocks_mined += 1

        # Coinbase rewards require 100 confirmations before becoming spendable.
        print("Blocks mined to get spendable balance:", blocks_mined)
        print("Miner wallet balance:", miner_wallet.getbalance())

        # 3. Generate address for Trader
        trader_address = trader_wallet.getnewaddress("Received")

        # 4. Send 20 BTC from Miner to Trader
        txid = miner_wallet.sendtoaddress(trader_address, 20.0)
        print("Transaction sent. TXID:", txid)

        # 5. Wait and fetch unconfirmed transaction from mempool
        time.sleep(1)
        mempool_tx = client.getmempoolentry(txid)
        print("Mempool transaction entry:", mempool_tx)

        # 6. Mine 1 block to confirm transaction
        client.generatetoaddress(1, mining_address)

        # 7. Extract transaction details
        raw_tx = client.getrawtransaction(txid, True)
        vin_txid = raw_tx["vin"][0]["txid"]
        vin_vout = raw_tx["vin"][0]["vout"]

        prev_tx = client.getrawtransaction(vin_txid, True)
        input_value = prev_tx["vout"][vin_vout]["value"]
        input_address = prev_tx["vout"][vin_vout]["scriptPubKey"].get("address", "UNKNOWN")

        output_address_1 = raw_tx["vout"][0]["scriptPubKey"].get("address", "UNKNOWN")
        output_amount_1 = raw_tx["vout"][0]["value"]
        output_address_2 = raw_tx["vout"][1]["scriptPubKey"].get("address", "UNKNOWN")
        output_amount_2 = raw_tx["vout"][1]["value"]

        if output_address_1 == trader_address:
            trader_output = (output_address_1, output_amount_1)
            miner_change = (output_address_2, output_amount_2)
        else:
            trader_output = (output_address_2, output_amount_2)
            miner_change = (output_address_1, output_amount_1)

        fees = round(input_value - output_amount_1 - output_amount_2, 8)
        tx_block = client.getblock(raw_tx["blockhash"])
        block_height = tx_block["height"]
        block_hash = tx_block["hash"]

        # 8. Output details to out.txt
        os.makedirs("../", exist_ok=True)
        with open('out.txt', 'w') as f:
            f.write("{}\n".format(txid))
            f.write("{}\n".format(input_address))
            f.write("{}\n".format(input_value))
            f.write("{}\n".format(trader_output[0]))
            f.write("{}\n".format(trader_output[1]))
            f.write("{}\n".format(miner_change[0]))
            f.write("{}\n".format(miner_change[1]))
            f.write("{}\n".format(fees))
            f.write("{}\n".format(block_height))
            f.write("{}\n".format(block_hash))

        print("Details written to ../out.txt")

    except Exception as e:
        print("Error occurred:", e)

if __name__ == "__main__":
    main()
