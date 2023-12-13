#*******************************************************************************************************************************
# Inizio definizione delle librerie python da importare
#*******************************************************************************************************************************
from flask import Flask, render_template, request, redirect, url_for    # usata per l'interfaccia grafica
import hashlib                                                          # usata per generare gli hash delle transazioni
import json
import rsa                                                              # usata per generare le firme digitali
from time import time, localtime, strftime                              # usata per generare il timestamp
#********************************************************************************************************************************
# Fine definizione delle librerie python da importare
#********************************************************************************************************************************

# Creazione di un'app Flask, ovvero framework per sviluppare WebApp
app = Flask(__name__)

# Configurazione per i file statici, nel mio caso il logo di BTC
app.config['STATIC_FOLDER'] = 'static'

#*******************************************************************************************************************************
# Inizio definizione della classe Blockchain
#*******************************************************************************************************************************
class Blockchain:
    difficulty = 2          #definizione della difficoltà, ovvero l'hash del blocco deve iniziare con n 0
    mining_reward = 10      #inizializzazione della ricompensa ai minatori per ogni blocco minato, successivamente si dimezzerà

    def __init__(self):     #inizializzazione di diversi attributi tra cui bilancio degli utenti e genesis block
        self.chain = []
        self.transactions = []
        self.mempool = []
        self.create_block(previous_hash=self.hash_string('The Times 03/Jan/2009 Chancellor on brink of second bailout for banks'))
        self.balances = {'Luca': 100, 'Prof': 100, 'System': 0, 'Miner': 0}
        self.transaction_confirmations = {}
        self.transaction_fees = {}
        self.key_pairs = {}
        self.transaction_counter = 0

    def generate_key_pair(self, user):   #funzione per la generazione di una coppia di chiavi per la firma digitale, una per utente
        (pubkey, privkey) = rsa.newkeys(512) #utilizza algoritmo RSA --> crittografia asimmetrica, chiavi da 256 bit l'una
        self.key_pairs[user] = (pubkey, privkey) #chiave privata deve essere segreta mentre pubblica può essere distribuita liberamente
        # successivamente le chiavi sono tenute in key_pairs che è un dizionario di chiavi

    def sign_transaction(self, user, transaction):  #firma della transazione usando privat key, RSa + funzione hash SHA-1
        privkey = self.key_pairs[user][1] #ottengo private key di utente, trasformo la transazione in formato json
        signature = rsa.sign(json.dumps(transaction, sort_keys=True).encode(), privkey, 'SHA-1') #calcolo dell'hash della tran. con SHA-1 per creare un digest univoco e identificativo della transazione
        return signature #mentre con la private key firma l'hash della transazione tramite RSA

    def verify_transaction(self, user, transaction, signature): #verifica dellà validità della transazione
        pubkey = self.key_pairs[user][0] #ottiene public key dell'utente
        try: #decodifica della firma tramite RSA e confronta risultato con l'hash della transazione originale
            rsa.verify(json.dumps(transaction, sort_keys=True).encode(), signature, pubkey)
            return True #ritorna True se sono uguali e quindi la firma corrisponde alla public key
        except rsa.pkcs1.VerificationError:
            return False #ritorna False se transazione non è valida o la firma è stata alterata

    def create_block(self, previous_hash):  #creazione della struttura di un blocco, composto da index, ts, transazioni, hash precedente e nonce
        block = {
            'index': len(self.chain) + 1, # Assegna l'indice del nuovo blocco (numero del blocco successivo al precedente)
            'timestamp': strftime("%d/%m/%Y %H:%M", localtime(time())), # Assegna la data e l'ora corrente nel formato specificato
            'transactions': self.transactions, # Assegna le transazioni presenti nella blockchain al nuovo blocco
            'previous_hash': previous_hash, # Assegna l'hash del blocco precedente al nuovo blocco
            'nonce': 0 # Inizializza il nonce a 0 (sarà successivamente calcolato con la Proof of Work)
        }

        proof = self.proof_of_work(block) # Calcolo della Proof of Work per trovare un nonce valido
        block['nonce'] = proof            # Assegna il valore calcolato di nonce al blocco

        if block['index'] % 2 == 0:       #dimezzamento della ricompensa ai minatori ogni due blocchi --> simulazione dell'halving
            self.mining_reward /= 2

        self.transactions = []      # Azzera la lista delle transazioni poiché sono state incluse nel blocco
        self.chain.append(block)    # Aggiunge il blocco alla catena della blockchain
        return block                # Restituisce il blocco appena creato

    def add_transaction(self, sender, recipient, amount, fee=0):  #funzione per la creazione di transazioni
        if sender not in self.key_pairs:
            self.generate_key_pair(sender)
        if recipient not in self.key_pairs:
            self.generate_key_pair(recipient)

        transaction = {     # transazione composta da mittente, destinatario, ammontare
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'fee': fee #inizialmente messo per simulare tassa per ogni ricompensa come negli exchamge
        }

        # Firma digitale
        signature = self.sign_transaction(sender, transaction)
        transaction['signature'] = signature.hex()  # conversione della firma in esadecimale

        transaction_hash = self.hash_string(json.dumps(transaction, sort_keys=True)) #calcolo dell'hash della transazione
        transaction['transaction_hash'] = transaction_hash

        self.mempool.append(transaction) #aggiunta della transazione alla mempool

        print(f"Transaction Hash: {transaction_hash}")  # stampa il valore dell'hash della transazione nel terminale
        print(f"Signature: {signature.hex()}")  # stampa il valore della firma nel terminale

        self.update_balances(sender, recipient, amount) #chiamata alla funzione per l'aggiornamento del saldo degli utenti
        self.transaction_counter += 1   #incremento del contatore che conteggia il numero di transazioni in MemPool

        if self.transaction_counter % 3 == 0:   #verifica che il numero di transazioni siano 3 per poter minare il blocco
            self.mine_block()  # se sono effettivamente 3 mina un nuovo blocco 

    def process_mempool(self):  #mempool nel quale le transazioni aspettano di essere minate
        self.transactions.extend(self.mempool)
        self.mempool = []

    def mine_block(self):   #funzione per minare un nuovo blocco
        previous_block = self.chain[-1]     
        previous_hash = self.hash_block(previous_block) #assegna a previous_hash l'hash del blocco precedente
        self.process_mempool()

        # Aggiorna direttamente i saldi del miner e del sistema e assegna ricompensa a miner
        miner_reward = self.mining_reward
        self.balances['Miner'] += miner_reward
        self.balances['System'] -= miner_reward
        #self.add_transaction('System', 'Miner', self.mining_reward)
        block = self.create_block(previous_hash)        #creazione del blocco
        print(f"Block #{block['index']} mined.")        #stampa nel terminale delle informazioni relative al nuovo blocco minato
        print(f"Block Hash: {self.hash_block(block)}")
        print(f"Timestamp: {block['timestamp']}")
        print(f"Nonce: {block['nonce']}")
        print(f"Mining Reward: {self.mining_reward}")
        return block # restituisce nuovo blocco minato

    def proof_of_work(self, block): #funzione che implementa una proof of work per trovare un nonce valido
        block_string = json.dumps(block, sort_keys=True).encode() # conversione del blocco in formato json per poi codificarlo in byte
        proof = 0 # inizializza il nonce a 0
        while not self.valid_proof(block_string, proof):
            proof += 1 # continua a incrementare il nonce finché non trova una proof valida
        return proof

    def valid_proof(self, block_string, proof): # Verifica della validità di una proof
        guess = f'{block_string}{proof}'.encode() # Concatena il blocco codificato e la proof e lo converte in byte
        guess_hash = hashlib.sha256(guess).hexdigest() # Calcola l'hash SHA-256 della concatenazione
        return guess_hash[:Blockchain.difficulty] == '0' * Blockchain.difficulty # verifica se hash inizia con n zeri

    def hash_block(self, block): # calcolo dell'hash di un blocco
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

    def update_balances(self, sender, recipient, amount):   #funzione che aggiorna il saldo dei due utenti
        self.balances.setdefault(sender, 0)
        self.balances.setdefault(recipient, 0)
        self.balances[sender] -= amount
        self.balances[recipient] += amount

    def analyze_block(self, block_number): #funzione per blockchain explorer
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

    # Visualizzazione delle conferme di una transazione
    def display_transaction_confirmations(self, transaction_hash):
        confirmations = self.transaction_confirmations.get(transaction_hash, 0)
        print(f"Transaction {transaction_hash} Confirmations: {confirmations}")

    # Impostazione delle conferme di una transazione
    def set_transaction_confirmation(self, transaction_hash, confirmations):
        self.transaction_confirmations[transaction_hash] = confirmations

    # Ottenimento della fee di una transazione, non più utilizzato
    def get_transaction_fee(self, transaction_hash):
        return self.transaction_fees.get(transaction_hash, 0)

    # Impostazione della fee di una transazione
    def set_transaction_fee(self, transaction_hash, fee):
        self.transaction_fees[transaction_hash] = fee

    def print_balances(self):  # funzione per stampare a terminale il saldo degli utenti
        print(f"\nSaldi finali:")
        for user, balance in self.balances.items():
            print(f"{user} Balance: {balance}")

# Istanza della Blockchain
blockchain = Blockchain()

@app.route('/') # homepage
def home():
    return render_template('index.html', balances=blockchain.balances, chain=blockchain.chain, mempool=blockchain.mempool)

@app.route('/transaction', methods=['POST'])  #funzione per l'acquisizione tramite metodo POST dei valori inseriti nel form per la creazione di una nuova transazione
def add_transaction():
    sender = request.form['sender']
    recipient = request.form['recipient']
    amount = int(request.form['amount'])

    if sender not in blockchain.balances or not recipient in blockchain.balances or amount < 0: #controlli per verificare che l'importo sia positivo e che gli utenti esistano
        return "Utente o importo non valido. Riprova."
    elif blockchain.get_balance(sender) < amount:
        return "Saldo insufficiente. Riprova con un importo più basso."
    else:
        blockchain.add_transaction(sender, recipient, amount)   #se i dati inseriti sono validi aggiunge la transazione

    return redirect(url_for('home'))

@app.route('/block', methods=['GET']) # route per esplorare blocco specifico
def explore_block():
    block_number = int(request.args.get('block_number'))

    if 0 < block_number <= len(blockchain.chain):
        explored_block = blockchain.chain[block_number - 1]
        print(f"\nBlock #{explored_block['index']} Hash: {blockchain.hash_block(explored_block)}")
        print(f"Timestamp: {explored_block['timestamp']}")
        print(f"Nonce: {explored_block['nonce']}")
        print("Transactions:")
        for transaction in explored_block['transactions']:
            print(json.dumps(transaction, sort_keys=True, indent=2))
    else:
        return "Blocco non valido."

    return render_template('index.html', balances=blockchain.balances, chain=blockchain.chain, explored_block=explored_block)

# Avvio dell'app Flask
if __name__ == '__main__':
    app.run(debug=True)
