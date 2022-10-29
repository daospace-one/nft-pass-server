# DAO SPACE 的 NFT PASS 项目文件
# 本文件混合了后端验证和链上验证的代码

from dataclasses import dataclass
from eth_account import Account
from flask import Flask, request
import json
import datetime
from typing import Any, List
from web3 import Web3
from eth_account.messages import encode_defunct
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app, resources=r'/*')
rpc_endpoint = "https://rpc.api.moonbeam.network"
w3 = Web3(Web3.HTTPProvider(rpc_endpoint))


@app.route("/")
def main():
    return "Welcome to DAO SPACE"


@app.route("/v1/signature_check", methods=['OPTIONS','POST'])
def signature_check():
    '''签名验证请求
    请求类型: POST
    请求路径: https://61618mh025.zicp.fun/v1/signature_check
    Header: 无限制
    Body:
        signature: string 签名
        address: string 钱包地址
        text: string 签名加密前的内容
        pass_id: number 用户选用的 NFT PASS 的 Token ID
    '''
    text = request.form.get('text', '')
    signature = request.form.get('signature', '')
    address = request.form.get('address', '')
    pass_id = request.form.get('pass_id', '')
    # nonce = request.form.get('nonce','')
    result = PassManager.signature_check(text, signature, address)
    if result == True:
        result2 = PassManager.available_check_on_chain(pass_id, address)
        if result2 == True:
            # 生成一个临时二维码
            qr_1 = str(pass_id)
            qr_2 = datetime.datetime.now().strftime("%c")
            with open('qrList.json') as f:
                qr_list = json.load(f)
            flag = False
            for qr in qr_list:
                if qr['id'] == qr_1:
                    qr['time'] = qr_2
                    flag = True
            if flag == False:
                qr_list.append({'id': qr_1, "time": qr_2})
            with open('qrList.json', 'w') as f:
                json.dump(qr_list, f)
            qr_str = qr_1+';'+qr_2
            return (qr_str)
        else:
            return '0'
    else:
        return '0'


@app.route("/v1/scan_qr_code", methods=['POST'])
def scan_qr_code():
    '''二维码扫码请求
    请求类型: POST
    请求路径: https://61618mh025.zicp.fun/v1/scan_qr_code
    Header: 略
    Body:略
    '''
    body = str(request.data)
    index_st = 17
    index_ed = body.find('&&devicenumber=')
    qr = body[index_st:index_ed]
    qr_parts = qr.split(';')
    with open('qrList.json') as f:
        qr_list = json.load(f)
    try:
        for qr in qr_list:
            if qr['id'] == qr_parts[0]:
                if qr['time'] != qr_parts[1]:
                    return "code=0003"
                passed_time = datetime.datetime.now(
                ) - datetime.datetime.strptime(qr_parts[1], "%c")
                if passed_time.seconds > 300:
                    return "code=0004"
                return "code=0000"
        return "code=0002"
    except:
        return "code=0001"


class Pass():
    '''通行证类'''
    STATE_ENABLE = 1
    STATE_DISABLE = 2
    PASS_TYPE_DATE = 1
    PASS_TYPE_COUNT = 2

    def __init__(self, id, state, pass_type, opening_date, valid_time=None, rest_count=None):
        self.id: int = id                 # 卡号
        self.opening_date = opening_date  # 开卡时间
        self.state = state                # 状态：1-启用 2-停用
        self.pass_type = pass_type        # 类型：1-时间限制型 2-次数限制型
        self.valid_time = valid_time      # 有效时长（天）
        self.rest_count = rest_count      # 剩余次数（天，1 天最多扣 1 次）


class PassManager():
    '''通行证管理类'''
    def get_passes():
        '''获取所有通行证

        Return:
        The list of passes
        '''
        with open('passesData.json') as f:
            passes_data = json.load(f)
        return passes_data['pass_data']

    def get_pass(id, tips=None):
        '''获取指定通行证

        Params:
        id: 卡号

        Return:
        Pass: 对应的通行证数据
        '''
        passes = PassManager.get_passes()
        for the_pass in passes:
            if the_pass['id'] == id:
                if tips != None:
                    print(tips)
                return Pass(**the_pass)
        return None

    def add_pass(id, pass_type, num, opening_date=datetime.datetime.now().strftime("%c")):
        '''添加卡号

        Params: 
        id: 卡号
        opening_date: 开卡时间，默认为当前时间
        '''
        passes = PassManager.get_passes()
        flag = False
        for the_pass in passes:
            if the_pass['id'] == id:
                print('Pass ID', id, 'has been used, please choose another ID.')
                flag = True
                break
        if flag == False:
            new_pass = Pass(id, Pass.STATE_ENABLE,
                            pass_type, num, opening_date)
            print(new_pass.opening_date)
            passes.append(new_pass.__dict__)
            passes_data = {"pass_data": passes}
            with open('passesData.json', 'w') as f:
                json.dump(passes_data, f)

    def cancel_pass(id):
        '''注销卡号

        Params: 
        id: 卡号
        '''
        passes = PassManager.get_passes()
        flag = False
        for the_pass in passes:
            if the_pass['id'] == id:
                the_pass['state'] = Pass.STATE_DISABLE
                print('Pass', id, 'has been cancelled.')
                passes_data = {"pass_data": passes}
                with open('passesData.json', 'w') as f:
                    json.dump(passes_data, f)
                flag = True
                break
        if flag == False:
            print('Pass', id, 'does not exist.')

    def delete_pass(id):
        '''删除卡号

        Params: 
        id: 卡号
        '''
        passes = PassManager.get_passes()
        flag = False
        for the_pass in passes:
            if the_pass['id'] == id:
                passes.remove(the_pass)
                print('Pass', id, 'has been deleted.')
                passes_data = {"pass_data": passes}
                with open('passesData.json', 'w') as f:
                    json.dump(passes_data, f)
                flag = True
                break
        if flag == False:
            print('Pass', id, 'does not exist.')

    def available_check_on_server(id):
        '''检查是否可用

        Params: 
        id: 卡号
        Return:
        是否可用: bool
        '''
        the_pass = PassManager.get_pass(id)
        if the_pass == None:
            print('Pass ID', id, 'does not exist when checking for availability.')
        elif the_pass.state == Pass.STATE_DISABLE:
            print('Pass ID', id, 'is disabled to use.')
        elif the_pass.pass_type == Pass.PASS_TYPE_DATE:
            passed_days = datetime.datetime.now(
            ) - datetime.datetime.strptime(the_pass.opening_date, "%c")
            if passed_days.days > the_pass.valid_time:
                print('Pass ID', id, 'is out of date.')
            else:
                pass
        elif the_pass.pass_type == Pass.PASS_TYPE_COUNT:
            if the_pass.rest_count <= 0:
                print('Pass ID', id, 'has no times to use.')
            else:
                pass

    def available_check_on_chain(id, address):
        '''检查是否可用

        Params: 
        id: 卡号
        address: 钱包地址
        Return:
        是否可用: bool
        '''
        contract_address = "0x1c9CF0E5473914A0e705e8Cf0BdD3EfbbFe17E48"
        abi_path = "./contracts/nft_pass.json"
        file = open(abi_path, "r")
        data = file.read()
        file.close()
        abi = json.loads(data)
        collection = w3.eth.contract(
            address=contract_address,
            abi=abi
        )
        id = int(id)
        try:
            true_address = collection.functions.ownerOf(id).call()
            print(true_address)
        except:
            print('NFT PASS', id, 'is not exist.')
            return False
        if address != true_address:
            print('Address', address, 'who want to use NFT PASS', id, 'is fake!')
            return False
        state = collection.functions.activated(id).call()
        if state == 0:
            print('NFT PASS', id, 'has not been actived')
            return False
        vaild_time = collection.functions.expires(id).call()
        # now = datetime.datetime.now().timetz
        print(vaild_time)
        # 跳过了时间戳验证
        return True

    def signature_check(text, signature, address):
        '''验证签名

        Params: 
        text: 消息文本
        signature: 签名
        address: 传入的地址
        Return:
        签名是否正确: bool
        '''
        try:
            message = encode_defunct(text=text)
            address_now = Account.recover_message(message, signature=signature)
            if address_now == address:
                print("Signature is correct!")
                return True
            else:
                print("Signature error.")
                return False
        except:
            print("Wrong format for signature verification.")
            return False

    def nft_check_ankr(id, address, contractAddress='0x1c9CF0E5473914A0e705e8Cf0BdD3EfbbFe17E48'):
        '''验证 NFT
        包括持有者和元数据'''
        # url = 'https://rpc.ankr.com/moonbeam/'
        url = 'https://rpc.ankr.com/moonbeam/a1a69bca0f653800e0c598b54630efc93cebb607760a6bed2d67ac142c12435b'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "jsonrpc": "2.0",
            "method": "eth_getStorageAt",
            "params": [
                contractAddress,
                address,
                "latest"
            ]
        }
        # data = {
        #     "jsonrpc": "2.0",
        #     "method": "ankr_getNFTHolders",
        #     "params": {
        #         "blockchain": "moonbeam",
        #         "contractAddress": contractAddress,
        #         "pageSize": 10,
        #         "pageToken": ""
        #     },
        #     "id": id
        # }
        res = requests.post(url=url, json=data, headers=headers)
        print(res.text, res.status_code)

    def nft_check(id, address, contractAddress="0x1c9CF0E5473914A0e705e8Cf0BdD3EfbbFe17E48"):
        '''验证 NFT
        包括持有者和元数据'''
        # url = 'https://moonbeamapi.nftscan.com/api/v2/asset/collection/amount'
        url = "https://rpc.ankr.com/multichain/a1a69bca0f653800e0c598b54630efc93cebb607760a6bed2d67ac142c12435b"
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "id": id,
            "jsonrpc": 2.0,
            "method": 'ankr_getNFTHolders',
            "params": {
                "blockchain": "moonbeam",
                "contractAddress": contractAddress,
                "pageSize": 10,
                "pageToken": ""
            }
        }
        res = requests.get(url=url, headers=headers, json=data)
        print(res.text, res.status_code)
