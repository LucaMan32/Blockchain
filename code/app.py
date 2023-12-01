from flask import Flask, render_template, request, redirect, url_for
import hashlib
import json
import rsa
from time import time, localtime, strftime

app = Flask(__name__)

# Configurazione per i file statici
app.config['STATIC_FOLDER'] = 'static'

class Blockchain:
    difficulty = 2
    mining_reward = 10

    def __init__(self):
        self.chain = []
        self.transactions = []
        self.mempool = []
        self.create_block(previous_hash=self.hash_string('The Times 03/Jan/2009 Chancellor on brink of second bailout for banks'))
        self.balances = {'Luca': 100, 'Prof': 100, 'System': 0, 'Miner': 0}
        self.transaction_confirmations = {}
        self.transaction_fees = {}
        self.key_pairs = {}
        self.transaction_counter = 0

    def generate_key_pair(self, user):
        (pubkey, privkey) = rsa.newkeys(512)
        self.key_pairs[user] = (pubkey, privkey)

    def sign_transaction(self, user, transaction):
        privkey = self.key_pairs[user][1]
        signature = rsa.sign(json.dumps(transaction, sort_keys=True).encode(), privkey, 'SHA-1')
        return signature

    def verify_transaction(self, user, transaction, signature):
        pubkey = self.key_pairs[user][0]
        try:
            rsa.verify(json.dumps(transaction, sort_keys=True).encode(), signature, pubkey)
            return True
        except rsa.pkcs1.VerificationError:
            return False

    def create_block(self, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': strftime("%d/%m/%Y %H:%M", localtime(time())),
            'transactions': self.transactions,
            'previous_hash': previous_hash,
            'nonce': 0
        }
        proof = self.proof_of_work(block)
        block['nonce'] = proof

        if block['index'] % 2 == 0:
            self.mining_reward /= 2

        self.transactions = []
        self.chain.append(block)
        return block

    def add_transaction(self, sender, recipient, amount, fee=0):
        if sender not in self.key_pairs:
            self.generate_key_pair(sender)
        if recipient not in self.key_pairs:
            self.generate_key_pair(recipient)

        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'fee': fee
        }

        # Firma digitale
        signature = self.sign_transaction(sender, transaction)
        transaction['signature'] = signature.hex()  # Converti la firma in esadecimale

        self.mempool.append(transaction)

        transaction_hash = self.hash_string(json.dumps(transaction, sort_keys=True))
        print(f"Transaction Hash: {transaction_hash}")
        print(f"Signature: {signature.hex()}")  # Stampa il valore della firma

        self.update_balances(sender, recipient, amount)
        self.transaction_counter += 1

        if self.transaction_counter % 3 == 0:
            self.mine_block()  # Estrai un nuovo blocco dopo ogni 3 transazioni

    def process_mempool(self):
        self.transactions.extend(self.mempool)
        self.mempool = []

    def mine_block(self):
        previous_block = self.chain[-1]
        previous_hash = self.hash_block(previous_block)
        self.process_mempool()
        self.add_transaction('System', 'Miner', self.mining_reward)
        block = self.create_block(previous_hash)
        print(f"Block #{block['index']} mined.")
        print(f"Block Hash: {self.hash_block(block)}")
        print(f"Timestamp: {block['timestamp']}")
        print(f"Nonce: {block['nonce']}")
        print(f"Mining Reward: {self.mining_reward}")
        return block

    def proof_of_work(self, block):
        block_string = json.dumps(block, sort_keys=True).encode()
        proof = 0
        while not self.valid_proof(block_string, proof):
            proof += 1
        return proof

    def valid_proof(self, block_string, proof):
        guess = f'{block_string}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:Blockchain.difficulty] == '0' * Blockchain.difficulty

    def hash_block(self, block):
        block_string = json.dumps(block, sort_keys=True).encode()
        while True:
            block['nonce'] += 1
            block_string = json.dumps(block, sort_keys=True).encode()
            hash_attempt = hashlib.sha256(block_string).hexdigest()
            if hash_attempt[:Blockchain.difficulty] == '0' * Blockchain.difficulty:
                return hash_attempt

    def hash_string(self, string):
        return hashlib.sha256(string.encode()).hexdigest()

    def get_balance(self, user):
        return self.balances.get(user, 0)

    def update_balances(self, sender, recipient, amount):
        self.balances.setdefault(sender, 0)
        self.balances.setdefault(recipient, 0)
        self.balances[sender] -= amount
        self.balances[recipient] += amount

    def analyze_block(self, block_number):
        if 0 < block_number <= len(self.chain):
            block = self.chain[block_number - 1]
            print(f"\nBlock #{block['index']} Hash: {self.hash_block(block)}")
            print(f"Timestamp: {block['timestamp']}")
            print(f"Nonce: {block['nonce']}")
            print("Transactions:")
            for transaction in block['transactions']:
                print(json.dumps(transaction, sort_keys=True, indent=2))
        else:
            print("Blocco non valido.")

    def display_transaction_confirmations(self, transaction_hash):
        confirmations = self.transaction_confirmations.get(transaction_hash, 0)
        print(f"Transaction {transaction_hash} Confirmations: {confirmations}")

    def set_transaction_confirmation(self, transaction_hash, confirmations):
        self.transaction_confirmations[transaction_hash] = confirmations

    def get_transaction_fee(self, transaction_hash):
        return self.transaction_fees.get(transaction_hash, 0)

    def set_transaction_fee(self, transaction_hash, fee):
        self.transaction_fees[transaction_hash] = fee

    def print_balances(self):
        print(f"\nSaldi finali:")
        for user, balance in self.balances.items():
            print(f"{user} Balance: {balance}")

# Istanza della Blockchain
blockchain = Blockchain()

@app.route('/')
def home():
    return render_template('index.html', balances=blockchain.balances, chain=blockchain.chain)

@app.route('/transaction', methods=['POST'])
def add_transaction():
    sender = request.form['sender']
    recipient = request.form['recipient']
    amount = int(request.form['amount'])

    if sender not in blockchain.balances or not recipient in blockchain.balances:
        return "Mittente o destinatario non valido. Riprova."

    blockchain.add_transaction(sender, recipient, amount)

    return redirect(url_for('home'))

@app.route('/block', methods=['GET'])
def explore_block():
    block_number = int(request.args.get('block_number'))

    if 0 < block_number <= len(blockchain.chain):
        block = blockchain.chain[block_number - 1]
        print(f"\nBlock #{block['index']} Hash: {blockchain.hash_block(block)}")
        print(f"Timestamp: {block['timestamp']}")
        print(f"Nonce: {block['nonce']}")
        print("Transactions:")
        for transaction in block['transactions']:
            print(json.dumps(transaction, sort_keys=True, indent=2))
    else:
        return "Blocco non valido."

    return render_template('index.html', balances=blockchain.balances, chain=blockchain.chain)

if __name__ == '__main__':
    app.run(debug=True)
