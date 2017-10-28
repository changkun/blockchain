import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4

from flask import Flask, jsonify, request
from urllib.parse import urlparse


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # 实例化该类之后，需要创建一个 genesis block
        self.new_block(previous_hash=1, proof=100)

        self.nodes = set()

    def register_node(self, address):
        """
        增加一个节点到节点链表里
        :param address: <str>节点地址.
        :return None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        确定一个给定的blockchain是否有效
        :param chain: <list> blockchain
        :return: <bool> 有效返回 True 无效返回 False
        """
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n----------\n')
            if block['previous_hash'] != self.hash(last_block):
                return False
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block
        return True

    def resolve_conflicts(self):
        """
        共识Consensus算法
        通过将我们的链替换为网络中最长的链表来解决冲突
        :return: <bool> 如果链表被替换了 那么返回 True 否则返回 False
        """
        neighbours = self.nodes
        new_chain = None
        # 只寻找比我们长的chain就可以了
        max_length = len(self.chain)
        # 综合并验证来自我们网络中所有节点的chain
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                # 检查最长的chain为有效chain
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        # 如果有效chain比我们的 chain 长，那么替换掉
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash=None):
        """
        创建一个新的 Block 到 Blockchain 中
        # 一个 block 包含
        #   - index,
        #   - timestamp,
        #   - transaction list,
        #   - proof,
        #   - previous hash
        # 每个新的区块都包含上一个区块的 hash，使得区块链的不变性成为可能，
        # 如果攻击者篡改了前序区块，所有后续区块的哈希都是错的
        :param proof: <int> 工作量证明算法给出的 Proof
        :param previous_hash: (可选) <str> 前一个 Block 的 Hash 值
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # 重置当前的交易列表
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        创建一个交易到下一个要挖的区块中
        :param sender: <str> 发送方的地址
        :param recipient: <str> 接受方的地址
        :param amount: <int> 金额
        :return: <int> 返回保存此交易的 block 的索引
        """
        # 添加一个新的交易到交易列表中
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        创建一个 SHA-256 的 block 哈希值
        :param block: <dict> block
        :return: <str>
        """
        # 计算一个 block 的哈希值
        # 必须要确认字典是有序的，否则就会出现 hash 的不一致
        # 因此这里在计算 block 数据的 hash 值之前，将其转化为一个json串
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # 返回 chain 中的最后一个 block
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        工作量证明算法的简化版
        - 找到一个数字 p' 使得 hash(pp') 初始的四个字符为0
          其中 p 是 p' 的前置proof
        - p 是前一个 proof, p' 是新的 proof
        :param last_proof: <int>
        :return: <int>
        """
        proof = 0
        previous_hash = self.hash(self.chain[-1])
        while self.valid_proof(last_proof, proof, previous_hash) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof, previous_hash):
        """
        验证 Proof: hash(last_proof, proof) 是否的开头是否包含4个0?
        :param last_proof: <int> 前一个 proof
        :param proof: <int> 当前proof
        :param previous_hash: <str> 前一个 block 的 hash
        :return: <bool> 正确返回 True 错误返回 False
        """
        guess = f'{last_proof}{proof}{previous_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


app = Flask(__name__)
# 给当前节点创建一个全局唯一的地址
node_identifier = str(uuid4()).replace('-', '')
# Blockchain 实例
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    """
    # 1. 计算工作量
    # 2. 奖励旷工，新增一次交易就赚一个币
    # 3. 将区块加入区块链
    # 运行工作量证明算法来获取下一次证明
    """
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # 创建一笔交易来奖励找到 proof 的人
    # 发送方设置为0来表示这个 node 是一个新的货币
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1
    )
    block = blockchain.new_block(proof)
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # 检查需要的数据是否在 POST 数据之中
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # 创建一笔交易
    index = blockchain.new_transaction(
        values['sender'], values['recipient'], values['amount']
    )
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return 'Error: Please supply a valid list of nodes', 400
    for node in nodes:
        blockchain.register_node(node)
    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200


def main():
    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
