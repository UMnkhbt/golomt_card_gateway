from datetime import datetime
from flask import Flask, jsonify, request
from pymongo import MongoClient
from models.income import Income, IncomeSchema
from models.transaction_type import TransactionType
import base64
import socket
import ssl
from http.client import HTTPSConnection
import requests, time, re, json, xmltodict

app = Flask(__name__)

loginUser = "Login"
loginPass = "Pass"
loginToken = "4DxHC7Ulh1734lbXyX6cMy4hibJMDYLbkOeo65ez+zs=$xih6efbMqNZ5Dy5PqC4N5FFfVizXCjLPvYkqwNPnCIo="
mainURL = "https://uatvpn.golomtbank.com/cardpro/service"

# **************************************************************  PURCHASE **************************************************************
@app.route('/Purchase')
def purchase():
  return "Method Not Allowed", 405

@app.route('/Purchase', methods=['POST'])
def purchase_request():

  if not request.get_json(): return "Not have requared fields!"
  jsn = request.get_json()  # Request to JSON data 

  if not 'amount' in jsn: return "Field amount is requared!"
  if not 'mode' in jsn: return "Field mode is requared!"
  if not 'track' in jsn: return "Field track is requared!"
  if not 'terminal_id' in jsn: return "Field terminal_id is requared!"
  if not 'merchant_id' in jsn: return "Field merchant_id is requared!"

  
  dbname = get_database()
  collection_name = dbname["users"]
  userCursor = collection_name.find({"User.terminal_id": jsn['terminal_id'], "User.merchant_id":jsn['merchant_id']})
  
  user = ""
  for doc in userCursor:
    user = doc['User']
    print (doc)
  if user == "": 
    return "Terminal is not found!"

  amount = str(int(jsn['amount']*100)).zfill(12)
  trace_num = str(user['trace_num'] + 1).zfill(6)
  batch_num = str(user['batch_num']).zfill(6)
  merchant_name = str(user['merchant_name'])
  sequence = jsn['sequence'] or "0001"
  acquiring = jsn['acquiring'] or "0003"
  code = jsn['code'] or "00"

  user['trace_num'] = user['trace_num'] + 1
  user['updated_at'] = datetime.today().strftime('%Y/%m/%d %H:%M:%S')

  collection_name.update(
    {
      "User.terminal_id":jsn['terminal_id'], 
      "User.merchant_id":jsn['merchant_id']
    },
    {
      "User": user
    }
  )

  xmldata = """<Document>
    <Header>
        <MsgId>"""+datetime.today().strftime('%Y%m%d%H%M%S')+"""</MsgId>
        <TrxnType>Purchase</TrxnType>
        <LoginId>"""+loginUser+"""</LoginId>
        <Password>"""+loginPass+"""</Password>
    </Header>
    <PosTxn>
        <MsgType>0200</MsgType>
        <F3>000000</F3>
        <F4>"""+amount+"""</F4>
        <F11>"""+trace_num+"""</F11>
        <F22>"""+jsn['mode']+"""</F22>
        <F23>"""+sequence+"""</F23>
        <F24>"""+acquiring+"""</F24>
        <F25>"""+code+"""</F25>
        <F35>"""+jsn['track']+"""</F35>
        <F41>"""+jsn['terminal_id']+"""</F41>
        <F42>"""+jsn['merchant_id']+"""</F42>
        <F43>"""+merchant_name+"""</F43>
        <F62>"""+batch_num+"""</F62>
    </PosTxn>
  </Document>"""
  
  
  #xmldata = json2xml(data)  # JSON to XML data
  # **************************************************************  input json write to DB ***************************************
  collection_name = dbname["purchase_input"]
  collection_name.insert_one(xmltodict.parse(xmldata))
  ##  XML DATA sent VPN 
  xmldata = xmldata.replace('\n','')
  xmldata = xmldata.replace('\t','')
  xmldata = xmldata.replace(' ', '')
  print(xmldata.strip())
  print("SENT")
  vpnresult = send_request_to_vpn(loginToken, "", mainURL , xmldata.strip(), "POST")
  print("RECEIVE")
  print(vpnresult)
  print(vpnresult.status_code)
  print(vpnresult.headers)
  print(str(vpnresult.content))

  return str( {
          "status_code":str(vpnresult.status_code),
          "content":str(vpnresult.content),
          "headers":str(vpnresult.headers),
        }
      )
  return str(vpnresult.content)
  

  return vpnresult #xmldata
  (
      response_status,
      response,
      response_headers,
  ) = send_request_to_vpn(False, "", "url_string", str(xmldata), "POST")

  if response_status != 200:
      result_data = (
          "Bank Gateway Proxy service connection failed.\nHTTP Error response: %s"
          % response
      )
  else:
      result_data = response["xmlresponse"]
  
  ## VPN RESULT Convert xml to json return
  result = xmltodict.parse(result_data)
  # **************************************************************  input json write to DB 
  collection_name = dbname["purchase_result"]
  collection_name.insert_one(result)

  return json.dumps(result)

# **************************************************************  REVERSAL **************************************************************
@app.route('/Reversal')
def reversal():
  return "Method Not Allowed", 405

@app.route('/Reversal', methods=['POST'])
def reversal_request():

  if not request.get_json(): return "Not have requared fields!"
  jsn = request.get_json()  # Request to JSON data 
  
  if not 'card_num' in jsn: return "Field card_num is requared!"
  if not 'amount' in jsn: return "Field amount is requared!"
  if not 'card_date' in jsn: return "Field card_date is requared!"
  if not 'mode' in jsn: return "Field mode is requared!"
  if not 'terminal_id' in jsn: return "Field terminal_id is requared!"
  if not 'merchant_id' in jsn: return "Field merchant_id is requared!"

  dbname = get_database()
  collection_name = dbname["users"]
  userCursor = collection_name.find({"User.terminal_id": jsn['terminal_id'], "User.merchant_id":jsn['merchant_id']})
  
  user = ""
  for doc in userCursor:
    user = doc['User']
    print (doc)
  if user == "": 
    return "Terminal is not found!"

  amount = str(int(jsn['amount']*100)).zfill(12)
  trace_num = str(user['trace_num'] + 1).zfill(6)
  batch_num = str(user['batch_num']).zfill(6)
  acquiring = jsn['acquiring'] or "0003"
  code = jsn['code'] or "00"

  user['trace_num'] = user['trace_num'] + 1
  user['updated_at'] = datetime.today().strftime('%Y/%m/%d %H:%M:%S')

  collection_name.update(
    {
      "User.terminal_id":jsn['terminal_id'], 
      "User.merchant_id":jsn['merchant_id']
    },
    {
      "User": user
    }
  )


  xmldata = """<Document>
    <Header>
        <MsgId>"""+datetime.today().strftime('%Y%m%d%H%M%S')+"""</MsgId>
        <TrxnType>Reversal</TrxnType>
        <LoginId>Login</LoginId>
        <Password>Pass</Password>
    </Header>
    <PosTxn>
        <MsgType>0400</MsgType>
        <F2>"""+jsn['card_num']+"""</F2>
        <F3>000000</F3>
        <F4>"""+amount+"""</F4>
        <F11>"""+trace_num+"""</F11>
        <F14>"""+jsn['card_date']+"""</F14>
        <F22>"""+jsn['mode']+"""</F22>
        <F24>"""+acquiring+"""</F24>
        <F25>"""+code+"""</F25>
        <F41>"""+jsn['terminal_id']+"""</F41>
        <F42>"""+jsn['merchant_id']+"""</F42>
        <F62>"""+batch_num+"""</F62>
    </PosTxn>
  </Document>"""
 
  
  #xmldata = json2xml(data)  # JSON to XML data
  # **************************************************************  input json write to DB 
  collection_name = dbname["reversal_input"]
  collection_name.insert_one(xmltodict.parse(xmldata))
  ##  XML DATA sent VPN 
  # send_request_to_vpn(proxy_auth_token, proxy_cert_data, url_string, params, request_method):
  vpnresult = send_request_to_vpn("", "4DxHC7Ulh1734lbXyX6cMy4hibJMDYLbkOeo65ez+zs=$xih6efbMqNZ5Dy5PqC4N5FFfVizXCjLPvYkqwNPnCIo=", "https://uatvpn.golomtbank.com", xmldata, "POST")
  print("https://10.10.10.1/")
  print(vpnresult)
  return vpnresult #xmldata
  (
      response_status,
      response,
      response_headers,
  ) = send_request_to_vpn(False, "", "url_string", str(xmldata), "POST")

  if response_status != 200:
      result_data = (
          "Bank Gateway Proxy service connection failed.\nHTTP Error response: %s"
          % response
      )
  else:
      result_data = response["xmlresponse"]
  
  ## VPN RESULT Convert xml to json return
  result = xmltodict.parse(result_data)
  # **************************************************************  input json write to DB 
  collection_name = dbname["reversal_result"]
  collection_name.insert_one(result)

  return json.dumps(result)

# **************************************************************  Void  REFUND **************************************************************
@app.route('/Refund')
def refund():
  return "Method Not Allowed", 405

@app.route('/Refund', methods=['POST'])
def refund_request():

  if not request.get_json(): return "Not have requared fields!"
  jsn = request.get_json()  # Request to JSON data 
  
  if not 'card_num' in jsn: return "Field card_num is requared!"
  if not 'amount' in jsn: return "Field amount is requared!"
  if not 'card_date' in jsn: return "Field card_date is requared!"
  if not 'mode' in jsn: return "Field mode is requared!"
  if not 'terminal_id' in jsn: return "Field terminal_id is requared!"
  if not 'merchant_id' in jsn: return "Field merchant_id is requared!"

  dbname = get_database()
  collection_name = dbname["users"]
  userCursor = collection_name.find({"User.terminal_id": jsn['terminal_id'], "User.merchant_id":jsn['merchant_id']})
  
  user = ""
  for doc in userCursor:
    user = doc['User']
    print (doc)
  if user == "": 
    return "Terminal is not found!"

  amount = str(int(jsn['amount']*100)).zfill(12)
  # strace_num = str(user['trace_num']).zfill(6)
  batch_num = str(user['batch_num']).zfill(6)
  acquiring = jsn['acquiring'] or "0003"
  code = jsn['code'] or "00"

  # user['trace_num'] = user['trace_num'] + 1
  # user['updated_at'] = datetime.today().strftime('%Y/%m/%d %H:%M:%S')

  # collection_name.update(
  #   {
  #     "User.terminal_id":jsn['terminal_id'], 
  #     "User.merchant_id":jsn['merchant_id']
  #   },
  #   {
  #     "User": user
  #   }
  # )

  #  **********************************    Purchase_result search 'card_num' && 'amount'  refund khiikh guikgeeg khaij olno

  xmldata = """<Document>
    <Header>
        <MsgId>"""+datetime.today().strftime('%Y%m%d%H%M%S')+"""</MsgId>
        <TrxnType>Void</TrxnType>
        <LoginId>Login</LoginId>
        <Password>Pass</Password>
    </Header>
    <PosTxn>
        <MsgType>0200</MsgType>
        <F2>"""+jsn['card_num']+"""</F2>
        <F3>020000</F3>
        <F4>"""+amount+"""</F4>
        <F11>"""+trace_num+"""</F11>
        <F12>"""+trace_time+"""</F12>
        <F13>"""+trace_date+"""</F13>
        <F14>"""+jsn['card_date']+"""</F14>
        <F22>"""+jsn['mode']+"""</F22>
        <F24>"""+acquiring+"""</F24>
        <F25>"""+code+"""</F25>
        <F37>"""+reference_num+"""</F37>
        <F38>"""+approval_code+"""</F38>
        <F41>"""+jsn['terminal_id']+"""</F41>
        <F42>"""+jsn['merchant_id']+"""</F42>
        <F62>"""+batch_num+"""</F62>
    </PosTxn>
  </Document>"""
   
  #xmldata = json2xml(data)  # JSON to XML data
  # **************************************************************  input json write to DB 
  collection_name = dbname["reversal_input"]
  collection_name.insert_one(xmltodict.parse(xmldata))
  ##  XML DATA sent VPN 
  vpnresult = send_request_to_vpn("4DxHC7Ulh1734lbXyX6cMy4hibJMDYLbkOeo65ez+zs=$xih6efbMqNZ5Dy5PqC4N5FFfVizXCjLPvYkqwNPnCIo=", "", "https://uatvpn.golomtbank.com/", xmldata, "POST")
  return vpnresult #xmldata
  (
      response_status,
      response,
      response_headers,
  ) = send_request_to_vpn(False, "", "url_string", str(xmldata), "POST")

  if response_status != 200:
      result_data = (
          "Bank Gateway Proxy service connection failed.\nHTTP Error response: %s"
          % response
      )
  else:
      result_data = response["xmlresponse"]
  
  ## VPN RESULT Convert xml to json return
  result = xmltodict.parse(result_data)
  # **************************************************************  input json write to DB 
  collection_name = dbname["reversal_result"]
  collection_name.insert_one(result)

  return json.dumps(result)

# **************************************************************  DETAILS **************************************************************
# **************************************************************  DB CONNECTION
def get_database():
  CONNECTION_STRING = "mongodb://localhost:27017/transactions"
  client = MongoClient(CONNECTION_STRING)
  return client['transactions']

# **************************************************************  JSON to XML 
def json2xml(json_obj, line_padding=""):
  result_list = list()

  json_obj_type = type(json_obj)

  if json_obj_type is list:
      for sub_elem in json_obj:
          result_list.append(json2xml(sub_elem, line_padding))

      return "\n".join(result_list)

  if json_obj_type is dict:
      for tag_name in json_obj:
          sub_obj = json_obj[tag_name]
          result_list.append("%s<%s>" % (line_padding, tag_name))
          result_list.append(json2xml(sub_obj, "\t" + line_padding))
          result_list.append("%s</%s>" % (line_padding, tag_name))

      return "\n".join(result_list)

  return "%s%s" % (line_padding, json_obj)

# **************************************************************  GOLOMT VPN SEND,RECEIV DATA
def send_request_to_vpn(proxy_auth_token, proxy_cert_data, url_string, params, request_method):
  # headers = {
  #     "Content-Type": "application/json",
  #     "Accept": "application/json",
  #     "Connection": "keep-alive",
  # }
  headers = {
    "Content-Type": "application/xml",
    "Accept": "application/xml",
    "Connection": "keep-alive",
  }
  if proxy_auth_token:
      headers["Authentication"] = proxy_auth_token

  if proxy_cert_data:
      host = url_string
      port = 80
      if "https://" in host:
          host = host.replace("https://", "")
          port = 443
      if "http://" in host:
          host = host.replace("http://", "")

      if len(host.split("/")) > 1:
          host = host.split("/")[0]

      if len(host.split(":")) > 1:
          port = int(host.split(":")[-1])
          host = ":".join(host.split(":")[:-1])

      conn = HTTPSConnection(host, port)
      sock = socket.create_connection(
          (conn.host, conn.port), conn.timeout, conn.source_address
      )
      ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_1)
      ctx.verify_mode = ssl.CERT_REQUIRED
      cert_data = str(base64.b64decode(proxy_cert_data), "utf-8")
      ctx.load_verify_locations(cadata=cert_data)
      ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
      conn.sock = ctx.wrap_socket(sock)

      if request_method == "POST":
          conn.request(
              request_method, url_string, headers=headers, body=params
          )
      else:
          conn.request(request_method, url_string, headers=headers)

      response = conn.getresponse()
      return (
          response.status,
          json.loads(response.read().decode("utf8"))
          if response.status == 200
          else response.reason,
          response.headers,
      )
  else:
      if request_method == "POST":
          res = requests.post(url_string, json=params, headers=headers)
      else:
          res = requests.get(url_string, headers=headers)
      return res
      return (
          res.status_code,
          res.json() if res.status_code == 200 else res.content,
          res.headers,
      )

# **************************************************************  XML to JSON
def xml2json(content):
  res=re.findall("<(?P<var>\S*)(?P<attr>[^/>]*)(?:(?:>(?P<val>.*?)</(?P=var)>)|(?:/>))",content)
  if len(res)>=1:
      attreg="(?P<avr>\S+?)(?:(?:=(?P<quote>['\"])(?P<avl>.*?)(?P=quote))|(?:=(?P<avl1>.*?)(?:\s|$))|(?P<avl2>[\s]+)|$)"
      if len(res)>1:
          return [{i[0]:[{"@attributes":[{j[0]:(j[2] or j[3] or j[4])} for j in re.findall(attreg,i[1].strip())]},{"$values":xml2json(i[2])}]} for i in res]
      else:
          return {res[0]:[{"@attributes":[{j[0]:(j[2] or j[3] or j[4])} for j in re.findall(attreg,res[1].strip())]},{"$values":xml2json(res[2])}]}
  else:
      return content
      
def requestVPN(vpnURL):

  #_, path = tempfile.mkstemp()
  #x = subprocess.Popen(['sudo', 'openvpn', '--config', path])

  try:
      #time required to connect the openvpn to connect vpn server
    time.sleep(8)
    start_time = time.time()
    url = vpnURL
    ret = requests.get(url)
    if ret.status_code == 200:
    #  x.kill()
      return ret.text
      print(ret.text)
    return "Error"
    print('Time took to check Ip address %s' % (time.time() - start_time))
    #x.kill()
    # termination with Ctrl+C
  except Exception as ex:
    return ex
    print('\nVPN terminated')    