# In order to import Mowl , remember to copy this file outside the example directory

from Mowl import *

client = MailSender('smtp_server_ip',465)
client.connect()
client.login('your_email_address','your_key')

envelop = Envelop('From@from.from',
                  'To@to.to',
                  'Hello World , this is Subject',
                  'FromNickName',
                  'ToNickName')

envelop.add(Text('''
    <html>
      <body>
        <p>Example</p>
        <img src="cid:dns">
      </body>
    </html>
''','html'))
with open('something.png','rb') as f:
    envelop.add(Image(f.read(),filename='img.png',cid='dns'))

client.send(envelop)