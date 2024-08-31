# In order to import Mowl , remember to copy this file outside the example directory

from Mowl import *

client = MailReceiver('pop_server_ip',995)
client.connect()
client.login('your_email_address','your_key')

print(len(client))
exampleMail = client[0]

for object in exampleMail:
    print(object['content'])