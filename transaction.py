import json
import base64
import plyvel

# vin class
########################################################################################################################
class Vin:
    def __init__(self, tx_id, index, unlock):
        self.tx_id = tx_id                      # string
        self.index = index                      # int
        self.unlock = unlock                    # bytes => Privatekey.ecdsa_deserialize(unlock)로 디코딩
    '''
    def vin_to_dict(self):
        return {
                "tx_id" : self.tx_id, 
                "index" : self.index,       
                "unlock" : self.unlock
                }
    '''

    def to_dict(self):
        return {'tx_id': self.tx_id, 'index': self.index, 'unlock': base64.b64encode(self.unlock).decode('utf-8')}

    def from_dict(self, data_json):
        return Vin(data_json["tx_id"], data_json["index"], base64.b64decode(data_json["unlock"]))


# Vout class
########################################################################################################################
class Vout:
    def __init__(self, value, lock):
        self.value = value                      # float
        self.lock = lock                        # bytes => PublicKey(pub, raw=True)로 디코딩
    '''
    def vout_to_dict(self):
        return {
                "value" : self.value,
                "lock"  : self.lock
                }
    '''
    def to_dict(self):
        return {'value': self.value, 'lock': base64.b64encode(self.lock).decode('utf-8')}

    def from_dict(self, data_json):
        return Vout(data_json["value"], base64.b64decode(data_json["lock"]))

# Transaction class
########################################################################################################################
class Transaction(object):

    # class variables
    _MemoryPool = 0

    # init
    ####################################################################################################################
    def __init__(self, tx_id, in_num, vin, out_num, vout):
        # Key = tx_id
        self.tx_id = tx_id          # bytes
        self.in_num = in_num        # int
        self.vin = vin              # list[Vin]
        self.out_num = out_num      # int
        self.vout = vout            # list[Vout]
    
    '''
    # for tx to dictionary type.
    def Tx_to_dict(self):
        return {
                    "tx_id"   : self.tx_id,
                    "in_num"  : self.in_num,
                    "vin"     : [item.vin_to_dict() for item in self.vin],
                    "out_num" : self.out_num,
                    "vout"    : [item.vout_to_dict() for item in self.vout]
                }
    '''


    # Make db for store pending transaction
    ####################################################################################################################
    @classmethod
    def initialize(cls):
        cls._MemoryPool = plyvel.DB('./db/MemoryPool', create_if_missing=True)


    # Insert transaction to DB
    ####################################################################################################################
    @classmethod
    def Insert_MemoryPool(cls, tx_id, in_counter, vin, out_counter, vout):
        """
        Args:
            tx_id       : bytes(key of db)
            in_counter  : int
            vin         : list[Vin]
            out_counter : int
            vout        : list[Vout]
        """

        newVin = []
        newVout = []

        # Convert vin and vout for store
        ################################################################################################################
        for vin_el in vin:
            newVin.append(json.dumps(vin_el.__dict__))

        for vout_el in vout:
            newVout.append(json.dumps(vout_el.__dict__))

        mempool = {"in_num": in_counter,
                   "vin": json.dumps(newVin),
                   "out_num": out_counter,
                   "vout": json.dumps(newVout)}

        mempool_en = json.dumps(mempool)

        cls._MemooryPool.put(tx_id, mempool_en.encode())

    # Pop transaction from DB
    ####################################################################################################################
    @classmethod
    def Pop_MemoryPool(cls, tx_id):
        """
        Args:
            tx_id       : bytes(key of db)
        """

        cls._MemoryPool.delete(tx_id, sync=True)

    def to_dict(self):
        return {'tx_id': base64.b64encode(self.tx_id).decode('utf-8'), 'in_num': self.in_num,
                'vin': [item.to_dict() for item in self.vin], 'out_num': self.out_num, 'vout': [item.to_dict() for item in self.vout]}

    def from_dict(self, data_json):
        return Transaction(base64.b64decode(data_json["tx_id"]), data_json["in_num"],
                           [Vin(0, 0, 0).from_dict(item) for item in data_json["vin"]], data_json["out_num"],
                           [Vout(0, 0).from_dict(item) for item in data_json["vout"]])
  
    
    #Communication part.


    def _broadcast_Tx(self):
        message = {'type': 'TRANSACTION', 'tx': self.to_dict()}
        #print(message)
        return self._broadcast(message)

    def _broadcast(self, message):
        results = []
        pool = multiprocessing.Pool(5)
        # Peer._peers / self._peers
      
        # have to 
        pp = (('127.0.0.1',5003),('127.0.0.1',5002))

        for (host, port) in pp:
            results.append(pool.apply_async(
                self._send_message, args=(host, port, message)))
        pool.close()
        pool.join()
        return [result.get() for result in results]

    def _send_message(self, host, port, message):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(host, port)
            s.connect((host, port))
            s.sendall(json.dumps(message).encode('utf-8'))
            response = s.recv(655350, 0)
            return response.decode('utf-8')
    
